; Single-speed CGB renderer. Original audio/PCM, link timing and save layout stay intact.
; Extra WRAM is accessed only in interrupt-disabled leaf code. The original stack
; lives in bank 1, so no push/pop/call/ret is permitted while bank 2 is selected.
DEF COLOR_BUFFER EQU $d000

ColorGetTiles:
	ld a, [wCurMapTileset]
	cp NUM_TILESETS
	jr c, .valid
	xor a
.valid
	add a
	ld e, a
	ld d, 0
	ld hl, ColorTilesetPointers
	add hl, de
	inc hl ; all tile tables are page aligned
	ld a, [hl]
	ld [wColorTilesHigh], a
	ret

ColorPikachuPortrait:
	ld a, $80
	ld [wColorCommand], a
	jp ColorUpdateBG

ColorLoadOverworld:
	ld a, SET_PAL_OVERWORLD
	ld [wDefaultPaletteCommand], a
	ld a, 1
	ld [wColorActive], a
	call ColorGetTiles
	ld a, [wCurMapTileset]
	add a
	ld e, a
	ld d, 0
	ld hl, MapPaletteSets
	add hl, de
	ld a, [hli]
	ld [wColorPaletteSet], a
	ld a, [hl]
	ld [wColorPaletteSet + 1], a
	call ColorUpdateBG
	call ColorUpdateOBJ
	jp ColorRepaintMaps

; Convert all eight palettes through the native DMG fade registers.
ColorUpdateBG:
	xor a
	ld [wColorPaletteIndex], a
.loop
	ld a, [wColorPaletteIndex]
	cp 7
	jr nz, .terrain
	ld a, [wColorCommand]
	cp $80
	jr nz, .terrain
	ld a, PAL_PIKACHU_PORTRAIT
	call GetCGBBasePalAddress
	xor a
	call DMGPalToCGBPal
	jr .transfer
.terrain
	ld a, [wColorPaletteSet]
	ld l, a
	ld a, [wColorPaletteSet + 1]
	ld h, a
	ld a, [wColorPaletteIndex]
	ld e, a
	ld d, 0
	add hl, de
	ld a, [hl]
	ld l, a
	ld h, 0
	add hl, hl
	add hl, hl
	add hl, hl
	ld de, MapPalettes
	add hl, de
	ld d, h
	ld e, l
	; Town-specific roofs use palette 6 on outdoor maps.
	ld a, [wColorPaletteIndex]
	cp 6
	jr nz, .convert
	ld a, [wCurMapTileset]
	cp OVERWORLD
	jr nz, .convert
	ld a, [wCurMap]
	cp FIRST_INDOOR_MAP
	jr nc, .convert
	ld hl, ColorRoofPalettes
	ld c, a
	ld b, 0
	add hl, bc
	add hl, bc
	ld a, [hli]
	ld d, [hl]
	ld e, a
.convert
	xor a
	call ColorDMGPalToCGBPal
.transfer
	ld a, [wColorPaletteIndex]
	call TransferCurBGPData
	ld hl, wColorPaletteIndex
	inc [hl]
	ld a, [hl]
	cp 8
	jr nz, .loop
	ret

ColorUpdateOBJ:
	xor a
	ld [wColorPaletteIndex], a
.loop
	ld a, [wColorPaletteIndex]
	add a
	add a
	add a
	ld e, a
	ld d, 0
	ld hl, ColorObjectPalettes
	add hl, de
	ld d, h
	ld e, l
	ld a, CONVERT_OBP0
	call ColorDMGPalToCGBPal
	ld a, [wColorPaletteIndex]
	call TransferCurOBPData
	ld hl, wColorPaletteIndex
	inc [hl]
	ld a, [hl]
	cp 8
	jr nz, .loop
	ret

; LCD is disabled by map-loading callers. Keep both VRAM banks in lockstep.
ColorMapAttributes::
	push de
	call ColorGetTiles
	pop de
	ld a, 1
	ldh [rVBK], a
	ld hl, wTileMap
	ld b, SCREEN_HEIGHT
.row
	ld c, SCREEN_WIDTH
.tile
	ld a, [hli]
	push hl
	ld l, a
	ld a, [wColorTilesHigh]
	ld h, a
	ld a, [hl]
	ld [de], a
	pop hl
	inc e
	dec c
	jr nz, .tile
	ld a, TILEMAP_WIDTH - SCREEN_WIDTH
	add e
	ld e, a
	jr nc, .noCarry
	inc d
.noCarry
	dec b
	jr nz, .row
	xor a
	ldh [rVBK], a
	ret

