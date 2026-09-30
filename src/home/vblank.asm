VBlank::

	push af
	push bc
	push de
	push hl

	ldh a, [rVBK] ; vram bank
	push af
	xor a
	ldh [rVBK], a ; reset vram bank to 0

	ldh a, [hLoadedROMBank]
	ld [wVBlankSavedROMBank], a

	ldh a, [hSCX]
	ldh [rSCX], a
	ldh a, [hSCY]
	ldh [rSCY], a

	ld a, [wDisableVBlankWYUpdate]
	and a
	jr nz, .ok
	ldh a, [hWY]
	ldh [rWY], a
.ok
	; PCM playback and color-buffer preparation may defer an interrupt.
	; Keep pending transfers queued until a complete VBlank is available.
	ld a, [wColorActive]
	and a
	jr z, .graphics
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr z, .graphics
	ldh a, [rLY]
	cp 144
	jr nz, .afterGraphics
.graphics

	farcall ColorVBlankAll
	call VBlankCopy
	call VBlankCopyDouble
	call UpdateMovingBgTiles
	; OAM DMA needs almost two scanlines. Font/sprite uploads can leave too
	; little of VBlank; keep the previous OAM for one frame in that case.
	ld a, [wColorActive]
	and a
	jr z, .oam
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr z, .oam
	ldh a, [rLY]
	cp 144
	jr c, .afterGraphics
	cp 152
	jr nc, .afterGraphics
.oam
	call hDMARoutine
.afterGraphics
	ld a, BANK(PrepareOAMData)
	ldh [hLoadedROMBank], a
	ld [rROMB], a
	call PrepareOAMData

	; VBlank-sensitive operations end.
	call TrackPlayTime ; keep track of time played

	call Random
	call ReadJoypad

	ldh a, [hVBlankOccurred]
	and a
	jr z, .skipZeroing
	xor a
	ldh [hVBlankOccurred], a

.skipZeroing
	ldh a, [hFrameCounter]
	and a
	jr z, .skipDec
	dec a
	ldh [hFrameCounter], a

.skipDec
	call FadeOutAudio

	ld a, BANK(Music_DoLowHealthAlarm)
	call BankswitchCommon
	call Music_DoLowHealthAlarm
	ld a, BANK(Audio1_UpdateMusic)
	call BankswitchCommon
	call Audio1_UpdateMusic

	call SerialFunction

	ld a, [wVBlankSavedROMBank]
	ldh [hLoadedROMBank], a
	ld [rROMB], a

	pop af
	ldh [rVBK], a

	pop hl
	pop de
	pop bc
	pop af
	reti


DelayFrame::
	call ColorPrepare
; Wait for the next vblank interrupt.
; As a bonus, this saves battery.

DEF NOT_VBLANKED EQU 1

	ld a, NOT_VBLANKED
	ldh [hVBlankOccurred], a
.halt
	halt
	ldh a, [hVBlankOccurred]
	and a
	jr nz, .halt
	ret
