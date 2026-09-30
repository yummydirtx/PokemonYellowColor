ColorRoofPalettes:
	dw PalletRoof
	dw ViridianRoof
	dw PewterRoof
	dw CeruleanRoof
	dw LavenderRoof
	dw VermilionRoof
	dw CeladonRoof
	dw FuchsiaRoof
	dw CinnabarRoof
	dw IndigoRoof
	dw SaffronRoof
	dw PalletRoof    ; unused map $0B
	dw PalletRoof    ; ROUTE_1
	dw ViridianRoof  ; ROUTE_2
	dw PewterRoof    ; ROUTE_3
	dw PewterRoof    ; ROUTE_4
	dw SaffronRoof   ; ROUTE_5
	dw VermilionRoof ; ROUTE_6 (hardcoded to use SaffronRoof for top 2 rows)
	dw SaffronRoof   ; ROUTE_7
	dw SaffronRoof   ; ROUTE_8
	dw LavenderRoof  ; ROUTE_9
	dw LavenderRoof  ; ROUTE_10
	dw VermilionRoof ; ROUTE_11
	dw VermilionRoof ; ROUTE_12
	dw FuchsiaRoof   ; ROUTE_13
	dw FuchsiaRoof   ; ROUTE_14
	dw FuchsiaRoof   ; ROUTE_15
	dw CeladonRoof   ; ROUTE_16
	dw CeladonRoof   ; ROUTE_17
	dw CeladonRoof   ; ROUTE_18
	dw CinnabarRoof  ; ROUTE_19
	dw CinnabarRoof  ; ROUTE_20
	dw CinnabarRoof  ; ROUTE_21
	dw IndigoRoof    ; ROUTE_22
	dw IndigoRoof    ; ROUTE_23
	dw CeruleanRoof  ; ROUTE_24
	dw CeruleanRoof  ; ROUTE_25

PalletRoof:
	RGB 27,31,27
	RGB 31,31,31
	RGB 24,24,24
	RGB 7,7,7

ViridianRoof:
	RGB 27,31,27
	RGB 0,29,7
	RGB 0,24,7
	RGB 7,7,7

PewterRoof:
	RGB 27,31,27
	RGB 24,25,26
	RGB 20,17,19
	RGB 7,7,7

CeruleanRoof:
	RGB 27,31,27
	RGB 14,24,31
	RGB 14,20,26
	RGB 7,7,7

LavenderRoof:
	RGB 27,31,27
	RGB 23,12,31
	RGB 19,9,24
	RGB 7,7,7

VermilionRoof:
	RGB 27,31,27
	RGB 29,8,0
	RGB 22,8,0
	RGB 7,7,7

CeladonRoof:
	RGB 27,31,27
	RGB 15,26,19
	RGB 3,20,11
	RGB 7,7,7

FuchsiaRoof:
	RGB 27,31,27
	RGB 31,3,18
	RGB 25,3,12
	RGB 7,7,7

CinnabarRoof:
	RGB 27,31,27
	RGB 29,0,0
	RGB 22,0,0
	RGB 7,7,7

IndigoRoof:
	RGB 27,31,27
	RGB 16,0,31
	RGB 10,0,25
	RGB 7,7,7

SaffronRoof:
	RGB 27,31,27
	RGB 31,27,0
	RGB 28,22,0
	RGB 7,7,7
