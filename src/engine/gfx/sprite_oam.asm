PrepareOAMData::
; Determine OAM data for currently visible
; sprites and write it to wShadowOAM.
; Yellow code has been changed to use registers more efficiently
; as well as tweaking the code to show cgb palettes

	ld a, [wUpdateSpritesEnabled]
	dec a
	jr z, .updateEnabled

	cp -1
	ret nz
	ld [wUpdateSpritesEnabled], a
	jp HideSprites

.updateEnabled
	xor a
	ldh [hOAMBufferOffset], a

.spriteLoop
	ldh [hSpriteOffset2], a

	ld e, a
	ld d, HIGH(wSpriteStateData1)

	ld a, [de] ; [x#SPRITESTATEDATA1_PICTUREID]
	and a
	jp z, .nextSprite

	inc e
	inc e
	ld a, [de] ; [x#SPRITESTATEDATA1_IMAGEINDEX]
	ld [wSavedSpriteImageIndex], a
	cp $ff ; off-screen (don't draw)
	jr nz, .visible

	call GetSpriteScreenXY
	jp .nextSprite

.visible
	call ColorSpritePalette
	cp $a0 ; is the sprite unchanging like an item ball or boulder?
	jr c, .usefacing

; unchanging
	ld a, $0
	jr .next

.usefacing
	and $f

.next
; read the entry from the table
	ld c, a
	ld b, 0
	ld hl, SpriteFacingAndAnimationTable
	add hl, bc
	add hl, bc
	ld a, [hli]
	ld h, [hl]
	ld l, a
; get sprite priority
	push de
	inc d
	ld a, e
	add $5
	ld e, a
	ld a, [de] ; [x#SPRITESTATEDATA2_GRASSPRIORITY]
	and $80
	ldh [hSpritePriority], a ; temp store sprite priority
	pop de


	call GetSpriteScreenXY

	ldh a, [hOAMBufferOffset]
	add [hl]
	cp $a0
	jr z, .hidden
	jr nc, .asm_4a41
.hidden
	call Func_4a7b
	ld [wSavedSpriteImageIndex], a
	ldh a, [hOAMBufferOffset]

	ld e, a
	ld d, HIGH(wShadowOAM)

.tileLoop
	ld a, [hli]
	ld c, a
.loop
	ldh a, [hSpriteScreenY]   ; temp for sprite Y position
	add $10                  ; Y=16 is top of screen (Y=0 is invisible)
	add [hl]                 ; add Y offset from table
	ld [de], a               ; write new sprite OAM Y position
	inc hl
	inc e
	ldh a, [hSpriteScreenX]   ; temp for sprite X position
	add $8                   ; X=8 is left of screen (X=0 is invisible)
	add [hl]                 ; add X offset from table
	ld [de], a
	inc hl
	inc e
	ld a, [wSavedSpriteImageIndex]
	add [hl]
	cp $80
	jr c, .asm_4a1c
	ld b, a
	ldh a, [hPikachuSpriteVRAMOffset]
	add b
.asm_4a1c
	ld [de], a ; tile id
	inc hl
	inc e
	ld a, [hl]
	bit BIT_SPRITE_UNDER_GRASS, a
	jr z, .skipPriority
	ldh a, [hSpritePriority]
	or [hl]
.skipPriority
	and $f0
	bit B_OAM_PAL1, a
	jr z, .spriteusesOBP0
	or OAM_HIGH_PALS
.spriteusesOBP0
	ld b, a
	ld a, [wColorActive]
	and a
	ld a, b
	jr z, .nativePalette
	and $f8
	ld b, a
	ld a, [wColorSpritePal]
	or b
.nativePalette
	ld [de], a
	inc hl
	inc e
	dec c
	jr nz, .loop

	ld a, e
	ldh [hOAMBufferOffset], a
.nextSprite
	ldh a, [hSpriteOffset2]
	add $10
	cp LOW($100)
	jp nz, .spriteLoop

	; Clear unused OAM.
.asm_4a41
	ld a, [wMovementFlags]
	bit BIT_LEDGE_OR_FISHING, a
	ld c, LOW(wShadowOAMEnd)
	jr z, .clear

; Don't clear the last 4 entries because they are used for the shadow in the
; jumping down ledge animation and the rod in the fishing animation.
	ld c, LOW(wShadowOAMSprite36)

.clear
	ldh a, [hOAMBufferOffset]
	cp c
	ret nc
	ld l, a
	ld h, HIGH(wShadowOAM)
	ld a, c
	ld de, $4 ; entry size
	ld b, $a0
.clearLoop
	ld [hl], b
	add hl, de
	cp l
	jr nz, .clearLoop
	ret

GetSpriteScreenXY:
	inc e
	inc e
	ld a, [de] ; [x#SPRITESTATEDATA1_YPIXELS]
	ldh [hSpriteScreenY], a
	inc e
	inc e
	ld a, [de] ; [x#SPRITESTATEDATA1_XPIXELS]
	ldh [hSpriteScreenX], a
	ld a, 4
	add e
	ld e, a
	ldh a, [hSpriteScreenY]
	add 4
	and $f0
	ld [de], a ; [x#SPRITESTATEDATA1_YADJUSTED]
	inc e
	ldh a, [hSpriteScreenX]
	and $f0
	ld [de], a  ; [x#SPRITESTATEDATA1_XADJUSTED]
	ret

Func_4a7b:
	push bc
	ld a, [wSavedSpriteImageIndex]
	swap a                   ; high nybble determines sprite used (0 is always player sprite, next are some npcs)
	and $f

	; Sprites $a and $b have one face (and therefore 4 tiles instead of 12).
	; As a result, sprite $b's tile offset is less than normal.
	cp $b
	jr nz, .notFourTileSprite
	ld a, $a * 12 + 4 ; $7c
	jr .done

.notFourTileSprite
	; a *= 12
	add a
	add a
	ld c, a
	add a
	add c
.done
	pop bc
	ret

INCLUDE "engine/gfx/oam_dma.asm"

_IsTilePassable::
	ld hl, wTilesetCollisionPtr ; pointer to list of passable tiles
	ld a, [hli]
	ld h, [hl]
	ld l, a ; hl now points to passable tiles
.loop
	ld a, [hli]
	cp $ff
	jr z, .tileNotPassable
	cp c
	jr nz, .loop
	xor a
	ret
.tileNotPassable
	scf
	ret

INCLUDE "data/tilesets/collision_tile_ids.asm"

ColorSpritePalette:
	push af
	push bc
	push hl
	ldh a, [hSpriteOffset2]
	cp $f0
	ld a, 5 ; Yellow uses dynamic picture IDs for the follower slot
	jr z, .store
	ldh a, [hSpriteOffset2]
	ld l, a
	ld h, HIGH(wSpriteStateData1)
	ld a, [hl]
	ld c, a
	ld b, 0
	ld hl, ColorSpritePaletteTable
	add hl, bc
	ld a, [hl]
.store
	ld [wColorSpritePal], a
	pop hl
	pop bc
	pop af
	ret

; Three opaque OBJ colors: skin/fur, clothing, and outline.
DEF COLOR_OBJ_RED EQU 0
DEF COLOR_OBJ_BLUE EQU 1
DEF COLOR_OBJ_GREEN EQU 2
DEF COLOR_OBJ_BROWN EQU 3
DEF COLOR_OBJ_PINK EQU 4
DEF COLOR_OBJ_YELLOW EQU 5
DEF COLOR_OBJ_WHITE EQU 6
DEF COLOR_OBJ_PURPLE EQU 7

ColorSpritePaletteTable:
	table_width 1, ColorSpritePaletteTable
	db COLOR_OBJ_WHITE ; SPRITE_NONE
	db COLOR_OBJ_RED ; SPRITE_RED
	db COLOR_OBJ_BLUE ; SPRITE_BLUE
	db COLOR_OBJ_WHITE ; SPRITE_OAK
	db COLOR_OBJ_BLUE ; SPRITE_YOUNGSTER
	db COLOR_OBJ_BROWN ; SPRITE_MONSTER
	db COLOR_OBJ_PINK ; SPRITE_COOLTRAINER_F
	db COLOR_OBJ_BLUE ; SPRITE_COOLTRAINER_M
	db COLOR_OBJ_PINK ; SPRITE_LITTLE_GIRL
	db COLOR_OBJ_BROWN ; SPRITE_BIRD
	db COLOR_OBJ_BLUE ; SPRITE_MIDDLE_AGED_MAN
	db COLOR_OBJ_BROWN ; SPRITE_GAMBLER
	db COLOR_OBJ_BLUE ; SPRITE_SUPER_NERD
	db COLOR_OBJ_PINK ; SPRITE_GIRL
	db COLOR_OBJ_BROWN ; SPRITE_HIKER
	db COLOR_OBJ_PINK ; SPRITE_BEAUTY
	db COLOR_OBJ_BROWN ; SPRITE_GENTLEMAN
	db COLOR_OBJ_PINK ; SPRITE_DAISY
	db COLOR_OBJ_BLUE ; SPRITE_BIKER
	db COLOR_OBJ_BLUE ; SPRITE_SAILOR
	db COLOR_OBJ_WHITE ; SPRITE_COOK
	db COLOR_OBJ_BLUE ; SPRITE_BIKE_SHOP_CLERK
	db COLOR_OBJ_BROWN ; SPRITE_MR_FUJI
	db COLOR_OBJ_BROWN ; SPRITE_GIOVANNI
	db COLOR_OBJ_PURPLE ; SPRITE_ROCKET
	db COLOR_OBJ_PURPLE ; SPRITE_CHANNELER
	db COLOR_OBJ_BLUE ; SPRITE_WAITER
	db COLOR_OBJ_PINK ; SPRITE_SILPH_WORKER_F
	db COLOR_OBJ_PINK ; SPRITE_MIDDLE_AGED_WOMAN
	db COLOR_OBJ_PINK ; SPRITE_BRUNETTE_GIRL
	db COLOR_OBJ_RED ; SPRITE_LANCE
	db COLOR_OBJ_RED ; SPRITE_UNUSED_RED_1
	db COLOR_OBJ_WHITE ; SPRITE_SCIENTIST
	db COLOR_OBJ_PURPLE ; SPRITE_ROCKER
	db COLOR_OBJ_BLUE ; SPRITE_SWIMMER
	db COLOR_OBJ_BROWN ; SPRITE_SAFARI_ZONE_WORKER
	db COLOR_OBJ_BLUE ; SPRITE_GYM_GUIDE
	db COLOR_OBJ_BROWN ; SPRITE_GRAMPS
	db COLOR_OBJ_BLUE ; SPRITE_CLERK
	db COLOR_OBJ_BROWN ; SPRITE_FISHING_GURU
	db COLOR_OBJ_PURPLE ; SPRITE_GRANNY
	db COLOR_OBJ_PINK ; SPRITE_NURSE
	db COLOR_OBJ_PINK ; SPRITE_LINK_RECEPTIONIST
	db COLOR_OBJ_BROWN ; SPRITE_SILPH_PRESIDENT
	db COLOR_OBJ_BLUE ; SPRITE_SILPH_WORKER_M
	db COLOR_OBJ_BROWN ; SPRITE_WARDEN
	db COLOR_OBJ_BLUE ; SPRITE_CAPTAIN
	db COLOR_OBJ_BLUE ; SPRITE_FISHER
	db COLOR_OBJ_PURPLE ; SPRITE_KOGA
	db COLOR_OBJ_BLUE ; SPRITE_GUARD
	db COLOR_OBJ_RED ; SPRITE_UNUSED_RED_2
	db COLOR_OBJ_PINK ; SPRITE_MOM
	db COLOR_OBJ_BROWN ; SPRITE_BALDING_GUY
	db COLOR_OBJ_BLUE ; SPRITE_LITTLE_BOY
	db COLOR_OBJ_RED ; SPRITE_UNUSED_RED_3
	db COLOR_OBJ_BLUE ; SPRITE_GAMEBOY_KID
	db COLOR_OBJ_PINK ; SPRITE_FAIRY
	db COLOR_OBJ_PURPLE ; SPRITE_AGATHA
	db COLOR_OBJ_BROWN ; SPRITE_BRUNO
	db COLOR_OBJ_BLUE ; SPRITE_LORELEI
	db COLOR_OBJ_WHITE ; SPRITE_SEEL
	db COLOR_OBJ_YELLOW ; SPRITE_PIKACHU
	db COLOR_OBJ_BLUE ; SPRITE_OFFICER_JENNY
	db COLOR_OBJ_YELLOW ; SPRITE_SANDSHREW
	db COLOR_OBJ_GREEN ; SPRITE_ODDISH
	db COLOR_OBJ_GREEN ; SPRITE_BULBASAUR
	db COLOR_OBJ_PINK ; SPRITE_JIGGLYPUFF
	db COLOR_OBJ_PINK ; SPRITE_CLEFAIRY
	db COLOR_OBJ_PINK ; SPRITE_CHANSEY
	db COLOR_OBJ_RED ; SPRITE_JESSIE
	db COLOR_OBJ_PURPLE ; SPRITE_JAMES
	db COLOR_OBJ_RED ; SPRITE_POKE_BALL
	db COLOR_OBJ_BROWN ; SPRITE_FOSSIL
	db COLOR_OBJ_BROWN ; SPRITE_BOULDER
	db COLOR_OBJ_WHITE ; SPRITE_PAPER
	db COLOR_OBJ_RED ; SPRITE_POKEDEX
	db COLOR_OBJ_WHITE ; SPRITE_CLIPBOARD
	db COLOR_OBJ_BLUE ; SPRITE_SNORLAX
	db COLOR_OBJ_BROWN ; SPRITE_UNUSED_OLD_AMBER
	db COLOR_OBJ_BROWN ; SPRITE_OLD_AMBER
	db COLOR_OBJ_BROWN ; SPRITE_UNUSED_GAMBLER_ASLEEP_1
	db COLOR_OBJ_BROWN ; SPRITE_UNUSED_GAMBLER_ASLEEP_2
	db COLOR_OBJ_BROWN ; SPRITE_GAMBLER_ASLEEP
	assert_table_length NUM_SPRITES + 1
