#!/usr/bin/env python3
"""Exercise trainer materials and thrown-ball colors in SameBoy CGB/DMG.

Encounter setup and routine calls are test-only RAM fixtures. Captures come
from the actual ROM renderer; the contact sheet is assembled from those frames.
"""
import ctypes
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from build_battle_colors import colorize, PICTURES
from build_portraits import encode
from sameboy import SameBoy

OUT=Path('build/verification/battle-colors')
OUT.mkdir(parents=True,exist_ok=True)
ROM=Path('src/pokeyellow.gbc')
report={'rom_sha256':hashlib.sha256(ROM.read_bytes()).hexdigest(),'back_loaders':[],'trainers':[],'balls':[]}


def image(p):
    return Image.frombytes('RGBA',(160,144),ctypes.string_at(p.lib.sb_pixels(),160*144*4),'raw','BGRA').convert('RGB')


def run(p,name,registers=None):
    p.begin_call(name,registers,scratch='wSpriteStateData1')
    for _ in range(600):
        p.tick(1)
        if p.call_finished():return
    raise AssertionError((name,'did not return'))


def reload(p,state):
    assert p.lib.sb_load(state)==0
    p.in_fixture=False


def rom_data(p,name,size):
    bank,address=p.symbols[name]
    start=bank*0x4000+(address&0x3fff) if bank else address
    return ROM.read_bytes()[start:start+size]


# The three back pictures must keep their exact original alignment, including
# the separate animated head tiles used during the battle-entry slide.
for dmg in [False,True]:
    p=SameBoy(ROM,'build/verification/test.sav',dmg=dmg)
    p.continue_game()
    p.warp(12,10,10,10)
    for symbol in ['wColorActive','hAutoBGTransferEnabled','hTileAnimations','hRedrawRowOrColumnMode','wUpdateSpritesEnabled']:
        p.put(symbol,0)
    for name,kind in [('Red',0),('Oak',4),('OldMan',1)]:
        p.put('wBattleType',kind)
        p.lib.sb_clear_write_counts()
        run(p,'LoadPlayerBackPic')
        if dmg:
            source=Image.open(f'src/gfx/{PICTURES[name]}.png').convert('L')
            grid=[[0]*56 for _ in range(56)]
            for y in range(48):
                for x in range(48):grid[y+8][x+8]=3-source.getpixel((x,y))//85
        else:grid=colorize(name)
        expected=encode(grid,True)
        vram=p.lib.sb_memory(3)
        assert bytes(vram[p.addr('vBackPic')-0x8000:p.addr('vBackPic')-0x8000+784])==expected,(dmg,name,'body')
        assert bytes(vram[:784])==expected,(dmg,name,'animated head')
        bad=[p.lib.sb_bad_vram_writes(),p.lib.sb_bad_palette_writes()]
        assert bad==[0,0],(dmg,name,bad)
        report['back_loaders'].append({'model':'DMG' if dmg else 'CGB-E','trainer':name,'body_and_animated_head_bytes_match':True,'blocked_writes':bad})
    p.close()

p=SameBoy(ROM,'build/verification/test.sav')
p.continue_game()
p.warp(12,10,10,10)
start=str(OUT/'start.state').encode()
assert p.lib.sb_save(start)==0
thumbnails=[]
for label,trainer in [('Bug Catcher',2),('Lass',3),('Rival',25),('Rocket',30),('Misty',35),('Sabrina',40)]:
    reload(p,start)
    p.sync()
    p.put('wCurOpponent',200+trainer)
    p.put('wTrainerNo',1)
    p.watch(['PrintBeginningBattleText'])
    p.lib.sb_clear_write_counts()
    for frame in range(700):
        p.tick(1)
        if p.events():break
    else:raise AssertionError((label,'no encounter'))
    p.tick(180)
    assert p.get('wIsInBattle')==2
    assert p.get('wEnemyMonSpecies2')==0
    palette_id=rom_data(p,'TrainerPalettes',48)[trainer]
    expected=rom_data(p,'CGBBasePalettes',256*8)[palette_id*8:palette_id*8+8]
    assert bytes(p.lib.sb_memory(8)[24:32])==expected,(label,'front palette')
    bad=[p.lib.sb_bad_vram_writes(),p.lib.sb_bad_palette_writes()]
    assert bad==[0,0],(label,bad)
    im=image(p)
    im.resize((480,432),Image.Resampling.NEAREST).save(OUT/(label.lower().replace(' ','-')+'.png'))
    thumbnails.append((label,im))
    report['trainers'].append({'trainer':label,'actual_encounter':True,'palette_matches':True,'blocked_writes':bad})

# A real wild encounter supplies the normal animation tiles, HUD and sprites.
reload(p,start)
p.put('wCurOpponent',165)
p.put('wCurEnemyLevel',5)
p.watch(['DisplayBattleMenu'])
for frame in range(1500):
    p.tick(1)
    if p.events():break
    if frame%60==0:p.press('b',4,0)
