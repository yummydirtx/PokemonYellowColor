# Pokémon Yellow Color 0.1.7 — preview

Fixes the brief colored-block flash when returning from a full-screen menu.
The map is now restored behind a uniform whiteout, including palettes whose
normal background shade is green or cream.

Fixes a scrolling race that could upload an old edge buffer at a new position.
The renderer keeps the previous view until the new tile IDs and attributes are
ready. The prior build fails a deterministic reproduction; the new build passes
96 edge-transfer cases and 7,680 frames of map-content checks. The exact reported
intermittent Viridian Forest half-tree scene still needs a physical retest.

Battle trainers have brighter CGB clothing colors. The player, Oak and old man
back pictures now separate exposed skin from the white background while keeping
white clothing/hair details and the original silhouettes.

Thrown Poké Balls have red caps and white lower halves throughout their toss
and shake. Great, Ultra, Master and Safari Balls use blue, gold, purple and green
caps. Their colors no longer depend on the battler's palette or native flashes.

Checks include six trainer introductions, all three back pictures on CGB/DMG,
15 ball-animation cases, and complete menu-selected captures on CGB and DMG.
The existing opening, maps, text, healing, fanfare, sprite, portrait, battle-effect,
surfing, save, walking and voice-timing checks pass. Walking remains at 29.86
updates/sec in the three benchmark scenes. See `docs/TESTING.md` for details.

Includes all prior terrain, animation, color and performance changes.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Only the patch and checksum manifest are release assets.
Normal battery saves retain their layout; emulator save states are build-specific.

This remains a playable preview. A complete playthrough and physical hardware/
link testing remain outstanding.
