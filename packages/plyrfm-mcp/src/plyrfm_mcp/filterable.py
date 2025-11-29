"""filterable decorator for MCP tools.

adds a `_filter` parameter that accepts jmespath expressions to
filter/project tool results. this reduces response size and lets
LLM clients request only the fields they need.

example:
    @mcp.tool
    @filterable
    async def list_tracks(limit: int = 20) -> list[dict]:
        ...

    # client can call with:
    # list_tracks(limit=10, _filter="[*].{id: id, title: title}")
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Annotated, Any, ParamSpec, TypeVar, overload

import jmespath
import jmespath.exceptions
from pydantic import Field, TypeAdapter

P = ParamSpec("P")
R = TypeVar("R")

# type alias for the filter parameter with description
FilterParam = Annotated[
    str | None,
    Field(
        default=None,
        description=(
            "jmespath expression to filter/project the result. "
            "examples: '[*].{id: id, title: title}' (select fields), "
            "'[?play_count > `50`]' (filter items), "
            "'[*].title' (extract values)"
        ),
    ),
]


def apply_filter(data: Any, filter_expr: str | None) -> Any:
    """apply jmespath filter to data."""
    if not filter_expr:
        return data
    try:
        # use pydantic's TypeAdapter to serialize - handles models, lists, etc.
        jsonable = TypeAdapter(type(data)).dump_python(data, mode="json")
        return jmespath.search(filter_expr, jsonable)
    except jmespath.exceptions.JMESPathError:
        # on bad filter, return original data
        return data


@overload
def filterable(
    fn: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[Any]]: ...


@overload
def filterable(
    fn: Callable[P, R],
) -> Callable[P, Any]: ...


def filterable(
    fn: Callable[P, R] | Callable[P, Awaitable[R]],
) -> Callable[P, Any] | Callable[P, Awaitable[Any]]:
    """decorator that adds `_filter` parameter to a tool.

    the filter is a jmespath expression applied to the result.
    see https://jmespath.org/ for syntax.

    usage:
        @mcp.tool
        @filterable
        async def list_things() -> list[dict]:
            return [{"id": 1, "name": "foo"}, ...]

        # call without filter - get everything
        list_things()

        # call with filter - get filtered result
        list_things(_filter="[*].{id: id}")
    """

    @wraps(fn)
    async def async_wrapper(
        *args: P.args, _filter: str | None = None, **kwargs: P.kwargs
    ) -> Any:
        result = await fn(*args, **kwargs)  # type: ignore[misc]
        return apply_filter(result, _filter)

    @wraps(fn)
    def sync_wrapper(
        *args: P.args, _filter: str | None = None, **kwargs: P.kwargs
    ) -> Any:
        result = fn(*args, **kwargs)  # type: ignore[misc]
        return apply_filter(result, _filter)

    # choose wrapper based on whether fn is async
    wrapper = async_wrapper if inspect.iscoroutinefunction(fn) else sync_wrapper

    # update signature to include _filter parameter
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    params.append(
        inspect.Parameter(
            "_filter",
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=FilterParam,
        )
    )
    wrapper.__signature__ = sig.replace(parameters=params)  # type: ignore[attr-defined]

    # update __annotations__ for pydantic's get_type_hints()
    # return type is Any since filtered results can have any shape
    wrapper.__annotations__ = {
        **fn.__annotations__,
        "_filter": FilterParam,
        "return": Any,
    }

    return wrapper
