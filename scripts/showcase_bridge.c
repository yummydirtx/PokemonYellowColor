/* Optional audiovisual capture extension. The verification adapter stays silent. */
#include "sameboy_bridge.c"
#include <stdio.h>

static FILE *audio_output;
static void audio_sample(GB_gameboy_t *g, GB_sample_t *sample) {
    if (audio_output) {
        /* Explicit little endian signed stereo PCM, independent of host byte order. */
        uint8_t bytes[] = {sample->left & 255, (sample->left >> 8) & 255,
                           sample->right & 255, (sample->right >> 8) & 255};
        fwrite(bytes, 1, sizeof(bytes), audio_output);
    }
}
void sb_audio_enable(void) {
    GB_set_sample_rate(gb, 48000);
    GB_apu_set_sample_callback(gb, audio_sample);
}
int sb_audio_start(const char *path) {
    if (audio_output) return -1;
    audio_output = fopen(path, "wb");
    return audio_output ? 0 : -1;
}
int sb_audio_stop(void) {
    if (!audio_output) return -1;
    int result = fclose(audio_output);
    audio_output = NULL;
    return result;
}
