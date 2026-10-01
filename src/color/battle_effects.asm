; Selected Crystal effects, compiled to OAM timelines for Yellow's battle engine.
; Picture graphics at $9000/$9310 and their BG palettes are never repurposed.
; All working variables belong to Yellow's existing animation scratch space.
Gen2TryAnimation::
	ldh a, [hOnCGB]
	and a
	ret z
	ld a, [wIsInBattle]
	and a
	ret z
	ld a, [wAnimationID]
	ld b, a
	ld hl, Gen2EffectTable
.find
	ld a, [hli]
	and a
	ret z ; carry clear: use Yellow's original animation
	cp b
	jr z, .found
	inc hl
	inc hl
	jr .find
.found
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld a, [hli]
	ld c, a ; number of graphics tiles
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a
	push hl
	ld hl, vSprites tile $31
	ld b, BANK(Gen2GFX_THUNDERSHOCK)
	call CopyVideoData
	pop hl
	ldh a, [hWhoseTurn]
	and a
	jr z, .timeline
	inc hl
	inc hl
.timeline
	ld a, [hli]
	ld h, [hl]
	ld l, a
	push hl
	call Gen2LoadEffectPalettes
	pop hl
.frame
	ld a, [hli]
	and a
	jr z, .done
	ld [wSubAnimFrameDelay], a
	ld a, [hli]
	push hl
	call Gen2FrameActions
	pop hl
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a
	push hl
	push de
	call ClearSprites
	pop hl
	ld a, [hli]
	and a
	jr z, .wait
	ld c, a
	ld b, 0
	ld de, wShadowOAM
	call CopyData
.wait
	ld a, [wSubAnimFrameDelay]
	ld c, a
	call DelayFrames
	pop hl
	jr .frame
.done
	call ClearSprites
	call DelayFrame ; remove effects from hardware OAM before restoring palettes
	ldh a, [rOBP1]
	cpl
	ld [wLastOBP1], a
	call UpdateCGBPal_OBP1
	scf ; handled; the usual damage/recoil/status logic still follows
	ret

Gen2FrameActions:
	; Actions run before their OAM frame. Preserve the flag byte across farcalls.
	push af
	bit 0, a
	jr z, .hide
	farcall Gen2PlayMoveSound
.hide
	pop af
	push af
	bit 1, a
	jr z, .show
	farcall AnimationHideMonPic
	call Delay3 ; finish erasing the picture before the short speed-line effect
.show
	pop af
	push af
	bit 2, a
	jr z, .lunge
	farcall AnimationShowMonPic
.lunge
	pop af
	push af
	bit 3, a
	jr z, .reset
	farcall AnimationMoveMonHorizontally
.reset
	pop af
	bit 4, a
	ret z
	farjp AnimationResetMonPosition

Gen2LoadEffectPalettes:
	ld hl, .gray
	ld de, wCGBPal
	ld bc, PAL_SIZE
	call CopyData
	ld c, 6
	farcall ColorTransferEffectPalette
	ld hl, .yellow
	ld de, wCGBPal
	ld bc, PAL_SIZE
	call CopyData
	ld c, 7
	farjp ColorTransferEffectPalette
.gray
	RGB 31,31,31, 25,25,25, 13,13,13, 0,0,0
.yellow
	RGB 31,31,31, 31,31,7, 31,16,1, 0,0,0

INCLUDE "color/battle_effects_data.asm"
