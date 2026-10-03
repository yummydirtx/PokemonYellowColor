# Pokémon Yellow Color 0.1.8 — preview

Restores Bug Catcher's original Gen 2 palette. His shared shadow color is dark
blue again, bringing back the contrast around his face, hair and hat that the
bright green in v0.1.7 had obscured. The README battle screenshot is updated.

The ROM changes only two palette bytes and one checksum byte from v0.1.7.
All prior rendering, trainer-back, Poké Ball and performance improvements remain.
The battle-color checks pass, and the BPS patch was independently applied with
Floating IPS and compared byte-for-byte with the built ROM.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Normal battery saves retain their layout.

This remains a playable preview; full-playthrough and physical hardware/link
validation remain outstanding. See `docs/TESTING.md` for the scope of this update.
