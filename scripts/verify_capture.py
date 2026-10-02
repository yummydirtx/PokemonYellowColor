#!/usr/bin/env python3
"""Select a Poké Ball through the battle menus and finish a real capture.

The encounter, inventory, nickname, low HP and sleeping status are RAM fixtures; the
engine calculates the catch, consumes the ball, adds the Pokémon and exits.
Both CGB and DMG execute the complete item-use path with ordinary button input.
"""
import ctypes
import hashlib
import json
from pathlib import Path
from PIL import Image
from sameboy import SameBoy

OUT=Path('build/verification')
results=[]
for dmg in [False,True]:
    p=SameBoy('src/pokeyellow.gbc',OUT/'test.sav',dmg=dmg)
    p.continue_game()
    p.sync()
    for name,text in [('wPlayerName','ASH'),('wPartyMonOT','ASH'),('wPartyMonNicks','PIKACHU')]:
        for i,c in enumerate(text):p.put(p.addr(name)+i,ord(c)-ord('A')+0x80)
        p.put(p.addr(name)+len(text),0x50)
    p.warp(12,10,10,10)
    p.sync()
    for i,value in enumerate([1,4,10,255]):p.put(p.addr('wNumBagItems')+i,value)
    p.put('wCurOpponent',165)
    p.put('wCurEnemyLevel',5)
    p.watch(['PrintBeginningBattleText','DisplayBattleMenu'])
    weakened=False
    for frame in range(1500):
        p.tick(1)
        if not weakened and any(e['name']=='PrintBeginningBattleText' for e in p.events()):
            # Set HP before the native HUD is drawn, so the screen stays truthful.
            p.put('wEnemyMonHP',0)
            p.put(p.addr('wEnemyMonHP')+1,1)
            weakened=True
        if any(e['name']=='DisplayBattleMenu' for e in p.events()):break
        if frame%60==0:p.press('b',4,0)
    else:raise AssertionError('No wild battle menu')
    assert weakened
    p.tick(8)
    p.sync()
    p.put('wEnemyMonStatus',7) # Sleeping Rattata; catch calculation stays native.
    before=p.get('wPartyCount')
    p.press('down',4,15) # ITEM
    p.press('a',4,100) # Bag
    p.watch(['ItemUseBall','TossBallAnimation','DisplayBattleMenu'])
    p.lib.sb_clear_write_counts()
    p.key('a',True) # POKE BALL
    frames=[];ball_frames=0;best=None
    for frame in range(1800):
        if frame==4:p.key('a',False)
        if frame>40:p.key('b',frame%60<4) # Text, then decline a nickname.
        p.tick(1)
        tossing=any(e['name']=='TossBallAnimation' for e in p.events())
        raw=ctypes.string_at(p.lib.sb_pixels(),160*144*4)
        im=Image.frombytes('RGBA',(160,144),raw,'raw','BGRA').convert('RGB')
        if tossing and not dmg:frames.append(im)
        if tossing:
            oam=list(p.lib.sb_memory(7)[:160])
            balls=[oam[i:i+4] for i in range(0,160,4) if 0<oam[i]<160 and 0<oam[i+1]<168 and oam[i+2] in [0x33,0x43,0x37,0x38,0x47,0x48]]
            if balls:
                ball_frames+=1
                assert all((s[3]&7 in [2,3]) if dmg else (s[3]&7==6) for s in balls),(dmg,frame,'wrong ball palette')
                if not dmg:
                    palettes=p.lib.sb_memory(9)
                    assert bytes(palettes[50:54])==bytes([255,127,191,20]),(frame,'wrong red/white colors')
                    if best is None and any(s[1]>88 for s in balls):best=im
        if tossing and p.get('wIsInBattle')==0:break
    else:
        p.capture(OUT/'capture_failure.png')
        raise AssertionError(('Capture did not return to the map',dmg,p.get('wPartyCount')))
    p.key('b',False)
    p.tick(120)
    assert p.get('wPartyCount')==before+1,(dmg,'Rattata not caught')
    assert p.get(p.addr('wPartySpecies')+before)==165
    assert p.get(p.addr('wBagItems')+1)==9,(dmg,'wrong item consumption')
    assert ball_frames>30
    bad=[p.lib.sb_bad_vram_writes(),p.lib.sb_bad_palette_writes()]
    assert bad==[0,0],(dmg,bad)
    if not dmg:
        assert p.get('wColorActive')==1 and p.get('wColorCommand')==9
        best.resize((480,432),Image.Resampling.NEAREST).save(OUT/'pokeball.png')
        clip=[im.resize((480,432),Image.Resampling.NEAREST) for im in frames[:330:2]]
        times=[round(i*2*70224/4194304*100)*10 for i in range(len(clip)+1)]
        clip[0].save(OUT/'pokeball.gif',save_all=True,append_images=clip[1:],duration=[b-a for a,b in zip(times,times[1:])],loop=0)
    results.append({'model':'DMG' if dmg else 'CGB-E','frames':frame+1,'ball_frames':ball_frames,'party_added':165,'balls_consumed':1,'returned_to_overworld':True,'blocked_writes':bad})
    p.close()
report={'rom_sha256':hashlib.sha256(Path('src/pokeyellow.gbc').read_bytes()).hexdigest(),'captures':results,'limitations':['Encounter, inventory, names, low HP and sleep set in RAM; no physical hardware test']}
(OUT/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
