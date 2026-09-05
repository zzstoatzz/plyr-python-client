"""Documentation checks must reject stale methods and keyword arguments."""

from plyrfm import PlyrClient

from scripts.check_doc_examples import check


def test_doc_calls_match_sdk() -> None:
    with PlyrClient() as client:
        assert not check("```python\nclient.tracks.get(42)\n```", client)
        assert check("```python\nclient.get_track(42)\n```", client)
        assert check(
            '```python\nclient.discover.search("ambient", offset=10)\n```', client
        )
