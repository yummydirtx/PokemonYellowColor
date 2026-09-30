# Pokémon Yellow Color 0.1.1 — preview

Fixes the white fur in Pikachu's reaction portraits. All 61 portrait graphics
now use distinct fur and background colors, including the partial animation
frames. All 29 reaction scripts were exercised in the emulator. Original
monochrome graphics remain in place for DMG/SGB.

Full-color GBC terrain, interiors, NPCs, and Pikachu follower, with Gen 2 front
and back battle sprites for all 151 Pokémon. Built from pinned pret Yellow
source with credited palette and graphics work from dannye's projects.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

The output is a 2 MiB GBC-compatible ROM. Only the patch and checksum manifest
are included as release assets.

Validation covers the opening rival battle, all 25 tilesets, all 302 Pokémon
sprite loads, menus, save/reload, surfing, and a monochrome boot. A full
playthrough and physical hardware/link testing remain outstanding. See the
repository's `docs/TESTING.md` for details.
