# Pokémon Yellow Color 0.1.5 — preview

Reworks ThunderShock into three short bursts of expanding, moving Gen 2 sparks.
The opaque black core is gone, the Pokémon remains visible, and the sound starts
with the first sparks. The final burst ends with the sound and leads straight
into the hit reaction. The new 92-frame effect replaces the previous 112-frame
sequence. Its motion and timing are adapted for Yellow, using unchanged Crystal
spark artwork. The other seven adapted moves retain their existing sequences.

The README preview now shows the revised effect during a button-driven battle
turn. Both attack directions have been checked across three sprite pairs, with
additional checks for the three bursts, visible movement, palette restoration,
sprite limits and safe LCD writes. A complete ThunderShock turn verifies both
attacks, damage, player PP consumption and return to the battle menu.

Includes the healing pulses, synchronized item jingles, double-speed performance
work, progressive text, overworld colors, yellow Pikachu portraits, and all 151
Gen 2 front/back sprites from previous versions. The existing regression suite
was rerun for this build; see `docs/TESTING.md` for results and limitations.

Apply `PokemonYellowColor.bps` to unmodified English USA/Europe Yellow:

- SHA-1: `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`
- CRC32: `7d527d62`
- Input size: 1,048,576 bytes

Apply to the original ROM, not a previously patched version. The output is a
2 MiB GBC-compatible ROM. Only the patch and checksum manifest are release assets.

This remains a playable preview: a complete playthrough and physical hardware/
link testing remain outstanding. Old emulator save states are build-specific;
use normal in-game saves when moving between versions.