; Generate the next six rows outside VBlank, aligned for a 192-byte GDMA.
ColorPrepareAuto::
	call ColorPrepareScroll
	ldh a, [hVBlankCopyBGSource]
	and a
	jr z, .auto
	ld l, a
	ldh a, [hVBlankCopyBGSource + 1]
	ld h, a
	ldh a, [hVBlankCopyBGDest]
	ld e, a
	ldh a, [hVBlankCopyBGDest + 1]
	ld d, a
	ld a, 2
	ld [wColorCopyKind], a
	jr .selected
.auto
	ld a, 1
	ld [wColorCopyKind], a
	ldh a, [hAutoBGTransferEnabled]
	and a
	ret z
	ld hl, wTileMap
	ldh a, [hAutoBGTransferDest]
	ld e, a
	ldh a, [hAutoBGTransferDest + 1]
	ld d, a
	ldh a, [hAutoBGTransferPortion]
	and a
	jr z, .selected
	ld bc, 120
	add hl, bc
	ld a, e
	add 192
	ld e, a
	jr nc, .middle
	inc d
.middle
	ldh a, [hAutoBGTransferPortion]
	cp 1
	jr z, .selected
	add hl, bc
	ld a, e
	add 192
	ld e, a
	jr nc, .selected
	inc d
.selected
	ld a, e
	ld [wColorAutoDest], a
	ld a, d
	ld [wColorAutoDest + 1], a
	di
	ld a, 2
	ldh [rSVBK], a
	ld de, COLOR_BUFFER
	ld a, [wColorTilesHigh]
	ld b, a
REPT 6
REPT 20
	ld a, [hli]
	set 1, d
	ld [de], a
	res 1, d
	ld c, a
	ld a, [bc]
	ld [de], a
	inc e
ENDR
	ld a, e
	add 12
	ld e, a
ENDR
	ld a, 1
	ldh [rSVBK], a
	ld [wColorAutoReady], a
	ei
	ret

ColorTransferVRAM::
	ld a, [wColorAutoReady]
	and a
	jr z, .scroll
	xor a
	ld [wColorAutoReady], a
	ld a, [wColorCopyKind]
	cp 2
	jr nz, .advance
	xor a
	ldh [hVBlankCopyBGSource], a
	jr .dma
.advance
	ldh a, [hAutoBGTransferPortion]
	inc a
	cp 3
	jr c, .portion
	xor a
.portion
	ldh [hAutoBGTransferPortion], a
.dma
	ld a, 2
	ldh [rSVBK], a
	; Copy tile IDs and attributes from paired, padded buffers.
FOR plane, 2
	ld a, plane
	ldh [rVBK], a
	ld a, HIGH(COLOR_BUFFER) + (1 - plane) * 2
	ldh [rVDMA_SRC_HIGH], a
	xor a
	ldh [rVDMA_SRC_LOW], a
	ld a, [wColorAutoDest]
	ldh [rVDMA_DEST_LOW], a
	ld a, [wColorAutoDest + 1]
	ldh [rVDMA_DEST_HIGH], a
	ld a, 11
	ldh [rVDMA_LEN], a
ENDR
	ld a, 1
	ldh [rSVBK], a
	xor a
	ldh [rVBK], a

.scroll
	ldh a, [hRedrawRowOrColumnMode]
	and a
	ret z
	ld c, a
	xor a
	ldh [hRedrawRowOrColumnMode], a
	ldh a, [hRedrawRowOrColumnDest]
	ld e, a
	ldh a, [hRedrawRowOrColumnDest + 1]
	ld d, a
	ld a, 2
	ldh [rSVBK], a
	dec c
	jp nz, .rows
	; HL is the toroidal destination; BC adds the stride after each pair.
FOR plane, 2
	ld a, plane
	ldh [rVBK], a
	ld de, COLOR_BUFFER + $100 + (1 - plane) * $200
	ldh a, [hRedrawRowOrColumnDest]
	ld l, a
	ldh a, [hRedrawRowOrColumnDest + 1]
	ld h, a
	ld bc, TILEMAP_WIDTH - 1
REPT SCREEN_HEIGHT
	ld a, [de]
	inc e
	ld [hli], a
	ld a, [de]
	inc e
	ld [hl], a
	add hl, bc
	res 2, h ; wrap $9cxx to $98xx
ENDR
ENDR
	jp .done

.rows
	; Rows begin on even tile coordinates. Two complete toroidal rows are
	; DMA'd; offscreen columns are replaced before horizontal scrolling exposes them.
FOR plane, 2
	ld a, plane
	ldh [rVBK], a
	ld a, HIGH(COLOR_BUFFER) + 4 + (1 - plane) * 2
	ldh [rVDMA_SRC_HIGH], a
	xor a
	ldh [rVDMA_SRC_LOW], a
	ld a, e
	and $e0
	ldh [rVDMA_DEST_LOW], a
	ld a, d
	ldh [rVDMA_DEST_HIGH], a
	ld a, 3
	ldh [rVDMA_LEN], a
