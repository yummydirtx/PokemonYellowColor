#!/usr/bin/env python3
"""Check menu whiteouts and actual scrolling tile IDs with SameBoy's LCD/DMA.

The edge fixture deliberately interrupts a pending redraw before preparation.
Walking tests use normal button input after test-only map positioning. Named
bank-one WRAM is read directly: frame boundaries can fall inside SVBK=2 work.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
from PIL import Image
from sameboy import SameBoy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom', default='src/pokeyellow.gbc')
parser.add_argument('--out', default='build/verification/rendering')
parser.add_argument('--only', choices=['all','menus','scrolling','edges'], default='all')
args = parser.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
p = SameBoy(args.rom, 'build/verification/test.sav')
p.continue_game()
state = str(out / 'start.state').encode()
assert p.lib.sb_save(state) == 0
report = {'rom_sha256': hashlib.sha256(Path(args.rom).read_bytes()).hexdigest(),
          'model': 'SameBoy CGB-E', 'menus': [], 'scrolling': [], 'edge_transfers': []}


def ram(name):
    address = p.addr(name) if isinstance(name, str) else name
    if 0xc000 <= address < 0xe000:
        return p.lib.sb_memory(1)[address - 0xc000]
    return p.get(address)


def word(name):
    return ram(name) | ram(p.addr(name)+1) << 8


def image():
    raw = ctypes.string_at(p.lib.sb_pixels(), 160*144*4)
    return Image.frombytes('RGBA', (160,144), raw, 'raw', 'BGRA').convert('RGB')


def restore():
    assert p.lib.sb_load(state) == 0
    p.in_fixture = False


# The fixture save has no Pokédex; party/card/options are entries 0/2/4.
for map_name, mid, width, x, y in ([('pallet',0,10,10,12), ('forest',51,17,16,18)] if args.only in ['all','menus'] else []):
    for menu, selection in [('party',0), ('card',2), ('options',4)]:
        restore()
        p.warp(mid,width,x,y)
        p.press('start',4,60)
        p.sync()
        p.put('wCurrentMenuItem',selection)
        p.press('a',4,120)
        p.watch(['ColorRepaintMaps','LoadGBPal'])
        p.lib.sb_clear_write_counts()
        frames, whiteout_frames, inside, previous = [], 0, False, 0
        for frame in range(160):
            if frame in [0,90]: p.key('b',True)
            if frame in [4,94]: p.key('b',False)
            p.tick(1)
            events = p.events()
            for e in events[previous:]:
                if e['name']=='ColorRepaintMaps': inside=True
                if e['name']=='LoadGBPal': inside=False
            previous=len(events)
            im=image()
            if inside:
                # A complete frame of the whiteout must hide the old menus and
                # every terrain palette, even when color zero is grass/cream.
                assert len(im.getcolors(160*144) or []) == 1 and im.getpixel((0,0))==(255,255,255), (map_name,menu,frame,'visible restoration artifact')
                whiteout_frames+=1
            if map_name=='pallet' and menu=='party' and frame%2==0: frames.append(im.resize((480,432),Image.Resampling.NEAREST))
        assert whiteout_frames>=3 or menu=='options', (map_name,menu,'whiteout not exercised')
        assert ram('wColorActive')==1 and p.get('hWY')==144
        bad=[p.lib.sb_bad_vram_writes(),p.lib.sb_bad_palette_writes()]
        assert bad==[0,0], (map_name,menu,bad)
        report['menus'].append({'map':map_name,'menu':menu,'uniform_white_frames':whiteout_frames,'blocked_writes':bad})
        if frames:
            times=[round(i*2*70224/4194304*100)*10 for i in range(len(frames)+1)]
            frames[0].save(out/'menu-return.gif',save_all=True,append_images=frames[1:],duration=[b-a for a,b in zip(times,times[1:])],loop=0)


def check_visible():
    vp=word('wMapViewVRAMPointer')
    sx,sy=p.get(0xff43),p.get(0xff42)
    dx=((sx-(vp%32)*8+128)%256)-128
    dy=((sy-((vp-0x9800)//32)*8+128)%256)-128
    ptr=word('wCurrentTileBlockMapViewPointer')
    stride=ram('wCurMapWidth')+6
    blocks=ram('wTilesetBank')*0x4000+(word('wTilesetBlocksPtr')&0x3fff)
    rom,vram=p.lib.sb_memory(0),p.lib.sb_memory(3)
    palbank=p.symbols['ColorTilesetPointers'][0]*0x4000
    pals=palbank+((ram('wColorTilesHigh')<<8)&0x3fff)
    for y in range(18+bool(sy%8)):
        for x in range(20+bool(sx%8)):
            tx=x+2*ram('wXBlockCoord')+dx//8
            ty=y+2*ram('wYBlockCoord')+dy//8
            block=ram(ptr+(ty//4)*stride+tx//4)
            expected=rom[blocks+block*16+(ty%4)*4+tx%4]
            va=0x1800+((sy//8+y)%32)*32+((sx//8+x)%32)
            assert vram[va]==expected, ('tile',x,y,vram[va],expected,ram('wXCoord'),ram('wYCoord'),sx,sy)
            assert vram[0x2000+va]==rom[pals+expected], ('attribute',x,y)


for name,mid,width,x,y in ([('forest',51,17,16,18),('pallet',0,10,10,12),('route1',12,10,10,16)] if args.only in ['all','scrolling'] else []):
    restore()
    p.warp(mid,width,x,y)
    p.sync()
    p.put(p.addr('wEventFlags')+0xac,0x7c) # Forest trainers already defeated.
    p.put('wGrassRate',0)
    p.lib.sb_clear_write_counts()
    positions=set()
    frames=0
    for key in ['left','right','up','down','right','left','down','up']*4:
        p.key(key,True)
        for _ in range(80):
            p.tick(1)
            check_visible()
            positions.add((p.get(0xff43),p.get(0xff42)))
            frames+=1
        p.key(key,False)
    bad=[p.lib.sb_bad_vram_writes(),p.lib.sb_bad_palette_writes()]
    assert bad==[0,0], (name,bad)
    assert len(positions)>25, (name,'not moving')
    report['scrolling'].append({'map':name,'frames':frames,'distinct_scroll_positions':len(positions),'visible_tile_and_attribute_mismatches':0,'blocked_writes':bad})


# Force the narrow race: a request exists, but its buffer still contains the
# previous edge. Neither VRAM plane may change until preparation has completed.
restore()
p.warp(51,17,16,18)
p.call('DisableLCD')
for name in ['hAutoBGTransferEnabled','hVBlankCopyBGSource','hTileAnimations','hRedrawRowOrColumnMode','wColorAutoReady']:
    p.put(name,0)


def call(name):
    p.begin_call(name,scratch='wSpriteStateData1')
    for _ in range(60):
        p.tick(1)
        if p.call_finished(): return
    raise AssertionError((name,'did not return'))


for mode in ([1,2] if args.only in ['all','edges'] else []):
    # Include both axes of the 32x32 tilemap torus and every legal even column.
    for row in [0,14,30]:
        for col in range(0,32,2):
            dest=0x9800+row*32+col
            source=[(i*7+row+col)%96 for i in range(40)]
            for i,value in enumerate(source):p.put(p.addr('wRedrawRowOrColumnSrcTiles')+i,value)
            p.put('wColorAutoReady',0)
            p.put('hRedrawRowOrColumnMode',mode)
            p.put('hRedrawRowOrColumnDest',dest&255)
            p.put(p.addr('hRedrawRowOrColumnDest')+1,dest>>8)
            before=bytes(p.lib.sb_memory(3)[0x1800:0x4000])
            call('ColorVBlankAll')
            assert bytes(p.lib.sb_memory(3)[0x1800:0x4000])==before, (mode,row,col,'unprepared edge was uploaded')
            assert p.get('hRedrawRowOrColumnMode')==mode
            call('ColorPrepareScroll')
            assert p.get('wColorAutoReady')&2
            call('ColorVBlankAll')
            assert p.get('hRedrawRowOrColumnMode')==0 and p.get('wColorAutoReady')==0
            rom,vram=p.lib.sb_memory(0),p.lib.sb_memory(3)
            pals=p.symbols['ColorTilesetPointers'][0]*0x4000+((p.get('wColorTilesHigh')<<8)&0x3fff)
            for i in range(36 if mode==1 else 40):
                yy,xx=(row+i//2,col+i%2) if mode==1 else (row+i//20,col+i%20)
                va=0x1800+(yy%32)*32+xx%32
                assert vram[va]==source[i], (mode,row,col,i,'wrong tile')
                assert vram[0x2000+va]==rom[pals+source[i]], (mode,row,col,i,'wrong attribute')
            report['edge_transfers'].append({'mode':'column' if mode==1 else 'row','row':row,'column':col,'unprepared_request_retained':True,'prepared_tile_and_attribute_bytes_match':True})
p.close()
report['limitations']=['RAM positioning and deterministic race fixtures; the reported intermittent forest scene was not reproduced naturally','No physical GBC test']
(out.parent/'rendering.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in report.items()},indent=2))
