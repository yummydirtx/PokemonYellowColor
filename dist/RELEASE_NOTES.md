# Pokémon Yellow Color 0.1.3 — preview

Fixes the noticeable walking slowdown, especially in Oak's lab. Normal GBC
gameplay now uses the double-speed CPU, and an unchanged-palette cache bug no
longer causes all eight character palettes to be uploaded every game update.
Prepared background buffers are reused until consumed. The crowded-lab
SameBoy fixture improves from roughly 20 to 30 game updates per second.
The original frame-based movement rules remain intact.

All 42 Pikachu recordings retain their original sample bits and playback rate.
Pokémon Centers, the Indigo Plateau lobby, link rooms, and printer sessions
use the original CPU/serial clock; normal maps return to double speed.

Fixes dialogue remaining blank during normal letter-by-letter printing and
appearing only after a later refresh. Holding B previously happened to use a
working refresh path. Input polling now keeps color tile transfers supplied,
so normal text speeds, A/B acceleration, blinking prompts, and line scrolling
all update visibly.

Also defers terrain animation and OAM transfers when large graphics uploads
leave insufficient VBlank time. Stronger timing checks include the final OAM
transfer; all monitored graphics work ends within VBlank.

Includes the building/interior/NPC color pass from 0.1.2, yellow Pikachu reaction
portraits, and Gen 2 front/back battle sprites for all 151 Pokémon.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Only the patch and checksum manifest are release assets.

Validation uses PyBoy plus independent SameBoy checks that include actual DMA
stalls. It covers 18 dialogue speed/button/renderer combinations, prompt
blinking and line scrolling, opening gameplay, 35 asset map entries across
all 25 tilesets, all 82 NPC types, 302 Pokémon sprite loads, all 29 Pikachu
reactions, menus, save/reload, surfing, and a DMG boot. See `docs/TESTING.md`.

This remains a playable preview: a complete playthrough and physical hardware/
link testing remain outstanding. Old emulator save states are build-specific;
use normal in-game saves when moving between versions.