ENDR
.done
	ld a, 1
	ldh [rSVBK], a
	xor a
	ldh [rVBK], a
	ret

ColorPrepareScroll:
	ldh a, [hRedrawRowOrColumnMode]
	and a
	ret z
	cp 2
	jp z, .rows
	di
	ld a, 2
	ldh [rSVBK], a
	ld hl, wRedrawRowOrColumnSrcTiles
	ld de, COLOR_BUFFER + $100
	ld a, [wColorTilesHigh]
	ld b, a
REPT 40
	ld a, [hli]
	set 1, d
	ld [de], a
	res 1, d
	ld c, a
	ld a, [bc]
	ld [de], a
	inc e
ENDR
	jp .done
.rows
	di
	ld a, 2
	ldh [rSVBK], a
	ld hl, wRedrawRowOrColumnSrcTiles
	ldh a, [hRedrawRowOrColumnDest]
	and 31
	ld e, a
	ld d, HIGH(COLOR_BUFFER) + 4
	ld a, [wColorTilesHigh]
	ld b, a
FOR row, 2
REPT SCREEN_WIDTH
	ld a, [hli]
	set 1, d
	ld [de], a
	res 1, d
	ld c, a
	ld a, [bc]
	ld [de], a
	inc e
	ld a, e
	and 31
	or row * 32
	ld e, a
ENDR
	ldh a, [hRedrawRowOrColumnDest]
	and 31
	or 32
	ld e, a
ENDR
.done
	ld a, 1
	ldh [rSVBK], a
	ei
	ret

ColorVBlankAll::
	ld a, [wColorActive]
	and a
	jr z, .native
	call ColorTransferVRAM
	jp ColorOriginalRedrawRowOrColumn
.native
	call ColorOriginalAutoBgMapTransfer
	call ColorOriginalVBlankCopyBgMap
	jp ColorOriginalRedrawRowOrColumn

ColorObjectPalettes:
	RGB 31,31,31, 31,22,14, 27,5,5, 3,3,4 ; player/red
	RGB 31,31,31, 31,22,14, 6,12,26, 3,3,4 ; blue
	RGB 31,31,31, 24,29,15, 6,20,9, 3,3,4 ; green
	RGB 31,31,31, 31,23,15, 17,11,5, 3,3,4 ; brown
	RGB 31,31,31, 31,23,19, 28,10,17, 3,3,4 ; pink
	RGB 31,31,31, 31,28,3, 22,12,2, 3,3,4 ; Pikachu
	RGB 31,31,31, 25,25,25, 13,14,16, 3,3,4 ; gray
	RGB 31,31,31, 31,22,14, 19,9,24, 3,3,4 ; purple

ColorDMGPalToCGBPal:
; Populate wCGBPal with colors from a base palette, selected using one of the
; DMG palette registers.
; Input:
; a = which DMG palette register
; de = address of CGB base palette
	and a
	jr nz, .notBGP
	ldh a, [rBGP]
	ld [wLastBGP], a
	jr .convert
.notBGP
	dec a
	jr nz, .notOBP0
	ldh a, [rOBP0]
	ld [wLastOBP0], a
	cp $d0
	jr nz, .convert
	ld a, $e4 ; expose all three opaque colors in the original sprite art
	jr .convert
.notOBP0
	ldh a, [rOBP1]
	ld [wLastOBP1], a
.convert
	FOR color_index, PAL_COLORS
		ld b, a
		and %11
		call .GetColorAddress
		ld a, [hli]
		ld [wCGBPal + color_index * 2], a
		ld a, [hl]
		ld [wCGBPal + color_index * 2 + 1], a

		IF color_index < PAL_COLORS - 1
			ld a, b
			rrca
			rrca
		ENDC
	ENDR
	ret

.GetColorAddress:
	add a
	ld l, a
	xor a
	ld h, a
	add hl, de
	ret


; Native full-screen menus replace both attribute maps. Restore colors from the
; actual VRAM tile IDs, including scrolled/offscreen rows, when returning to maps.
; The short DI section protects each paired VRAM access; EI between tiles keeps
; audio and input interrupts serviced. Waiting for mode 0/1 leaves mode 2 as a
; safety margin before the next mode 3, so no writes touch inaccessible VRAM.
ColorRepaintMaps:
	ld hl, vBGMap0
	ld a, [wColorTilesHigh]
	ld d, a
.loop
	di
.wait
	ldh a, [rSTAT]
	and 2
	jr nz, .wait
	xor a
	ldh [rVBK], a
	ld a, [hl]
	ld e, a
	ld a, [de]
	ld c, a
	ld a, 1
	ldh [rVBK], a
	ld [hl], c
	xor a
	ldh [rVBK], a
	ei
	inc hl
	ld a, h
	cp $a0
	jr nz, .loop
	ret
