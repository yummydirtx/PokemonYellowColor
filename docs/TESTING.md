# Version 0.1.7 verification

The final clean build was tested with RGBDS 1.0.3, PyBoy 2.7.0, and SameBoy
revision `213a12ce93d66b105a113debd9396306066a7cfc` on 2026-10-02.
The exact build and patch hashes are recorded in `dist/manifest.json`.

| Check | Result |
| --- | --- |
| Pinned pret baseline against the supplied dump | Exact byte-for-byte match |
| RAM/save layout comparison | All 3,180 shared named SRAM/WRAM/HRAM symbols retain their original addresses |
| Clean assembly/link/header checks | Passed; 2 MiB, MBC5 + 32 KiB battery RAM, CGB-compatible header |
| BPS unit tests | 3 passed: round trips, wrong/corrupt input rejection, external SourceCopy command |
| Patch application with bundled implementation | Exact target match |
| Independent Floating IPS application | Exact target match |
| Opening with button input | New game, naming, both house floors, Pallet, Oak's capture, lab, starter, rival battle, follower |
| Overworld scrolling | All four directions and toroidal background-map wrapping |
| Party/stats menu return | No visible palette attribute mismatches |
| Menu whiteout | Frame-by-frame party/card/options exits in Pallet and forest; repaint frames uniformly white, zero blocked LCD writes; v0.1.6 fails at Pallet party-return frame 33 |
| Scrolling edge race | 96 forced row/column requests across toroidal wrap positions; unprepared requests retain VRAM, prepared tiles and attributes match; v0.1.6 fails the first unprepared column case |
| Moving map contents | 7,680 frames across forest, Pallet and Route 1; every visible tile ID checked against map blocks and every attribute against its tile palette; zero mismatches or blocked writes |
| Trainer battle colors | Six actual encounter introductions; front palettes match, player back colored; all three back loaders preserve body/head alignment on CGB and the original pixels on DMG |
| Thrown balls | Five types × catch/breakout/trainer-block sequences (15 cases); white lower halves and correct cap colors throughout, palette slot reclaimed, zero blocked LCD writes |
| Complete capture | Menu-selected Poké Ball on CGB and DMG; engine catches Rattata, adds it to the party, consumes exactly one ball and returns to overworld colors |
| Dialogue progression | 18 combinations: fast/medium/slow, no held button/A/B, color and original transfer branches; complete text reaches VRAM, with at least 10 partial stages and at most 3 frames display lag |
| Text prompts and line scrolling | Blinking arrow, CONT moving the previous bottom line to the top, progressive third line, and normal dialogue close passed |
| Healing pulse | SameBoy: one/six party members in Viridian and Fuchsia Centers; all eight phases alternate, NPC palettes restore, zero blocked VRAM/palette writes |
| Item-fanfare synchronization | SameBoy: actual visible Potion and hidden Antidote pickups at all three speeds with no held button/A/B; both text rows match WRAM at the exact instruction that starts the sound |
| Gen 2 battle effects | SameBoy: eight moves × both directions × three front/back pairs (48 cases); no picture-byte or BG-palette corruption, tilemap/OBJ palettes restored, no stale OAM, zero blocked VRAM/palette writes |
| ThunderShock motion | Three distinct spark bursts and at least 12 distinct OAM arrangements in both directions across all three sprite pairs; only four spark sprites, with no opaque core |
| ThunderShock battle turn | Button-selected move against a wild Pikachu fixture; both sides animate, take damage, and return to the menu; player PP decrements normally; hit sound follows the sparks within one frame; zero blocked LCD writes |
| Effect hardware limits | At most 38 OAM entries and nine sprites on a scanline; tiles stay above the text box and inside the effect VRAM range |
| Effect fallback | Animations-off option skips effects; Ember still uses the original engine; native dispatch bypasses the Gen 2 effect player |
| Effect source regeneration | Imported PNG hashes and generated frames/timelines match the checked-in Gen 2 source data |
| Outdoor materials | SameBoy: all 25 tilesets loaded in both CGB-E and DMG models (50 exact artwork comparisons); original native sheets preserved |
| Flowers and terrain restoration | All three CGB and original DMG flower poses observed; water keeps animating; Route 1, Pallet, Route 22 and forest tiles survive menu return; zero blocked VRAM/palette writes |
| Terrain source regeneration | CGB wood/stone/stump masks and three flower frames match their checked-in generated data |
| Save and fresh-emulator Continue | Game checksum accepted; map and party data restored |
| Map entry matrix | 26 maps covering all 25 tilesets; zero visible palette attribute mismatches |
| Asset color audit | 35 map entries across all 25 tilesets, tile and NPC atlases visually reviewed; zero palette attribute mismatches |
| NPC graphics | All 82 types, 256 native/CGB standing and walking loader comparisons; original tiles preserved |
| White uniforms | Skin and coat colors present in all 18 scientist/Oak/cook frames; original silhouettes and outlines preserved |
| Pokémon sprite loaders | 151 front + 151 back sprites; decoded VRAM matches source graphics byte-for-byte |
| Pikachu reaction portraits | All 29 reaction scripts and 61 graphic entries exercised; yellow fur and return to overworld palettes checked |
| Portrait source regeneration | Checked-in CGB tile data matches the deterministic generator; original PNGs remain unchanged |
| Surfing minigame | Gameplay, results, exit, and overworld palette restoration passed |
| Monochrome fallback | New game through the bedroom, using PyBoy's DMG boot ROM |
| Active-display overworld transfer timing | All monitored graphics blocks in opening/map and dialogue tests finished in LCD mode 1 (VBlank), including OAM DMA; counts are in the reports |
| Independent LCD/DMA timing | SameBoy: 26 maps across all 25 tilesets and nine dialogue combinations; zero writes to VRAM or palette data during blocked LCD mode 3, zero visible attribute mismatches |
| Walking CPU budget | SameBoy: all three optimized walking fixtures sustain 256 game updates per 512 display frames, without redundant OBJ palette uploads |
| Pikachu PCM timing | SameBoy: all 42 clips, 1,447,632 bits per mode, exact source bitstreams and 360 ticks at 8 MHz between every bit; checked in CGB double speed, CGB single speed, and DMG modes |
| Clock transitions | All 14 maps that initiate link handshakes select single speed; normal maps select double speed; printer entry/exit and soft reset checked |

