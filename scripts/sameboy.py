"""Minimal ctypes interface to the optional SameBoy verification adapter."""
import ctypes as C
from pathlib import Path
import re
from PIL import Image


class Event(C.Structure):
    _fields_ = [('ticks', C.c_uint64), ('id', C.c_uint16), ('ly', C.c_uint8),
               ('mode', C.c_uint8), ('speed', C.c_uint8), ('a', C.c_uint8), ('d', C.c_uint8)]


class SameBoy:
    def __init__(self, rom, save=None, dmg=False):
        self.lib = C.CDLL(str(Path('build/performance/sameboy_bridge.dylib').resolve()))
        self.symbols = {m[3]: (int(m[1], 16), int(m[2], 16)) for m in re.finditer(
            r'^([0-9a-f]+):([0-9a-f]+) (\S+)', Path(rom).with_suffix('.sym').read_text(), re.M)}
        self.lib.sb_open.argtypes = [C.c_char_p, C.c_char_p, C.c_char_p, C.c_int]
        self.lib.sb_read.restype = C.c_uint8
        self.lib.sb_events.restype = C.POINTER(Event)
        self.lib.sb_pixels.restype = C.POINTER(C.c_uint32)
        self.lib.sb_memory.restype = C.POINTER(C.c_uint8)
        boot = Path('.cache/sameboy/build/bin/BootROMs') / ('dmg_boot.bin' if dmg else 'cgb_boot.bin')
        assert self.lib.sb_open(str(rom).encode(), str(boot).encode(),
                                str(save).encode() if save else None, 2 if dmg else 0x205) == 0
        self.in_fixture = False

    def addr(self, name):
        return self.symbols[name][1]

    def get(self, name):
        return self.lib.sb_read(self.addr(name) if isinstance(name, str) else name)

    def put(self, name, value):
        self.lib.sb_write(self.addr(name) if isinstance(name, str) else name, value)

    def tick(self, frames):
        self.lib.sb_tick(frames)

    def key(self, key, held):
        self.lib.sb_key(['right', 'left', 'up', 'down', 'a', 'b', 'select', 'start'].index(key), held)

    def press(self, key, frames=4, settle=60):
        self.key(key, True)
        self.tick(frames)
        self.key(key, False)
        self.tick(settle)

    def watch(self, names):
        self.lib.sb_clear_watches()
        self.names = names
        for i, name in enumerate(names):
            self.lib.sb_watch(i, *self.symbols[name])

    def events(self):
        assert self.lib.sb_event_count() < 1000000, 'Timing trace buffer overflowed'
        ptr = self.lib.sb_events()
        # Copy entries before another emulator call mutates the C array.
        return [dict(name=self.names[e.id], ticks=e.ticks, ly=e.ly, mode=e.mode,
                     speed=e.speed, a=e.a, d=e.d) for e in ptr[:self.lib.sb_event_count()]]

    def capture(self, path):
        raw = C.string_at(self.lib.sb_pixels(), 160 * 144 * 4)
        Image.frombytes('RGBA', (160, 144), raw, 'raw', 'BGRA').convert('RGB').save(path)

    def warp(self, mid, width, x, y):
        self.sync()
        ptr = self.addr('wOverworldMap') + 7 + width + (width + 6) * (y // 2) + x // 2
        for i, v in enumerate([mid, ptr & 255, ptr >> 8, y, x, y & 1, x & 1]):
            self.put(self.addr('wCurMap') + i, v)
        self.lib.sb_register(4, self.addr('wStack'))
        self.lib.sb_register(5, self.addr('EnterMap'))
        self.in_fixture = False
        self.tick(300)

    def close(self):
        self.lib.sb_close()

    def continue_game(self):
        self.tick(1000)
        self.press('start', 10, 240)
        for _ in range(12):
            self.press('a', 10, 120)
            if self.get('wUpdateSpritesEnabled') == 1 and self.get('hWY') == 144:
                break
        assert self.get('wUpdateSpritesEnabled') == 1, 'Continue did not enter the map'
        for _ in range(4):
            self.press('b', 4, 45)

    def call(self, name, registers=None, timeout=600):
        """RAM trampoline for testing an actual ROM routine; caller saves fixtures."""
        self.sync()
        bank, pc = self.symbols[name]
        if bank:
            self.put(0x2000, bank)
            self.put('hLoadedROMBank', bank)
        trap = self.addr('wTileMap')
        ack = trap + 16
        code = [0x3e, 1, 0xea, ack & 255, ack >> 8, 0xc3, (trap+5) & 255, (trap+5) >> 8]
        for i, b in enumerate(code):
            self.put(trap + i, b)
        self.put(ack, 0)
        sp = self.addr('wStack') - 2
        self.put(sp, trap & 255)
        self.put(sp + 1, trap >> 8)
        self.lib.sb_register(4, sp)
        self.lib.sb_register(5, pc)
        for index, value in (registers or {}).items():
            self.lib.sb_register(index, value)
        for frame in range(timeout):
            self.tick(1)
            if self.get(ack):
                self.in_fixture = True
                return frame + 1
        raise AssertionError(f'{name} did not return')

    def sync(self):
        # Frame callbacks can stop at the interrupt vector with IME cleared.
        # Finish that ISR before replacing PC; otherwise a fixture skips RETI
        # and falsely deadlocks the next DelayFrame, especially on DMG.
        pc = self.addr('wTileMap') + 5 if self.in_fixture else self.addr('DelayFrame.halt')
        assert self.lib.sb_sync(pc), 'Could not reach an interrupt-safe fixture point'
