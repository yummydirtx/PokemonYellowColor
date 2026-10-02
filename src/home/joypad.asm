Joypad::
	; Letter delays and text prompts poll input without calling DelayFrame.
	; Keep their automatic tile/attribute transfers supplied, once per consumed
	; buffer. Never overwrite a transfer still waiting for a safe VBlank.
	push af
	ldh a, [hAutoBGTransferEnabled]
	and a
	jr z, .input
	ld a, [wColorAutoReady]
	and 1
	call z, ColorPrepare
.input
	pop af
	homejp _Joypad

ReadJoypad::
	homejp ReadJoypad_
