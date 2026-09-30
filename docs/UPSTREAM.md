# Upstream sources

Pinned source revisions used for this project:

| Source | Revision | Use |
| --- | --- | --- |
| https://github.com/pret/pokeyellow | `e89ead154b9968aa50eed9328ff2b38b6c194382` | Complete baseline disassembly, verified byte-for-byte against the user's English Yellow dump |
| https://github.com/dannye/pokered-gbc | `c1a3b6c5a7591472241036d0cf09c3817f841f93` | Terrain assignments, map and roof palettes; credits to FroggestSpirit, Drenn, dannye and contributors |
| https://github.com/dannye/pokeyellow-gen-2-gfx | `0ac32c82681b32c0a8c8b9162c18ce31ac74f876` | Gen 2 Pokémon and trainer artwork, species/trainer palettes, 6×6 back sprite loading, introduction palette helpers |
| https://github.com/gbdev/rgbds | `v1.0.3` | Assembler/linker/graphics toolchain |

The color transfer implementation in `src/color/engine.asm` is new for this
project. It runs at the original single CPU speed to preserve Pikachu PCM audio
and link timing. Tile IDs and palette attributes are prepared together, then
transferred using GBC DMA. Horizontal columns use unrolled CPU transfers.

Bank 0x3b holds the palette/color engine; banks 0x40–0x42 hold expanded graphics
and palette data. The resulting cartridge is 2 MiB, MBC5 with 32 KiB battery RAM.
Existing game and save data addresses remain unchanged; eleven unused bytes of
fixed audio-page RAM hold renderer state. Additional scratch buffers use WRAM
bank 2 only in interrupt-disabled leaf code, because the original stack is in
bank 1.

Original code/assets retain their original ownership and attribution. This
repository does not assert a new license over Pokémon or upstream assets.
