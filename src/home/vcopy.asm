; this function seems to be used only once
; it store the address of a row and column of the VRAM background map in hl
; INPUT: h - row, l - column, b - high byte of background tile map address in VRAM
GetRowColAddressBgMap::
	xor a
	srl h
	rr a
	srl h
	rr a
	srl h
	rr a
	or l
	ld l, a
	ld a, b
	or h
	ld h, a
	ret

; clears a VRAM background map with blank space tiles
; INPUT: h - high byte of background tile map address in VRAM
ClearBgMap::
	ld a, ' '
	jr FillBgMapCommon

; fills a VRAM background map with tile index in register l
; INPUT: h - high byte of background tile map address in VRAM
FillBgMap:: ; unreferenced
	ld a, l

FillBgMapCommon:
	ld de, TILEMAP_AREA
	ld l, e
.loop
	ld [hli], a
	dec e
	jr nz, .loop
	dec d
	jr nz, .loop
	ret

; This function redraws a BG row of height 2 or a BG column of width 2.
; One of its main uses is redrawing the row or column that will be exposed upon
; scrolling the BG when the player takes a step. Redrawing only the exposed
; row or column is more efficient than redrawing the entire screen.
; However, this function is also called repeatedly to redraw the whole screen
; when necessary. It is also used in trade animation and elevator code.
RedrawRowOrColumn::
	farjp ColorOriginalRedrawRowOrColumn

AutoBgMapTransfer::
	farjp ColorOriginalAutoBgMapTransfer

VBlankCopyBgMap::
	farjp ColorOriginalVBlankCopyBgMap



VBlankCopyDouble::
; Copy [hVBlankCopyDoubleSize] 1bpp tiles
; from hVBlankCopyDoubleSource to hVBlankCopyDoubleDest.

; While we're here, convert to 2bpp.
; The process is straightforward:
; copy each byte twice.

	ldh a, [hVBlankCopyDoubleSize]
	and a
	ret z

	ld [hSPTemp], sp ; save stack pointer

	ldh a, [hVBlankCopyDoubleSource]
	ld l, a
	ldh a, [hVBlankCopyDoubleSource + 1]
	ld h, a
	ld sp, hl

	ldh a, [hVBlankCopyDoubleDest]
	ld l, a
	ldh a, [hVBlankCopyDoubleDest + 1]
	ld h, a

	ldh a, [hVBlankCopyDoubleSize]
	ld b, a
	xor a ; transferred
	ldh [hVBlankCopyDoubleSize], a

.loop
REPT TILE_SIZE / 4 - 1
	pop de
	ld [hl], e
	inc l
	ld [hl], e
	inc l
	ld [hl], d
	inc l
	ld [hl], d
	inc l
ENDR
	pop de
	ld [hl], e
	inc l
	ld [hl], e
	inc l
	ld [hl], d
	inc l
	ld [hl], d
	inc hl
	dec b
	jr nz, .loop

	ld [hVBlankCopyDoubleSource], sp
	ld sp, hl ; load destination into sp to save time with ld [$xxxx], sp
	ld [hVBlankCopyDoubleDest], sp

	ldh a, [hSPTemp]
	ld l, a
	ldh a, [hSPTemp + 1]
	ld h, a
	ld sp, hl

	ret


VBlankCopy::
; Copy [hVBlankCopySize] 2bpp tiles (or 16 * [hVBlankCopySize] tile map entries)
; from hVBlankCopySource to hVBlankCopyDest.

; Source and destination addresses are updated,
; so transfer can continue in subsequent calls.

	ldh a, [hVBlankCopySize]
	and a
	ret z

	ld [hSPTemp], sp

	ldh a, [hVBlankCopySource]
	ld l, a
	ldh a, [hVBlankCopySource + 1]
	ld h, a
	ld sp, hl

	ldh a, [hVBlankCopyDest]
	ld l, a
	ldh a, [hVBlankCopyDest + 1]
	ld h, a

	ldh a, [hVBlankCopySize]
	ld b, a
	xor a ; transferred
	ldh [hVBlankCopySize], a

.loop
REPT TILE_SIZE / 2 - 1
	pop de
	ld [hl], e
	inc l
	ld [hl], d
	inc l
ENDR
	pop de
	ld [hl], e
	inc l
	ld [hl], d
	inc hl
	dec b
	jr nz, .loop

	ld [hVBlankCopySource], sp
	ld sp, hl
	ld [hVBlankCopyDest], sp

	ldh a, [hSPTemp]
	ld l, a
	ldh a, [hSPTemp + 1]
	ld h, a
	ld sp, hl

	ret


UpdateMovingBgTiles::
; Animate water and flower
; tiles in the overworld.

	ldh a, [hTileAnimations]
	and a
	ret z

	ldh a, [rLY]
	cp $90 ; check if not in vblank period??? (maybe if vblank is too long)
	ret c
	; On CGB, paired background transfers share the budget with tile uploads.
	; Defer water/flower animation when it would crowd out the OAM transfer.
	ld a, [wColorActive]
	and a
	jr z, .animate
	ldh a, [rLY]
	cp 150
	ret nc
.animate

	ldh a, [hMovingBGTilesCounter1]
	inc a
	ldh [hMovingBGTilesCounter1], a
	cp 20
	ret c
	cp 21
	jr z, .flower

; water

	ld hl, vTileset tile $14
	ld c, TILE_SIZE

	ld a, [wMovingBGTilesCounter2]
	inc a
	and 7
	ld [wMovingBGTilesCounter2], a

	and 4
	jr nz, .left
.right
	ld a, [hl]
	rrca
	ld [hli], a
	dec c
	jr nz, .right
	jr .done
.left
	ld a, [hl]
	rlca
	ld [hli], a
	dec c
	jr nz, .left
.done
	ldh a, [hTileAnimations]
	rrca
	ret nc

	xor a
	ldh [hMovingBGTilesCounter1], a
	ret

.flower
	xor a
	ldh [hMovingBGTilesCounter1], a

	ld a, [wMovingBGTilesCounter2]
	and 3
	cp 2
	ld hl, FlowerTile1
	jr c, .copy
	ld hl, FlowerTile2
	jr z, .copy
	ld hl, FlowerTile3
.copy
	ldh a, [hOnCGB]
	and a
	jr z, .nativeFlower
	ld a, [wCurMapTileset]
	and a ; OVERWORLD; indoor animated tiles keep their native palette/art
	jr nz, .nativeFlower
	ld de, ColorFlowerTile1 - FlowerTile1
	add hl, de
.nativeFlower
	ld de, vTileset tile $03
	ld c, TILE_SIZE
.loop
	ld a, [hli]
	ld [de], a
	inc de
	dec c
	jr nz, .loop
	ret

FlowerTile1: INCBIN "gfx/tilesets/flower/flower1.2bpp"
FlowerTile2: INCBIN "gfx/tilesets/flower/flower2.2bpp"
FlowerTile3: INCBIN "gfx/tilesets/flower/flower3.2bpp"

INCLUDE "color/flower_data.asm"
