; Preserve all registers: these hooks run inside timing- and flag-sensitive code.
ColorPrepare::
	push af
	ld a, [wColorActive]
	and a
	jr z, .done
	push bc
	push de
	push hl
	farcall ColorPrepareAuto
	pop hl
	pop de
	pop bc
.done
	pop af
	ret

ColorTransfer::
	ld a, [wColorActive]
	and a
	ret z
	farjp ColorTransferVRAM

ColorMapView::
	push af
	ldh a, [hOnCGB]
	and a
	jr z, .done
	push bc
	push de
	push hl
	farcall ColorMapAttributes
	pop hl
	pop de
	pop bc
.done
	pop af
	ret
