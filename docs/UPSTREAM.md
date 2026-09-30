# Upstream sources

Pinned source revisions used for this project:

| Source | Revision | Use |
| --- | --- | --- |
| https://github.com/pret/pokeyellow | `e89ead154b9968aa50eed9328ff2b38b6c194382` | Complete baseline disassembly, verified byte-for-byte against the user's English Yellow dump |
| https://github.com/dannye/pokered-gbc | `c1a3b6c5a7591472241036d0cf09c3817f841f93` | Terrain assignments, map and roof palettes; credits to FroggestSpirit, Drenn, dannye and contributors |
| https://github.com/dannye/pokeyellow-gen-2-gfx | `0ac32c82681b32c0a8c8b9162c18ce31ac74f876` | Gen 2 Pokémon and trainer artwork, species/trainer palettes, 6×6 back sprite loading, introduction palette helpers |
| https://github.com/gbdev/rgbds | `v1.0.3` | Assembler/linker/graphics toolchain |

The color transfer implementation in `src/color/engine.asm` is new for this
project. It retains the original single CPU speed used by Pikachu PCM audio
and serial code; link compatibility still needs validation. Tile IDs and palette attributes are prepared together, then
transferred using GBC DMA. Horizontal columns use unrolled CPU transfers.

Bank 0x3b holds the palette/color engine; banks 0x40–0x42 hold expanded battle graphics
and palette data. Banks 0x43–0x44 hold the CGB reaction portrait variants.
Bank 0x45 holds CGB copies of scientist, Oak, cook, and Seel overworld sprites.
The resulting cartridge is 2 MiB, MBC5 with 32 KiB battery RAM.
Existing game and save data addresses remain unchanged; eleven unused bytes of
fixed audio-page RAM hold renderer state. Additional scratch buffers use WRAM
bank 2 only in interrupt-disabled leaf code, because the original stack is in
bank 1.

Full-screen menu exit rebuilds both VRAM attribute maps from the actual tile
IDs, including offscreen scroll rows. The display interrupt defers graphics
work when it arrives too late for safe VRAM/OAM access. Palette conversion
continues to honor the original fade registers.

Yellow's beach house has a dedicated tile-color table. Pikachu's dynamic
follower slot is handled separately from the ordinary NPC picture IDs.

`scripts/build_portraits.py` derives CGB-only indexed tile data from Yellow's
original portrait PNGs. Enclosed fur regions receive the yellow index, while
the exterior field and small eye highlights retain white. Partial animation
graphics are classified in the context of their complete base frame. Original
PNGs and the original DMG/SGB graphics path remain available. The generated
assembly is checked in so normal builds do not require image-processing tools.

`scripts/build_overworld_sprites.py` separates skin from white clothing, hats,
and Oak's silver hair using frame-specific indexed pixel masks. These variants
are selected by the normal NPC sheet loader on CGB; native source sheets remain
unchanged. Seel uses a white body with dark contours instead of skin/blue colors.

The material pass replaces inherited grayscale defaults with cream masonry,
wood, teal tile, sandstone, lavender stone, and blue-gray metal. Tile assignments
separate equipment and window glass from walls/floors across shared tilesets.
The palette table omits its unused padding; all 25 palette sets are range checked.

Original code/assets retain their original ownership and attribution. This
repository does not assert a new license over Pokémon or upstream assets.