The display interrupt defers graphics work if PCM playback or buffer preparation
delays entry past the beginning of VBlank. Audio/input bookkeeping continues,
and pending graphics transfers are retained for the next safe frame. Terrain
animation and OAM DMA also check their remaining scanline budget after large
font/sprite uploads. The test samples LCD mode after the final graphics work,
including OAM DMA.

PyBoy 2.7.0 omits the CPU stall for General Purpose VRAM DMA in
`core/mb.py`. Its scanline readings alone therefore cannot establish a hardware
budget. The independent SameBoy checks include those stalls and monitor blocked
VRAM/palette writes as well as the end of graphics work.

The walking comparison uses 512-frame button sequences in each location:

| Scene | Original Yellow updates/sec | Version 0.1.6 | Version 0.1.7 |
| --- | ---: | ---: | ---: |
| Oak's lab, center | 28.81 | 29.86 | 29.86 |
| Oak's lab, lower floor | 28.11 | 29.86 | 29.86 |
| Pallet Town | 28.11 | 29.86 | 29.86 |

These are game-loop updates, not LCD refresh rates or emulator host throughput.
The median walking-animation interval remains two display frames. The comparison
ROM is v0.1.6 (target hash `fde8ce1369fd08ea54ed4d6f51d8af5a69484261499f3aca45e8d79053f074f7`).
The report retains the historical key `before_optimization` for the optional
comparison ROM; in this run that key means v0.1.6, not the older slow renderer.

The map matrix uses test-only RAM warps. The sprite matrix calls actual ROM
routines through a test-only RAM trampoline and compares their output with
RGBDS-generated source tiles. The asset audit also checks the original sprite branch and produces contact
sheets containing only each sprite's real source frames. The surfing fixture
grants Surf only in emulator RAM. None of these fixtures is compiled into the distributed patch.

The dialogue regression opens the actual Oak lab scientist conversation using
button input after a map-position fixture. It compares text in VRAM against the
WRAM text buffer on every frame, verifies the three configured speeds remain
distinct, and checks both speed-up buttons. The original transfer branch uses
the same CGB emulator fixture with native rendering selected; the separate DMG
boot test covers actual monochrome startup. Pallet's sign supplies a real
three-line conversation and blinking prompt.
The README portrait uses the normal follower interaction with a high-happiness
screenshot fixture; it does not change happiness in the released game.

The reported bug was reproduced before the fix: without a held button, all 29
non-space characters reached WRAM but none reached the visible tilemap during
the 240-frame capture. With B held, the visible text progressed normally.

The healing regression calls the actual healing-machine routine after a map
positioning fixture and checks every flash in hardware OAM/palette RAM. The
previous build fails this check because all eight palette samples are identical.
Fuchsia specifically covers the purple Rocker NPC: the healing palette must
not commandeer his palette. The fanfare regression uses button input to pick
up a visible Potion and hidden Antidote in Viridian Forest and stops at `PlaySound` before playback.

