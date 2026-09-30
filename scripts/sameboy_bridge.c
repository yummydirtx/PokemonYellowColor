/* Small headless adapter for hardware timing checks. Build against SameBoy's
 * public C API; no changes to the emulator or the tested ROM are required. */
#include "Core/gb.h"
#include <stdlib.h>
#include <string.h>

static GB_gameboy_t *gb;
static uint32_t pixels[160 * 144];
static uint64_t ticks, frames;
static int16_t watches[65536], banks[64];
typedef struct {
    uint64_t ticks;
    uint16_t id;
    uint8_t ly, mode, speed, a, d;
} Event;
static Event events[1000000];
static unsigned event_count;
static unsigned blocked_vram_writes, blocked_palette_writes;

static uint32_t rgb(GB_gameboy_t *g, uint8_t r, uint8_t g2, uint8_t b) {
    return 0xff000000u | ((uint32_t)r << 16) | ((uint32_t)g2 << 8) | b;
}
static void vblank(GB_gameboy_t *g, GB_vblank_type_t type) { frames++; }
static bool write_memory(GB_gameboy_t *g, uint16_t addr, uint8_t value) {
    if (((addr >= 0x8000 && addr < 0xa000) || addr == 0xff69 || addr == 0xff6b)
        && (GB_read_memory(g, 0xff40) & 0x80) && (GB_read_memory(g, 0xff41) & 3) == 3) {
        if (addr < 0xa000) blocked_vram_writes++;
        else blocked_palette_writes++;
    }
    return true;
}
static void execute(GB_gameboy_t *g, uint16_t pc, uint8_t opcode) {
    int id = watches[pc];
    if (id < 0 || event_count == 1000000) return;
    if (pc >= 0x4000 && pc < 0x8000) {
        uint16_t bank;
        GB_get_direct_access(g, GB_DIRECT_ACCESS_ROM, NULL, &bank);
        if (bank != banks[id]) return;
    }
    events[event_count++] = (Event){ticks, id, GB_read_memory(g, 0xff44),
        GB_read_memory(g, 0xff41) & 3, GB_read_memory(g, 0xff4d) & 0x80,
        GB_get_registers(g)->af >> 8, GB_get_registers(g)->de >> 8};
}

int sb_open(const char *rom, const char *boot, const char *save, int model) {
    gb = GB_init(GB_alloc(), model);
    ticks = frames = event_count = 0;
    blocked_vram_writes = blocked_palette_writes = 0;
    memset(watches, -1, sizeof(watches));
    GB_set_turbo_mode(gb, true, true);
    GB_set_emulate_joypad_bouncing(gb, false);
    GB_set_pixels_output(gb, pixels);
    GB_set_rgb_encode_callback(gb, rgb);
    GB_set_vblank_callback(gb, vblank);
    GB_set_execution_callback(gb, execute);
    GB_set_write_memory_callback(gb, write_memory);
    if (GB_load_rom(gb, rom) || GB_load_boot_rom(gb, boot)) return -1;
    if (save && GB_load_battery(gb, save)) return -2;
    return 0;
}
void sb_close(void) { GB_free(gb); GB_dealloc(gb); gb = NULL; }
void sb_tick(unsigned n) {
    uint64_t end = frames + n;
    while (frames < end) ticks += GB_run(gb);
}
int sb_sync(unsigned addr) {
    uint64_t end = ticks + 140448 * 300;
    while (GB_get_registers(gb)->pc != addr && ticks < end) ticks += GB_run(gb);
    return GB_get_registers(gb)->pc == addr;
}
void sb_key(unsigned key, int held) { GB_set_key_state(gb, key, held); }
uint8_t sb_read(unsigned addr) { return GB_read_memory(gb, addr); }
void sb_write(unsigned addr, uint8_t value) { GB_write_memory(gb, addr, value); }
void sb_register(unsigned index, uint16_t value) {
    GB_get_registers(gb)->registers[index] = value;
}
uint16_t sb_get_register(unsigned index) { return GB_get_registers(gb)->registers[index]; }
void sb_watch(unsigned id, unsigned bank, unsigned addr) {
    watches[addr] = id; banks[id] = bank;
}
void sb_clear_watches(void) { memset(watches, -1, sizeof(watches)); event_count = 0; }
void sb_clear_events(void) { event_count = 0; }
unsigned sb_event_count(void) { return event_count; }
void sb_clear_write_counts(void) { blocked_vram_writes = blocked_palette_writes = 0; }
unsigned sb_bad_vram_writes(void) { return blocked_vram_writes; }
unsigned sb_bad_palette_writes(void) { return blocked_palette_writes; }
Event *sb_events(void) { return events; }
uint32_t *sb_pixels(void) { return pixels; }
uint8_t *sb_memory(unsigned kind) { return GB_get_direct_access(gb, kind, NULL, NULL); }
int sb_save(const char *path) { return GB_save_state(gb, path); }
int sb_load(const char *path) { return GB_load_state(gb, path); }
