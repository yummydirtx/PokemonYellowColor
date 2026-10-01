SECTION "CGB outdoor materials", ROMX, BANK[$48]

; Called with LCD off by every map load/reload. Only substitute graphics;
; tile numbers, blocks, collision and native tileset pointers stay unchanged.
ColorLoadTilesetTilePatternData::
	ldh a, [hOnCGB]
	and a
	jr z, .native
	ld a, [wCurMapTileset]
	ld hl, ColorTerrainOverworld
	cp OVERWORLD
	jr z, .color
	ld hl, ColorTerrainForest
	cp FOREST
	jr z, .color
.native
	ld a, [wTilesetGfxPtr]
	ld l, a
	ld a, [wTilesetGfxPtr + 1]
	ld h, a
	ld de, vTileset
	ld bc, MAP_TILESET_SIZE tiles
	ld a, [wTilesetBank]
	jp FarCopyData
.color
	ld de, vTileset
	ld bc, MAP_TILESET_SIZE tiles
	jp CopyData

INCLUDE "color/terrain_data.asm"
