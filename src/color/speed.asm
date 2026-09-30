; Normal gameplay runs at 2x CPU speed; the LCD and PSG retain their native rate.
; Map loading calls this with the LCD off. Printer exit may call it with LCD on.
; These maps run serial handshakes in their scripts, before talking to the clerk.
ColorSelectMapSpeed::
	push af
	push bc
	push hl
	ld a, [wCurMap]
	ld b, a
	ld hl, .serialMaps
.map
	ld a, [hli]
	cp $ff
	jr z, .double
	cp b
	jr nz, .map
	call ColorEnableSingleSpeed
	jr .done
.double
	call ColorEnableDoubleSpeed
.done
	pop hl
	pop bc
	pop af
	ret
.serialMaps
	db VIRIDIAN_POKECENTER, PEWTER_POKECENTER, CERULEAN_POKECENTER
	db LAVENDER_POKECENTER, VERMILION_POKECENTER, CELADON_POKECENTER
	db FUCHSIA_POKECENTER, CINNABAR_POKECENTER, SAFFRON_POKECENTER
	db MT_MOON_POKECENTER, ROCK_TUNNEL_POKECENTER, INDIGO_PLATEAU_LOBBY
	db TRADE_CENTER, COLOSSEUM, $ff

ColorEnableDoubleSpeed::
	push af
	ld a, $80
	jr ColorSetSpeed
ColorEnableSingleSpeed::
	push af
	xor a
ColorSetSpeed:
	push bc
	ld b, a
	ldh a, [hOnCGB]
	and a
	jr z, .done
	ldh a, [rKEY1]
	and $80
	cp b
	jr z, .done
	; Mask interrupts without changing IME (initialization calls with IME=0).
	ldh a, [rIE]
	ld c, a
	xor a
	ldh [rIE], a
	ldh a, [rP1]
	push af
	ld a, JOYP_GET_NONE
	ldh [rP1], a
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	jr z, .switch
	; Start an LCD-on switch in mode 3 so the switch does not freeze video
	; memory access in a state that produces black pixels (Pan Docs KEY1).
.waitMode3
	ldh a, [rSTAT]
	and 3
	cp 3
	jr nz, .waitMode3
.switch
	ld a, 1
	ldh [rKEY1], a
	stop
	pop af
	ldh [rP1], a
	ld a, c
	ldh [rIE], a
.done
	pop bc
	pop af
	ret
