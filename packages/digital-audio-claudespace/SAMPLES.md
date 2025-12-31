# samples

CC0 public domain samples from [VCSL (Versilian Community Sample Library)](https://github.com/sgossner/VCSL).

## local library

Samples are stored in `/samples/` (gitignored), organized by instrument:

```
samples/
  harp/           - concert harp, warm plucked strings
  vibraphone/     - soft mallets, warm sustaining tones
  glockenspiel/   - bright metallic bells
  chimes/         - tubular bells, orchestral
```

## source

VCSL uses Hornbostel-Sachs classification:

```
Aerophones/          - wind (flutes, organ, recorders)
Chordophones/        - strings (harps, zithers)
Electrophones/       - synths (TX81Z)
Idiophones/          - pitched percussion (vibes, glock, bells)
Membranophones/      - drums
```

## browsing & downloading

```bash
# browse categories
gh api repos/sgossner/VCSL/contents/Idiophones | jq -r '.[].name'

# drill down
gh api "repos/sgossner/VCSL/contents/Idiophones/Struck Idiophones/Vibraphone" | jq -r '.[].name'

# download
curl -LO "https://github.com/sgossner/VCSL/raw/master/path/to/sample.wav"
```

## naming conventions

- Harp: `KSHarp_{Note}_{Dynamic}{Variation}.wav` (e.g., `KSHarp_E3_mf1.wav`)
- Vibraphone: `Vibes_soft_{Note}_v{vel}_rr{round}_Main.wav`
- Glockenspiel: `glock_{dynamic}_{Note}_{round}.wav`
- Chimes: `chimes_{Note}_{dynamic}_rr{round}.wav`

## license

CC0 - public domain. no attribution required.
