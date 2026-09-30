# Version 0.1.1 verification

The final clean build was tested with RGBDS 1.0.3 and PyBoy 2.7.0 on 2026-09-30.
The exact build and patch hashes are recorded in `dist/manifest.json`.

| Check | Result |
| --- | --- |
| Pinned pret baseline against the supplied dump | Exact byte-for-byte match |
| RAM/save layout comparison | All 3,160 shared named RAM symbols retain their original addresses |
| Clean assembly/link/header checks | Passed; 2 MiB, MBC5 + 32 KiB battery RAM, CGB-compatible header |
| BPS unit tests | 3 passed: round trips, wrong/corrupt input rejection, external SourceCopy command |
| Patch application with bundled implementation | Exact target match |
| Independent Floating IPS application | Exact target match |
| Opening with button input | New game, naming, both house floors, Pallet, Oak's capture, lab, starter, rival battle, follower |
| Overworld scrolling | All four directions and toroidal background-map wrapping |
| Party/stats menu return | No visible palette attribute mismatches |
| Save and fresh-emulator Continue | Game checksum accepted; map and party data restored |
| Map entry matrix | 26 maps covering all 25 tilesets; zero visible palette attribute mismatches |
| Pokémon sprite loaders | 151 front + 151 back sprites; decoded VRAM matches source graphics byte-for-byte |
| Pikachu reaction portraits | All 29 reaction scripts and 61 graphic entries exercised; yellow fur and return to overworld palettes checked |
| Portrait source regeneration | Checked-in CGB tile data matches the deterministic generator; original PNGs remain unchanged |
| Surfing minigame | Gameplay, results, exit, and overworld palette restoration passed |
| Monochrome fallback | New game through the bedroom, using PyBoy's DMG boot ROM |
| Active-display overworld transfer timing | Transfer endpoint remained within scanlines 145–151 in the opening test |

The display interrupt defers graphics work if PCM playback or buffer preparation
delays entry past the beginning of VBlank. Audio/input bookkeeping continues,
and pending graphics transfers are retained for the next safe frame.

The map matrix uses test-only RAM warps. The sprite matrix calls actual ROM
routines through a test-only RAM trampoline and compares their output with
RGBDS-generated source tiles. The surfing fixture grants Surf only in emulator
RAM. None of these fixtures is compiled into the distributed patch.

Machine-readable results are preserved in `docs/verification/`; screenshots
are in `docs/screenshots/`. Re-running the scripts produces fresh results in
`build/verification/`. Floating IPS was built from revision
`ff216a75df0987047a67d7923567dc4482ce07ac` for the independent patch check.

## Remaining validation

This is a playable preview, not a claim that every possible game path has been
tested. A complete playthrough, every battle animation, evolution/trade/Hall of
Fame transitions, emotion-selection triggers, printer/link/Super Game Boy operation,
and physical GBC/flash-cartridge testing remain outstanding. Headless tests do
not assess audible PCM quality. The original single CPU speed is retained.

The original battery-save layout is preserved, but imported long-running saves
have not been comprehensively exercised. Emulator save states are specific to
the ROM build and should not be carried between versions.
