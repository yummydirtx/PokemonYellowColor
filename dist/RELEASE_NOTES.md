# Pokémon Yellow Color 0.1.6 — preview

Adds a second outdoor material pass. Rounded fence posts now have wood-colored
interiors, rounded route stones have warm stone fills, and forest stumps have
colored cut faces, growth rings and bark. A small forest stone also receives a
material fill. These details previously shared the near-white ground color.

Flowers now have pink petals and green foliage in all three animation poses.
Their dedicated outdoor palette and CGB frame data remain in place as the
flowers sway. The README includes current scenery and a before/after comparison.

The original Game Boy graphics remain intact. Tile IDs, map blocks, collision,
encounters and saves are unchanged. Outdoor replacements load with the normal
map graphics; they add no per-frame walking work. The flower animation adds a
small frame-selection branch without switching ROM banks during VBlank.

Checks cover all 25 tileset loads on CGB and DMG (50 artwork comparisons), all
three flower poses on both models, water animation, and outdoor menu restoration.
The existing opening, maps, text, healing, fanfares, sprites, portraits, battle
effects, save, surfing, walking and voice-timing suite was rerun. See
`docs/TESTING.md` for results and limitations.

Includes the ThunderShock revision and all prior color/performance fixes.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Only the patch and checksum manifest are release assets.

This remains a playable preview: a complete playthrough and physical hardware/
link testing remain outstanding. Emulator save states are build-specific;
use normal in-game saves when moving between versions.