else:raise AssertionError('No wild battle menu')
p.tick(8)
battle=str(OUT/'wild.state').encode()
assert p.lib.sb_save(battle)==0
BALLS=[('Poke',4,(31,5,5)),('Great',3,(5,13,31)),('Ultra',2,(31,25,3)),('Master',1,(23,7,29)),('Safari',8,(10,23,7))]
ball_tiles={0x33,0x43,0x37,0x38,0x47,0x48}
for label,item,rgb in BALLS:
    for outcome,anim_data,is_battle in [('caught',0x43,1),('breakout',0x63,1),('blocked',0x43,2)]:
        reload(p,battle)
        for symbol,value in [('wCurItem',item),('wAnimationID',0xc1),('wPokeBallAnimData',anim_data),('wIsInBattle',is_battle),('hWhoseTurn',0)]:p.put(symbol,value)
        # TOSS_ANIM follows SLIDE_DOWN_ANIM at $c1 in Yellow.
        p.lib.sb_clear_write_counts()
        p.begin_call('MoveAnimation',scratch='wSpriteStateData1')
        caps=set();positions=set();frames=[];ball_frames=0;best=None
        for frame in range(800):
            p.tick(1)
            oam=list(p.lib.sb_memory(7)[:160])
            balls=[oam[i:i+4] for i in range(0,160,4) if 0<oam[i]<160 and 0<oam[i+1]<168 and oam[i+2] in ball_tiles]
            for sy,sx,tile,attr in balls:
                assert attr&7==6,(label,outcome,frame,'ball inherited species palette',attr)
                raw=p.lib.sb_memory(9)
                cap=raw[52]|raw[53]<<8
                assert cap==(rgb[0]|rgb[1]<<5|rgb[2]<<10),(label,outcome,frame,'wrong cap color',cap)
                assert bytes(raw[50:52])==b'\xff\x7f',(label,'white lower half changed')
                caps.add(cap);positions.add((sx,sy))
            if balls:
                ball_frames+=1
                if best is None and max(s[1] for s in balls)>88:best=image(p)
            if label=='Poke' and outcome=='caught' and frame%2==0:frames.append(image(p).resize((480,432),Image.Resampling.NEAREST))
            if p.call_finished():break
        else:raise AssertionError((label,outcome,'animation hung'))
        assert ball_frames>15 and len(positions)>10,(label,outcome,'no thrown ball',ball_frames,len(positions))
        bad=[p.lib.sb_bad_vram_writes(),p.lib.sb_bad_palette_writes()]
        assert bad==[0,0],(label,outcome,bad)
        report['balls'].append({'ball':label,'outcome_fixture':outcome,'frames':frame+1,'colored_ball_frames':ball_frames,'distinct_positions':len(positions),'blocked_writes':bad})
        if outcome=='caught':
            assert best is not None
            thumbnails.append((label+' Ball',best))
            best.resize((480,432),Image.Resampling.NEAREST).save(OUT/(label.lower()+'-ball.png'))
        if frames:
            times=[round(i*2*70224/4194304*100)*10 for i in range(len(frames)+1)]
            frames[0].save(OUT/'pokeball.gif',save_all=True,append_images=frames[1:],duration=[b-a for a,b in zip(times,times[1:])],loop=0)
        # Later palette commands must be able to reclaim the effect slot.
        run(p,'RunPaletteCommand',{1:0x0100})
        assert p.get('wColorCommand')==1
        ptr=p.addr('wCGBBasePalPointers')+4
        address=p.get(ptr)|(p.get(ptr+1)<<8)
        bank=p.symbols['CGBBasePalettes'][0]
        source=ROM.read_bytes()[bank*0x4000+(address&0x3fff):bank*0x4000+(address&0x3fff)+8]
        shades=[(p.get(0xff49)>>(2*i))&3 for i in range(4)]
        expected=b''.join(source[shade*2:shade*2+2] for shade in shades)
        assert bytes(p.lib.sb_memory(9)[48:56])==expected,(label,outcome,'effect palette not reclaimed')
        report['balls'][-1]['palette_slot_reclaimed']=True
p.close()
sheet=Image.new('RGB',(320*3,312*((len(thumbnails)+2)//3)),'#171717')
draw=ImageDraw.Draw(sheet)
for i,(label,im) in enumerate(thumbnails):
    x,y=i%3*320,i//3*312
    draw.text((x+5,y+4),label,fill='white')
    sheet.paste(im.resize((320,288),Image.Resampling.NEAREST),(x,y+24))
sheet.save(OUT/'battle-colors.png')
report['limitations']=['Encounter and animation RAM fixtures; capture outcomes forced to test each visual path','No physical GBC test']
(OUT.parent/'battle_colors.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
