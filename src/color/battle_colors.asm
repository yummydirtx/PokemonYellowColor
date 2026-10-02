SECTION "CGB battle materials", ROMX, BANK[$49]

ColorLoadBattleBack::
	ld hl, ColorRedBackTiles
	ld a, [wBattleType]
	cp BATTLE_TYPE_PIKACHU
	jr nz, .oldMan
	ld hl, ColorOakBackTiles
	jr .load
.oldMan
	cp BATTLE_TYPE_OLD_MAN
	jr nz, .load
	ld hl, ColorOldManBackTiles
.load
	push hl
	ld a, BANK("Sprite Buffers")
	call OpenSRAM
	pop hl
	ld de, sSpriteBuffer1
	ld bc, PIC_SIZE tiles
	call CopyData
	ld de, sSpriteBuffer1
	ld hl, vBackPic
	ld b, BANK(ColorRedBackTiles)
	ld c, PIC_SIZE
	call CopyVideoData
	jp CloseSRAM

ColorLoadBallPalette::
	ld hl, .red
	ld a, [wCurItem]
	cp GREAT_BALL
	jr nz, .ultra
	ld hl, .blue
	jr .load
.ultra
	cp ULTRA_BALL
	jr nz, .master
	ld hl, .gold
	jr .load
.master
	cp MASTER_BALL
	jr nz, .safari
	ld hl, .purple
	jr .load
.safari
	cp SAFARI_BALL
	jr nz, .load
	ld hl, .green
.load
	ld de, wCGBPal
	ld bc, PAL_SIZE
	call CopyData
	ld c, 6
	farjp ColorTransferEffectPalette
.red
	RGB 31,31,31, 31,31,31, 31,5,5, 2,2,3
.blue
	RGB 31,31,31, 31,31,31, 5,13,31, 2,2,3
.gold
	RGB 31,31,31, 31,31,31, 31,25,3, 2,2,3
.purple
	RGB 31,31,31, 31,31,31, 23,7,29, 2,2,3
.green
	RGB 31,31,31, 31,31,31, 10,23,7, 2,2,3

INCLUDE "color/battle_trainer_data.asm"
