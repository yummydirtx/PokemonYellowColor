# Pokémon Yellow Color 0.1.2 — preview

A broader color pass for buildings, interiors, and overworld characters:

- Terracotta roofs in Pallet and slate-blue roofs in Pewter, with cream masonry
  and blue window glass across towns.
- Wood floors, teal tile, sandstone and lavender stone interiors; blue-gray
  equipment, computers and cabinets instead of inherited grayscale defaults.
- Skin and clothing palettes for previously gray NPCs. Scientists, Oak and cooks
  have separate white uniforms in all standing and walking frames. Oak has
  silver hair; Seel has a white body. Original monochrome sheets are preserved.

Includes the yellow Pikachu reaction portraits from 0.1.1 and Gen 2 front/back
battle sprites for all 151 Pokémon.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Only the patch and checksum manifest are release assets.

The asset audit covers 35 map entries across all 25 tilesets, all 82 NPC types,
and 256 native/CGB sprite loader comparisons. Opening gameplay, all 302 Pokémon
sprite loads, all 29 Pikachu reactions, menus, save/reload, surfing and a DMG boot
also pass. See `docs/TESTING.md` for methods and remaining validation.

This remains a playable preview: a complete playthrough and physical hardware/
link testing remain outstanding. Old emulator save states are build-specific;
use normal in-game saves when moving between versions.
