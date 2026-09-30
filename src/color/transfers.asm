ColorOriginalRedrawRowOrColumn::
	ldh a, [hRedrawRowOrColumnMode]
	and a
	ret z
	ld b, a
	xor a
	ldh [hRedrawRowOrColumnMode], a
	dec b
	jr nz, .redrawRow
.redrawColumn
	ld hl, wRedrawRowOrColumnSrcTiles
	ldh a, [hRedrawRowOrColumnDest]
	ld e, a
	ldh a, [hRedrawRowOrColumnDest + 1]
	ld d, a
	ld c, SCREEN_HEIGHT
.loop1
	ld a, [hli]
	ld [de], a
	inc de
	ld a, [hli]
	ld [de], a
	ld a, TILEMAP_WIDTH - 1
	add e
	ld e, a
	jr nc, .noCarry
	inc d
.noCarry
; the following 4 lines wrap us from bottom to top if necessary
	ld a, d
	and HIGH(TILEMAP_AREA - 1)
	or HIGH(vBGMap0)
	ld d, a
	dec c
	jr nz, .loop1
	xor a
	ldh [hRedrawRowOrColumnMode], a
	ret
.redrawRow
	ld hl, wRedrawRowOrColumnSrcTiles
	ldh a, [hRedrawRowOrColumnDest]
	ld e, a
	ldh a, [hRedrawRowOrColumnDest + 1]
	ld d, a
	push de
	call .DrawHalf ; draw upper half
	pop de
	ld a, TILEMAP_WIDTH
	add e
	ld e, a
	; fall through and draw lower half

.DrawHalf
	ld c, SCREEN_WIDTH / 2
.loop2
	ld a, [hli]
	ld [de], a
	inc de
	ld a, [hli]
	ld [de], a
	ld a, e
	inc a
; the following 6 lines wrap us from the right edge to the left edge if necessary
	and %11111
	ld b, a
	ld a, e
	and %11100000
	or b
	ld e, a
	dec c
	jr nz, .loop2
	ret

; This function automatically transfers tile number data from the tile map at
; wTileMap to VRAM during V-blank. Note that it only transfers one third of the
; background per V-blank. It cycles through which third it draws.
; This transfer is turned off when walking around the map, but is turned
; on when talking to sprites, battling, using menus, etc. This is because
; the above function, RedrawRowOrColumn, is used when walking to
; improve efficiency.
ColorOriginalAutoBgMapTransfer::
	ldh a, [hAutoBGTransferEnabled]
	and a
	ret z
	ld [hSPTemp], sp ; save stack pointer
	ldh a, [hAutoBGTransferPortion]
	and a
	jr z, .transferTopThird
	dec a
	jr z, .transferMiddleThird
.transferBottomThird
	hlcoord 0, 2 * SCREEN_HEIGHT / 3
	ld sp, hl
	ldh a, [hAutoBGTransferDest + 1]
	ld h, a
	ldh a, [hAutoBGTransferDest]
	ld l, a
	ld de, 12 * TILEMAP_WIDTH
	add hl, de
	xor a ; TRANSFERTOP
	jr .doTransfer
.transferTopThird
	hlcoord 0, 0
	ld sp, hl
	ldh a, [hAutoBGTransferDest + 1]
	ld h, a
	ldh a, [hAutoBGTransferDest]
	ld l, a
	ld a, TRANSFERMIDDLE
	jr .doTransfer
.transferMiddleThird
	hlcoord 0, SCREEN_HEIGHT / 3
	ld sp, hl
	ldh a, [hAutoBGTransferDest + 1]
	ld h, a
	ldh a, [hAutoBGTransferDest]
	ld l, a
	ld de, 6 * TILEMAP_WIDTH
	add hl, de
	ld a, TRANSFERBOTTOM
.doTransfer
	ldh [hAutoBGTransferPortion], a ; store next portion
	ld b, SCREEN_HEIGHT / 3

TransferBgRows::
; unrolled loop and using pop for speed
REPT SCREEN_WIDTH / 2 - 1
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

	ld a, TILEMAP_WIDTH - (SCREEN_WIDTH - 1)
	add l
	ld l, a
	jr nc, .ok
	inc h
.ok
	dec b
	jr nz, TransferBgRows

	ldh a, [hSPTemp]
	ld l, a
	ldh a, [hSPTemp + 1]
	ld h, a
	ld sp, hl
	ret

; Copies [hVBlankCopyBGNumRows] rows from hVBlankCopyBGSource to hVBlankCopyBGDest.
; If hVBlankCopyBGSource is XX00, the transfer is disabled.
ColorOriginalVBlankCopyBgMap::
	ldh a, [hVBlankCopyBGSource] ; doubles as enabling byte
	and a
	ret z
	ld [hSPTemp], sp ; save stack pointer
	ldh a, [hVBlankCopyBGSource]
	ld l, a
	ldh a, [hVBlankCopyBGSource + 1]
	ld h, a
	ld sp, hl
	ldh a, [hVBlankCopyBGDest]
	ld l, a
	ldh a, [hVBlankCopyBGDest + 1]
	ld h, a
	ldh a, [hVBlankCopyBGNumRows]
	ld b, a
	xor a
	ldh [hVBlankCopyBGSource], a ; disable transfer so it doesn't continue next V-blank
	jr TransferBgRows
