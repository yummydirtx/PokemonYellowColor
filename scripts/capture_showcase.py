#!/usr/bin/env python3
"""Capture actual original/current ROM footage; no ROM or save is modified.

Run from the repository root. SameBoy's CGB-E model is used for BOTH versions.
Fixtures set map positions, a display name, and the battle encounter/moves.
Walking and the battle turn then run through the game's ordinary input loop.
Intermediate raw footage, audio, states and traces stay in ignored build/.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image
from sameboy import SameBoy

ROOT = Path('build/showcase')
SCENES = {
    'pallet': ((0, 10, 4, 7), [('right', 13), ('down', 5), ('left', 8), ('up', 5)]),
    'route1': ((12, 10, 10, 16), [('left', 6), ('right', 12), ('left', 6)]),
    'lab': ((40, 5, 3, 9), [('right', 4), ('left', 3), ('up', 6),
                           ('down', 6), ('right', 3), ('left', 3), ('up', 3)]),
    'forest': ((51, 17, 16, 18), [('left', 5), ('right', 5)] * 3),
}


def pixels(p):
    return Image.frombytes('RGBA', (160, 144),
        ctypes.string_at(p.lib.sb_pixels(), 160*144*4), 'raw', 'BGRA').convert('RGB')


def rename(p, name, value):
    for i, byte in enumerate([ord(c) - ord('A') + 0x80 for c in value] + [0x50]):
        p.put(p.addr(name) + i, byte)


class Recording:
    def __init__(self, p, directory):
        self.p, self.directory, self.trace = p, directory, []
        directory.mkdir(parents=True, exist_ok=True)
        self.video = (directory / 'frames.rgb').open('wb')
        assert p.lib.sb_audio_start(str(directory / 'audio.s16le').encode()) == 0

    def frame(self, segment, **metadata):
        self.p.tick(1)
        self.video.write(pixels(self.p).tobytes())
        self.trace.append(dict(segment=segment,
            x=self.p.get('wXCoord'), y=self.p.get('wYCoord'),
            walk=self.p.get('wWalkCounter'), scx=self.p.get(0xff43), scy=self.p.get(0xff42),
            pose=self.p.get('wSpritePlayerStateData1ImageIndex'),
            map=self.p.get('wCurMap'), **metadata))

    def idle(self, n, segment):
        for _ in range(n):
            self.frame(segment)

    def close(self, extra=None):
        self.video.close()
        assert self.p.lib.sb_audio_stop() == 0
        (self.directory / 'trace.json').write_text(json.dumps(self.trace))
        report = dict(frames=len(self.trace), seconds=len(self.trace)*70224/4194304,
                      audio_samples=(self.directory/'audio.s16le').stat().st_size//4,
                      **(extra or {}))
        (self.directory / 'capture.json').write_text(json.dumps(report, indent=2)+'\n')
        print(self.directory, report, flush=True)


def walk(p, name, directory):
    start, path = SCENES[name]
    if name == 'forest':
        # Trainer-header data supplies the event byte/bit in either ROM layout.
        rom = p.lib.sb_memory(0)
        for i in range(5):
            bank, addr = p.symbols[f'ViridianForestTrainerHeader{i}']
            offset = bank*0x4000 + (addr & 0x3fff)
            bit = rom[offset]
            event = rom[offset+2] | rom[offset+3] << 8
            assert bit < 8 and p.addr('wEventFlags') <= event < p.addr('wGrassRate')
            p.put(event, p.get(event) | (1 << bit))
    p.warp(*start)
    p.put('wGrassRate', 0)  # Keep the walking take free of random encounters.
    p.put('wWaterRate', 0)
    rec = Recording(p, directory)
    rec.idle(24, -1)
    for segment, (direction, count) in enumerate(path):
        dx, dy = {'right': (1, 0), 'left': (-1, 0), 'up': (0, -1), 'down': (0, 1)}[direction]
        target = (p.get('wXCoord') + dx*count, p.get('wYCoord') + dy*count)
        p.key(direction, True)
        for frame in range(count*30+120):
            rec.frame(segment)
            assert p.get('wCurMap') == start[0] and p.get('wIsInBattle') == 0, name
            if (p.get('wXCoord'), p.get('wYCoord')) == target and p.get('wWalkCounter') == 0:
                break
        else:
            p.capture(directory/'blocked.png')
            raise AssertionError((name, direction, target, p.get('wXCoord'), p.get('wYCoord')))
        p.key(direction, False)
    rec.idle(45, len(path))
    rec.close({'waypoints_reached': len(path)})


def battle(p, directory):
    p.warp(12, 10, 10, 10)
    p.put('wCurOpponent', 84)
    p.put('wCurEnemyLevel', 5)
    p.watch(['DisplayBattleMenu'])
    for frame in range(1500):
        p.tick(1)
        if p.events():
            break
        if frame % 60 == 0:
            p.press('b', 4, 0)
    else:
        raise AssertionError('Encounter did not reach the menu')
    p.tick(8)
    for side in ['Battle', 'Enemy']:
        for i, move in enumerate([84, 0, 0, 0]):
            p.put(p.addr(f'w{side}MonMoves')+i, move)
            p.put(p.addr(f'w{side}MonPP')+i, 30 if i == 0 else 0)
        p.put(f'w{side}MonStatus', 0)
    p.put('wOptions', (p.get('wOptions') & 0x70) | 1)
    p.press('a', 4, 40)
    p.watch(['MoveAnimation', 'PlayApplyingAttackSound.playSound', 'DisplayBattleMenu'])
    rec = Recording(p, directory)
    rec.idle(60, -1)
    p.key('a', True)
    events, seen = [], 0
    for frame in range(1500):
        if frame == 4:
            p.key('a', False)
        if frame >= 45:
            p.key('a', frame % 45 < 4)
        rec.frame(0)
        new = p.events()
        for e in new[seen:]:
            events.append(dict(frame=len(rec.trace)-1, name=e['name'],
                               side=p.get('hWhoseTurn'), animation=p.get('wAnimationID')))
        seen = len(new)
        if any(e['name'] == 'DisplayBattleMenu' for e in new):
            break
    else:
        raise AssertionError('Battle turn did not finish')
    p.key('a', False)
    rec.idle(60, 1)
    rec.close({'events': events, 'returned_to_menu': True,
               'player_pp': p.get('wBattleMonPP')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['original', 'color'], required=True)
    parser.add_argument('--scenes', nargs='+', default=[*SCENES, 'battle'])
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    library = ROOT / 'showcase_bridge.dylib'
    if not library.exists():
        subprocess.run(['cc', '-O2', '-shared', '-fPIC', '-I.cache/sameboy',
                        'scripts/showcase_bridge.c', '.cache/sameboy/build/lib/libsameboy.a',
                        '-o', str(library)], check=True)
    rom = Path('build/baseline.gbc' if args.version == 'original' else 'src/pokeyellow.gbc')
    p = SameBoy(rom, 'build/verification/test.sav', library=library)
    p.lib.sb_audio_start.argtypes = [ctypes.c_char_p]
    p.lib.sb_audio_enable()
    p.continue_game()
    rename(p, 'wPlayerName', 'ASH')
    rename(p, 'wPartyMonOT', 'ASH')  # Preserve the starter/follower ownership check.
    rename(p, 'wPartyMonNicks', 'PIKACHU')
    state = ROOT / f'{args.version}.state'
    assert p.lib.sb_save(str(state).encode()) == 0
    try:
        for scene in args.scenes:
            assert p.lib.sb_load(str(state).encode()) == 0
            p.in_fixture = False
            directory = ROOT / args.version / scene
            if scene == 'battle':
                battle(p, directory)
            else:
                walk(p, scene, directory)
    finally:
        p.close()
    (ROOT / args.version / 'source.json').write_text(json.dumps({
        'rom_sha256': hashlib.sha256(rom.read_bytes()).hexdigest(),
        'model': 'SameBoy CGB-E', 'lcd_fps': 4194304/70224,
        'audio': '48000 Hz signed little-endian 16-bit stereo',
        'fixtures': ['same normal save', 'map positions', 'ASH / PIKACHU names',
                     'no random encounters during walking', 'forest trainers already beaten',
                     'wild Pikachu and ThunderShock moves'],
    }, indent=2)+'\n')


if __name__ == '__main__':
    main()
