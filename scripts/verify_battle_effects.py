#!/usr/bin/env python3
"""Exercise both directions of the Gen 2 effects in SameBoy's CGB model.

A RAM encounter fixture enters a real wild battle. Routine fixtures then run
MoveAnimation with three front/back sprite pairs; they do not simulate damage.
Artwork, background tiles, palette restoration, OAM bounds and LCD writes are
checked independently of the timeline compiler.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from sameboy import SameBoy

OUT = Path('build/verification')
MOVES = {'THUNDERSHOCK': 84, 'THUNDERBOLT': 85, 'THUNDER_WAVE': 86, 'THUNDER': 87,
         'SCRATCH': 10, 'CUT': 15, 'TACKLE': 33, 'QUICK_ATTACK': 98}
p = SameBoy('src/pokeyellow.gbc', OUT / 'test.sav')
p.continue_game()
p.warp(12, 10, 10, 10)
p.put('wCurOpponent', 165)  # Rattata encounter
p.put('wCurEnemyLevel', 5)
p.watch(['DisplayBattleMenu'])
for frame in range(1500):
    p.tick(1)
    if p.events():
        break
    if frame % 60 == 0:
        p.press('b', 4, 0)
else:
    raise AssertionError('Wild battle did not reach the battle menu')
p.tick(8)
assert p.get('wIsInBattle') == 1
state = b'build/animation-fixes/battle-effects.state'
assert p.lib.sb_save(state) == 0


def run(name, registers=None, timeout=600):
    # Battle code does not use the overworld sprite-state array. Keeping this
    # test trampoline here preserves the visible HUD and animation tile buffers.
    p.begin_call(name, registers, scratch='wSpriteStateData1')
    for frame in range(timeout):
        p.tick(1)
        if p.call_finished():
            return frame+1
    raise AssertionError(f'{name} did not return')


def load_pair(back, front):
    for symbol in ['wBattleMonSpecies', 'wBattleMonSpecies2', 'wPartyMon1Species',
                   'wCurSpecies', 'wCurPartySpecies']:
        p.put(symbol, back)
    run('GetMonHeader')
    run('LoadMonBackPic')
    p.put('hWhoseTurn', 0)
    run('AnimationShowMonPic')
    for symbol in ['wEnemyMonSpecies', 'wEnemyMonSpecies2', 'wCurSpecies', 'wCurPartySpecies']:
        p.put(symbol, front)
    run('GetMonHeader')
    run('LoadMonFrontSprite', {2: p.addr('vFrontPic')})
    run('RunPaletteCommand', {1: 0x0100})
    run('SetAnimationPalette')


def background():
    return bytes(p.get(p.addr('wTileMap')+i) for i in range(360))


def image():
    import ctypes
    raw = ctypes.string_at(p.lib.sb_pixels(), 160*144*4)
    return Image.frombytes('RGBA', (160, 144), raw, 'raw', 'BGRA').convert('RGB')


results, thumbnails = [], []
for back, front in [(84, 165), (180, 14), (132, 21)]:
    assert p.lib.sb_load(state) == 0
    p.in_fixture = False
    load_pair(back, front)
    pair_state = b'build/animation-fixes/battle-pair.state'
    assert p.lib.sb_save(pair_state) == 0
    for move, number in MOVES.items():
        for side in [0, 1]:
            assert p.lib.sb_load(pair_state) == 0
            p.in_fixture = True
            p.put('wAnimationID', number)
            p.put('wAnimationType', 0)
            p.put('hWhoseTurn', side)
            p.put('wOptions', p.get('wOptions') & 0x7f)
            pics = bytes(p.lib.sb_memory(3)[0x1000:0x1620])
            bg = background()
            palettes = bytes(p.lib.sb_memory(9)[:64])
            bg_palettes = bytes(p.lib.sb_memory(8)[:64])
            attributes = bytes(p.lib.sb_memory(3)[0x3800:0x4000])
            p.lib.sb_clear_write_counts()
            p.watch(['Gen2TryAnimation.found', 'Gen2PlayMoveSound'])
            p.begin_call('MoveAnimation', scratch='wSpriteStateData1')
            maximum, scanline_max, best, frames = 0, 0, None, []
            effect_palettes = set()
            for frame in range(500):
                p.tick(1)
                oam = list(p.lib.sb_memory(7)[:160])
                sprites = [oam[i:i+4] for i in range(0, 160, 4)
                           if 0 < oam[i] < 160 and 0 < oam[i+1] < 168]
                if sprites and len(sprites) >= maximum:
                    maximum = len(sprites)
                    best = image()
                for y in range(144):
                    scanline_max = max(scanline_max, sum(sy-16 <= y < sy-8 for sy, _, _, _ in sprites))
                for sy, sx, tile, attr in sprites:
                    assert sy <= 104, (move, side, 'effect overlaps the text box', sy)
                    assert 0x31 <= tile <= 0x7f, (move, side, 'effect overwrote battler tile range', tile)
                    assert attr & 7 in [6, 7], (move, side, 'effect uses a battler palette', attr)
                    effect_palettes.add(attr & 7)
                assert bytes(p.lib.sb_memory(3)[0x1000:0x1620]) == pics, (move, side, 'battler art overwritten')
                assert bytes(p.lib.sb_memory(8)[:64]) == bg_palettes, (move, side, 'battler colors changed')
                if back == 84 and frame % 2 == 0:
                    frames.append(image().resize((480, 432), Image.Resampling.NEAREST))
                if p.call_finished():
                    break
            else:
                raise AssertionError((move, side, 'did not return'))
            assert len([e for e in p.events() if e['name'] == 'Gen2TryAnimation.found']) == 1
            assert any(e['name'] == 'Gen2PlayMoveSound' for e in p.events())
            assert maximum > 0 and scanline_max <= 10, (move, side, 'OAM limit', maximum, scanline_max)
            assert background() == bg, (move, side, 'battler tilemap not restored')
            assert bytes(p.lib.sb_memory(9)[:64]) == palettes, (move, side, 'OBJ palette not restored')
            assert bytes(p.lib.sb_memory(3)[0x3800:0x4000]) == attributes, (move, side, 'BG attributes changed')
            bad = [p.lib.sb_bad_vram_writes(), p.lib.sb_bad_palette_writes()]
            assert bad == [0, 0], (move, side, 'writes during mode 3', bad)
            assert not any(p.lib.sb_memory(7)[i] for i in range(0, 160, 4)), 'Stale OAM after animation'
            results.append({'move': move, 'side': side, 'back_species': back, 'front_species': front,
                            'frames': frame+1, 'max_sprites': maximum, 'max_per_scanline': scanline_max,
                            'effect_palettes': sorted(effect_palettes), 'blocked_writes': bad,
                            'picture_bytes_preserved': True, 'tilemap_and_palettes_restored': True})
            if back == 84:
                thumbnails.append((f'{move} / {"enemy" if side else "player"}', best))
                if move in ['THUNDERSHOCK', 'THUNDER', 'SCRATCH', 'QUICK_ATTACK']:
                    frames[0].save(OUT / f'{move.lower()}_{side}.gif', save_all=True,
                                   append_images=frames[1:], duration=34, loop=0)

# Verify the Options switch bypasses all new effects, and an unported move
# still uses the original engine. hOnCGB=0 checks the dispatch fallback; actual
# DMG boot coverage belongs to verify_special_scenes.py.
fallbacks = []
for case in ['disabled', 'legacy_move', 'dmg_dispatch']:
    assert p.lib.sb_load(state) == 0
    p.in_fixture = False
    p.put('wAnimationID', 52 if case == 'legacy_move' else 84)
    p.put('wAnimationType', 0)
    p.put('hWhoseTurn', 0)
    if case == 'disabled':
        p.put('wOptions', p.get('wOptions') | 0x80)
    if case == 'dmg_dispatch':
        p.put('hOnCGB', 0)
    p.watch(['Gen2TryAnimation.found', 'PlaySubanimation'])
    run('MoveAnimation')
    names = [e['name'] for e in p.events()]
    assert 'Gen2TryAnimation.found' not in names, (case, names)
    assert ('PlaySubanimation' in names) == (case != 'disabled')
    fallbacks.append(case)
p.close()
sheet = Image.new('RGB', (4*320, 4*314), '#222222')
draw = ImageDraw.Draw(sheet)
for i, (label, im) in enumerate(thumbnails):
    x, y = i%4*320, i//4*314
    draw.text((x+4, y+3), label, fill='white')
    sheet.paste(im.resize((320, 288), Image.Resampling.NEAREST), (x, y+22))
sheet.save(OUT / 'battle_effects.png')
report = {'rom_sha256': hashlib.sha256(Path('src/pokeyellow.gbc').read_bytes()).hexdigest(),
          'model': 'SameBoy CGB-E', 'cases': results, 'fallbacks': fallbacks,
          'limitations': ['Routine fixtures test visuals, not a full battle playthrough',
                          'No physical GBC test']}
(OUT / 'battle_effects.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
