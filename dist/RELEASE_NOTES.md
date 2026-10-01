# Pokémon Yellow Color 0.1.4 — preview

Fixes Pokémon Center healing balls and monitors remaining static. Their
original eight-phase pulse now changes a dedicated red/white CGB palette,
without recoloring Center NPCs, and restores the normal palettes afterward.

Fixes item fanfares starting before the last letters appear. Text-command
sounds now wait for the preceding text to reach the screen, including fast
text and A/B acceleration. Hidden pickups use the same synchronization.

Adds adapted Gen 2 battle effects for ThunderShock, Thunderbolt, Thunder Wave,
Thunder, Scratch, Cut, Tackle, and Quick Attack. These use Crystal's effect
artwork, palettes, OAM layouts, and frame sequences, placed for Yellow's front
and back sprites. Effects stay above the text box and restore their palettes.
This is a selected-effects port, not the complete Gen 2 animation engine;
Yellow's sounds, damage/status rules, animation option, and other moves remain.

Includes the double-speed performance work, progressive text, building/interior/
NPC colors, yellow Pikachu portraits, and all 151 Gen 2 front/back sprites from
previous versions.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Only the patch and checksum manifest are release assets.

New SameBoy checks cover healing with one/six party members, 18 text speed/
button combinations at the exact fanfare start, and 48 animation combinations:
eight moves × both directions × three sprite pairs. They check sprite limits,
text-box clipping, unchanged Pokémon graphics, restored tilemaps/palettes, and
blocked LCD writes. Animation-off and native fallback paths are also checked.
The existing opening, sprite, portrait, map, text, save, surfing, performance,
and hardware timing checks remain in place. See `docs/TESTING.md`.

This remains a playable preview: a complete playthrough and physical hardware/
link testing remain outstanding. Old emulator save states are build-specific;
use normal in-game saves when moving between versions.
