# Pokémon Yellow Color

A playable Game Boy Color enhancement of English Pokémon Yellow, with per-tile
overworld colors and Gen 2 battle graphics. **Version 0.1.7 is a preview build:**
the opening, all tilesets, sprite loaders, menus, saving, and surfing minigame
have automated checks; a complete playthrough and physical hardware testing
are still outstanding.

## Apply the patch

Download [PokemonYellowColor.bps](dist/PokemonYellowColor.bps) and apply it to
an **unmodified English USA/Europe Yellow ROM** with a BPS patcher such as
[Floating IPS](https://github.com/Alcaro/Flips).

| Input property | Required value |
| --- | --- |
| Size | 1,048,576 bytes |
| SHA-1 | `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1` |
| CRC32 | `7d527d62` |

The included Python patcher needs only Python 3, with no packages to install:

```sh
python3 scripts/bps.py apply "original-yellow.gbc" dist/PokemonYellowColor.bps "YellowColor.gbc"
```

It verifies the input and all BPS checksums and refuses to overwrite an existing
output. Load the resulting 2 MiB ROM in Game Boy Color mode. Full artifact
checksums are in [dist/manifest.json](dist/manifest.json).

## Before and after

[Watch the 43-second showcase](docs/showcase/showcase.mp4): Pallet Town,
Route 1, Oak’s lab, Viridian Forest, and ThunderShock. Both versions are captured
in Game Boy Color mode, with matching walking poses for the moving color reveal.
These showcase clips were recorded with v0.1.6; the screenshots below include
the newer trainer and Poké Ball colors.
[Download the individual videos and GIFs](docs/showcase/README.md).

![Walking through Pallet Town: original Yellow to full color](docs/showcase/pallet.gif)

## What changes

- All 25 overworld tilesets have individual terrain and furniture colors.
- Towns use distinct roof palettes, cream masonry, blue windows, and natural
  wood, stone, and metal colors in interiors. Pallet has terracotta roofs.
- Rounded route barriers have filled wood/stone colors. Forest stumps have
  colored cut faces and bark; animated flowers have pink petals and green leaves.
- NPCs have skin and clothing colors. Scientists, Oak, and cooks have separate
  white uniforms; their standing and walking frames use CGB-specific tiles.
- All 151 Pokémon have Gen 2 front and detailed 6×6 back sprites with species
  palettes. Trainer graphics come from the same Gen 2 graphics integration,
  with brighter CGB clothing colors and separate skin fills on the player, Oak,
  and old man back pictures. White clothing and hair details remain intact.
- Thrown Poké Balls retain red caps and white lower halves throughout the toss
  and shake. Great, Ultra, Master and Safari Balls have distinct cap colors.
- Eight moves use adapted Gen 2 effect artwork and frame sequences: ThunderShock,
  Thunderbolt, Thunder Wave, Thunder, Scratch, Cut, Tackle, and Quick Attack.
  Effects have their own palettes and stay above the battle text box.
  ThunderShock uses three moving spark bursts, with no opaque disk over the target.
- Pikachu's follower and reaction portraits have yellow fur. All 61 portrait
  graphics, including partial animation patches, have separate fur/background
  colors, with white eye highlights and red-orange cheeks.
- Dialogue appears progressively at all three text speeds; holding A or B
  accelerates it. Text prompts and line scrolling refresh during input waits.
  Item fanfares wait until the preceding text is fully displayed.
- Pokémon Center healing balls and monitors pulse red and white, then restore
  the normal NPC palettes.
- GBC gameplay uses the double-speed CPU, with unchanged frame-based game rules
  and correctly timed Pikachu voice samples. Unchanged NPC palettes are cached.
  Pokémon Centers, link rooms, and printing retain the original serial clock.
- Scrolling updates tile graphics and palette attributes together. Full-screen
  menus restore the entire background attribute map behind a uniform whiteout.
  Scrolling waits for the new edge data before exposing it, preventing a stale
  edge buffer from being displayed at a new screen position.
- Yellow's story, encounters, battle rules, follower, voice samples, and surfing
  minigame remain in place. No gameplay rebalance or extra Pokémon are added.

![Pallet Town](docs/screenshots/pallet.png)
![Oak's lab](docs/screenshots/oaks_lab.png)
![Gen 2 Pikachu and Eevee in battle](docs/screenshots/battle.png)
![Yellow Pikachu reaction portrait](docs/screenshots/portrait.png)

![Brighter trainer colors and player skin tones](docs/screenshots/trainer_battle.png)
![Colored Poké Ball during a menu-selected capture](docs/screenshots/pokeball.gif)

![Reworked ThunderShock during a battle turn](docs/screenshots/thundershock.gif)
![Pokémon Center healing pulse](docs/screenshots/healing_pulse.gif)

![Outdoor material improvements, before and after](docs/screenshots/terrain_comparison.png)
![Colored flowers in motion](docs/screenshots/flowers.gif)

## Build and verify

Building requires a C compiler, GNU Make, Python 3, and **RGBDS 1.0.3**.
Install that version from [RGBDS](https://github.com/gbdev/rgbds/releases/tag/v1.0.3),
then point the build script at its binaries:

```sh
python3 scripts/build.py --base "original-yellow.gbc" --rgbds /path/to/rgbds/bin
```

This builds the ROM locally and creates a verified BPS patch in `dist/`.
The default RGBDS path is `.cache/rgbds`. ROMs, saves, emulator states, and
downloaded development tools are excluded from Git.

For the automated emulator checks:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_emulator.py
.venv/bin/python scripts/verify_sprites.py
.venv/bin/python scripts/verify_special_scenes.py
.venv/bin/python scripts/build_portraits.py --check
.venv/bin/python scripts/verify_portraits.py
.venv/bin/python scripts/build_overworld_sprites.py --check
.venv/bin/python scripts/verify_assets.py
.venv/bin/python scripts/verify_text.py
.venv/bin/python scripts/build_battle_effects.py --check
.venv/bin/python scripts/build_terrain.py --check
.venv/bin/python scripts/build_battle_colors.py --check
```

Run the scripts in that order, from the repository root, after building.
The first creates emulator states for the later checks. Outputs go to
`build/verification/`. See [testing and limitations](docs/TESTING.md).
The additional SameBoy checks described there account for graphics DMA stalls
and verify walking, LCD access, voice timing, and CPU-speed transitions.

## Credits

- [pret/pokeyellow](https://github.com/pret/pokeyellow): the documented Yellow
  disassembly; its pinned baseline reproduces the supported ROM exactly.
- [dannye/pokered-gbc](https://github.com/dannye/pokered-gbc): terrain assignments,
  map and roof palettes, from FroggestSpirit, Drenn, dannye, and contributors.
- [dannye/pokeyellow-gen-2-gfx](https://github.com/dannye/pokeyellow-gen-2-gfx):
  Gen 2 Pokémon/trainer graphics, palettes, and back-sprite integration.
- [pret/pokecrystal](https://github.com/pret/pokecrystal): selected battle-effect
  graphics, palettes, OAM layouts, and frame sequences adapted to Yellow.
- [RGBDS](https://rgbds.gbdev.io/), [PyBoy](https://github.com/Baekalfen/PyBoy),
  [SameBoy](https://github.com/LIJI32/SameBoy),
  and [Pan Docs](https://gbdev.io/pandocs/): development tools and references.

[Pinned revisions and implementation notes](docs/UPSTREAM.md) document the
upstream contributions and the new color renderer.

This is an unofficial fan project. Original and upstream assets retain their
ownership; no new license is asserted over them. The distributed game artifact
is a patch, not a complete ROM.
