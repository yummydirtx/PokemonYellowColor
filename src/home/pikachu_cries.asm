; Each bit originally lasts 180 T-cycles, including calls and byte boundaries.
; This delay is 52 T-cycles at 1x and 232 at 2x: it adds exactly 180,
; giving 360 CPU cycles per bit at 2x and preserving the recorded voice's pitch.
; E is zero at 1x, $80 at 2x. Neither path changes BC, HL or the sample in D.
MACRO pcm_sample_delay
	ld a, e
	and a
	ld a, 1
	jr z, .wait\@
	ld a, 12
.wait\@
	nop
	nop
	nop
.loop\@
	dec a
	jr nz, .loop\@
ENDM

PlayPikachuPCM::
	vc_hook Unknown_PlayPikachuPCM
	push de
	; Cache the actual CPU speed; DMG reads of KEY1 are not meaningful.
	ldh a, [hOnCGB]
	and a
	jr z, .speedKnown
	ldh a, [rKEY1]
	and $80
.speedKnown
	ld e, a
	ldh a, [hLoadedROMBank]
	push af
	ld a, b
	call BankswitchCommon
	ld a, [hli]
	ld c, a
	ld a, [hli]
	ld b, a
.loop
	ld a, [hli]
	ld d, a
	pcm_sample_delay

REPT 7
	call LoadNextSoundClipSample
	call PlaySoundClipSample
ENDR

	call LoadNextSoundClipSample
	dec bc
	ld a, c
	or b
	jr nz, .loop
	pop af
	call BankswitchCommon
	pop de
	ret

LoadNextSoundClipSample::
	ld a, d
	and $80
	srl a
	srl a
	ldh [rAUD3LEVEL], a
	sla d
	ret

PlaySoundClipSample::
	pcm_sample_delay
	ret
