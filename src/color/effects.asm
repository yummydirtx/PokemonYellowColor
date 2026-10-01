SECTION "Color effects", ROMX, BANK[$46]

ColorFinishText::
	ld a, [wColorActive]
	and a
	ret z
	ldh a, [hAutoBGTransferEnabled]
	and a
	ret z
	push bc
	; Consume a possibly stale queued portion, then all three fresh portions.
	; A deferred VBlank must not count as a completed transfer.
	ld c, 4
.portion
	call DelayFrame
	ld a, [wColorAutoReady]
	and a
	jr nz, .portion
	dec c
	jr nz, .portion
	pop bc
	ret
