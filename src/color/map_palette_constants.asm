	const_def
	const INTRO_GRAY        ; 00: used only when booting up the game
	const OUTDOOR_MASONRY      ; 01
	const OUTDOOR_RED       ; 02
	const OUTDOOR_GREEN     ; 03
	const OUTDOOR_BLUE      ; 04
	const OUTDOOR_GLASS    ; 05
	const OUTDOOR_BROWN     ; 06
	const OUTDOOR_ROOF      ; 07
	const CRYS_TEXTBOX      ; 08
	const INDOOR_STONE       ; 09
	const INDOOR_RED        ; 0A
	const INDOOR_GREEN      ; 0B
	const INDOOR_BLUE       ; 0C
	const INDOOR_YELLOW     ; 0D
	const INDOOR_BROWN      ; 0E
	const INDOOR_STEEL ; 0F
	const MAP_PALETTE_10    ; 10
	const MAP_PALETTE_11    ; 11
	const MAP_PALETTE_12    ; 12
	const MAP_PALETTE_13    ; 13
	const MAP_PALETTE_14    ; 14
	const MAP_PALETTE_15    ; 15
	const MAP_PALETTE_16    ; 16
	const CAVE_GRAY         ; 17
	const CAVE_RED          ; 18
	const CAVE_GREEN        ; 19
	const CAVE_BLUE         ; 1A
	const CAVE_YELLOW       ; 1B
	const CAVE_BROWN        ; 1C
	const CAVE_LIGHT_BLUE   ; 1D
	const BENCH_GUY_PAL     ; 1E
	const PC_POKEBALL_PAL   ; 1F: doubles as textbox palette for some areas
	const FOREST_ROCKS      ; 20
	const FOREST_TREES      ; 21
	const ALT_TEXTBOX_PAL   ; 22: used in areas with skeleton pokemon
	const INDOOR_PURPLE     ; 23

	const INDOOR_WOOD
	const INDOOR_TEAL
	const INDOOR_SANDSTONE
	const INDOOR_LAVENDER
	const OUTDOOR_FLOWERS
DEF NUM_MAP_PALETTES EQU const_value

; Named to make tileset palette assignments consistent with Pokecrystal
	const_def
	const PAL_BG_GRAY      ; 00
	const PAL_BG_RED       ; 01
	const PAL_BG_GREEN     ; 02
	const PAL_BG_WATER     ; 03
	const PAL_BG_YELLOW    ; 04
	const PAL_BG_BROWN     ; 05
	const PAL_BG_ROOF      ; 06
	const PAL_BG_TEXT      ; 07

; Used when you want a tile to display above the Player and NPCs
	const_def $80
	const PAL_BG_PRIORITY_GRAY   ; 80
	const PAL_BG_PRIORITY_RED    ; 81
	const PAL_BG_PRIORITY_GREEN  ; 82
	const PAL_BG_PRIORITY_WATER  ; 83
	const PAL_BG_PRIORITY_YELLOW ; 84
	const PAL_BG_PRIORITY_BROWN  ; 85
	const PAL_BG_PRIORITY_ROOF   ; 86
	const PAL_BG_PRIORITY_TEXT   ; 87