The battle-effects fixture enters a real Rattata encounter, then calls
`MoveAnimation` with Pikachu/Rattata, Charizard/Gengar, and Snorlax/Mew pictures.
It inspects both attack directions each frame and compares the sprite graphics,
background palettes, and final tilemap against their pre-animation values.
This isolates visual behavior; it is not a complete combat-rules test. Opening
playthrough coverage separately exercises the new effects during a real battle.
The effect matrix contact sheet and GIFs show these emulator fixtures, including test names.

The additional ThunderShock capture uses a normal battle turn after setting the
wild encounter, nickname and available moves in test RAM. Button input selects
the attack and advances text; the game handles both attacks, damage, PP and the
return to its menu. The README GIF now comes from this capture, with an
[opponent-side preview](screenshots/thundershock_enemy.gif) and
[chronological frames](screenshots/thundershock_sequence.png) showing expansion
and the clear intervals. The hit sound begins within one frame of the final burst.
GIF delays alternate between 30 and 40 ms to preserve the Game Boy's frame rate
when sampling every other frame. This is a visual adaptation of the Gen 2
sparks; automated motion/safety checks alone do not establish visual quality.

The rendering regression reads fixed bank-one WRAM directly, because a frame
boundary can land during the renderer's temporary bank-two scratch work. It
compares actual visible tile IDs against the canonical map blocks as well as
checking attributes. The forced race test creates a request before preparation
and checks that neither VRAM plane changes. This proves the stale-buffer bug
and its fix; the reported exact intermittent half-tree scene was not reproduced
through ordinary walking. A physical forest retest remains necessary. The
[menu-return recording](screenshots/menu_return.gif) shows the corrected whiteout.

The battle-color matrix uses routine fixtures to force all three animation
outcomes for each ball type. These are visual tests, including otherwise
impossible combinations such as a Master Ball breakout. The separate capture
check uses menu input on CGB and DMG; only encounter, inventory, names, starting
HP and sleep are set in RAM, and the game calculates the capture outcome and
item/party changes. The README ball GIF comes from that capture. The trainer
[contact sheet](screenshots/battle_colors.png) contains the encounter and animation
fixtures; it is separate from the menu-selected capture.

Machine-readable results are preserved in `docs/verification/`; screenshots
are in `docs/screenshots/`. Re-running the scripts produces fresh results in
`build/verification/`. Floating IPS was built from revision
`ff216a75df0987047a67d7923567dc4482ce07ac` for the independent patch check.

## Independent timing checks

After the normal build and `verify_emulator.py`, build the pinned SameBoy core
and open-source boot ROMs locally (a C compiler and RGBDS are required):

```sh
git clone https://github.com/LIJI32/SameBoy.git .cache/sameboy
git -C .cache/sameboy checkout 213a12ce93d66b105a113debd9396306066a7cfc
make -C .cache/sameboy -j4 build/lib/libsameboy.a bootroms RGBDS=../../.cache/rgbds/
.venv/bin/python scripts/verify_performance.py
.venv/bin/python scripts/verify_hardware_scenes.py
.venv/bin/python scripts/verify_feedback.py
.venv/bin/python scripts/verify_battle_effects.py
.venv/bin/python scripts/verify_thundershock.py
.venv/bin/python scripts/verify_terrain.py
.venv/bin/python scripts/verify_rendering.py
.venv/bin/python scripts/verify_battle_colors.py
.venv/bin/python scripts/verify_capture.py
```

The performance comparison also expects the exact original ROM and its matching
pret symbols at `build/baseline.gbc` and `build/baseline.sym`. An optional
`--before path/to/prior.gbc` includes a prior build with a matching `.sym`.
The adapter uses SameBoy's public API and compiles locally; no emulator code
is included in the game. It runs on macOS/Linux with a C compiler. Fixtures
finish pending interrupts before replacing the program counter.
SameBoy warns that some PPU/APU phases following a double-to-single speed switch
are not fully modeled; physical speed-transition/audio checks remain necessary.

## Remaining validation

This is a playable preview, not a claim that every possible game path has been
tested. A complete playthrough, every battle animation, evolution/trade/Hall of
Fame transitions, emotion-selection triggers, printer/link/Super Game Boy operation,
and physical GBC/flash-cartridge testing remain outstanding. Headless tests do
not assess audible PCM quality. CPU speed selection and the PCM bit period are
verified; this does not replace listening or physical cable/printer testing.

The original battery-save layout is preserved, but imported long-running saves
have not been comprehensively exercised. Emulator save states are specific to
the ROM build and should not be carried between versions.
