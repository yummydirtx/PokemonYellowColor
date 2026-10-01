#!/usr/bin/env python3
"""Edit the captured original/Color footage into pixel-crisp comparison videos.

Walking takes are matched by exact player pose, scroll and map coordinates;
original frames are retimed to the Color take, so these are not speed benchmarks.
The battle is two replays joined by a wipe between stationary attack poses.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('build/showcase')
OUT = Path('docs/showcase')
FPS = 4194304 / 70224
OUTPUT_FPS = FPS / 2
SAMPLE_RATE = 48000
TITLES = {
    'pallet': ('Pallet Town', 'Terracotta roofs, blue water, and Pikachu in yellow'),
    'route1': ('Route 1', 'Pink flowers, green leaves, and wooden path borders'),
    'lab': ("Oak’s lab", 'Warm wood, colorful books, and properly shaded scientists'),
    'forest': ('Viridian Forest', 'Fresh greens, tree bark, and colored cut stumps'),
    'battle': ('ThunderShock', 'Gen 2 sprites and three moving bursts of sparks'),
}
FIELDS = ['segment', 'x', 'y', 'walk', 'scx', 'scy', 'pose']
FFMPEG = shutil.which('ffmpeg')


def font(size, bold=False):
    # macOS capture workstation; command-line overrides make rendering portable.
    return ImageFont.truetype(ARGS.bold_font if bold else ARGS.font, size)


def load(version, name):
    directory = ROOT / version / name
    trace = json.loads((directory/'trace.json').read_text())
    video = np.memmap(directory/'frames.rgb', dtype=np.uint8, mode='r').reshape((-1,144,160,3))
    assert len(video) == len(trace)
    audio = np.fromfile(directory/'audio.s16le', dtype='<i2').reshape((-1,2))
    assert abs(len(audio) - len(video)*SAMPLE_RATE/FPS) < 10
    return dict(video=video, audio=audio, trace=trace,
                info=json.loads((directory/'capture.json').read_text()))


def match_frames(original, color):
    groups, used, counts = defaultdict(list), defaultdict(int), defaultdict(int)
    for i, row in enumerate(original):
        groups[tuple(row[k] for k in FIELDS)].append(i)
    for row in color:
        counts[tuple(row[k] for k in FIELDS)] += 1
    matched = []
    for row in color:
        key = tuple(row[k] for k in FIELDS)
        assert key in groups, ('No identical walking pose', row)
        candidates = groups[key]
        fraction = used[key] / max(1, counts[key]-1)
        matched.append(candidates[round(fraction*(len(candidates)-1))])
        used[key] += 1
    assert all(b >= a for a, b in zip(matched, matched[1:])), 'Footage would run backwards'
    return matched


def audio_slice(take, first, last):
    return take['audio'][round(first*SAMPLE_RATE/FPS):round(last*SAMPLE_RATE/FPS)]


def timeline(name, original, color):
    if name != 'battle':
        match = match_frames(original['trace'], color['trace'])
        # Reveal begins with both versions walking and continues through a turn.
        start, end = round(2.15*FPS), round(3.85*FPS)
        entries = [(i, j) for i, j in zip(match, range(len(match)))]
        audio = color['audio'].copy()  # Continuous original game music from this take.
        report = {'walking_poses_matched': len(match), 'exact_pose_matches': len(match),
                  'original_frames': len(original['video']), 'color_frames': len(color['video']),
                  'audio': 'Continuous Color take; original walking frames aligned to its footsteps'}
    else:
        old_attack = next(e['frame'] for e in original['info']['events'] if e['name']=='MoveAnimation')
        old_hit = next(e['frame'] for e in original['info']['events'] if e['name']=='PlayApplyingAttackSound.playSound')
        new_attack = next(e['frame'] for e in color['info']['events'] if e['name']=='MoveAnimation')
        new_hit = next(e['frame'] for e in color['info']['events'] if e['name']=='PlayApplyingAttackSound.playSound')
        old_first, old_last = old_attack-31, old_hit+21
        new_first, new_last = new_attack, new_hit+75
        hold, tail = 96, 30
        entries = [(i, new_attack-1) for i in range(old_first, old_last)]
        start, end = len(entries), len(entries)+hold
        entries += [(old_last-1, new_attack-1)]*hold
        entries += [(old_last-1, i) for i in range(new_first, new_last)]
        entries += [(old_last-1, new_last-1)]*tail
        parts = [audio_slice(original, old_first, old_last),
                 audio_slice(original, old_last, old_last+hold),
                 audio_slice(color, new_first, new_last+tail)]
        # Short ramps prevent clicks at an editorial cut while preserving effect timing.
        n = round(SAMPLE_RATE*.012)
        for i, part in enumerate(parts):
            part = part.astype(np.float64)
            if i: part[:n] *= np.linspace(0,1,n)[:,None]
            if i < len(parts)-1: part[-n:] *= np.linspace(1,0,n)[:,None]
            parts[i] = part.astype('<i2')
        audio = np.concatenate(parts)
        report = {'original_attack': [old_attack, old_hit], 'color_attack': [new_attack, new_hit],
                  'edit': 'First player attack replayed in each version; stationary wipe between replays',
                  'audio': 'Each replay uses its own captured game audio; 12 ms edit ramps'}
    report['wipe_lcd_frames'] = [start, end]
    return entries, audio, start, end, report


def composite(old, new, progress):
    width = round(progress*160)
    game = Image.fromarray(old).copy()
    if width:
        game.paste(Image.fromarray(new).crop((0,0,width,144)),(0,0))
    return game, width


def presentation(game, title, subtitle, number, progress, width):
    frame = Image.new('RGB',(1080,1080),'#101922')
    draw = ImageDraw.Draw(frame)
    draw.text((60,23), title, font=font(42, True), fill='#f4f1dd')
    draw.text((60,77), subtitle, font=font(22), fill='#acbac4')
    draw.text((920,39), f'{number:02d} / 05', font=font(22), fill='#8296a5')
    frame.paste(game.resize((960,864),Image.Resampling.NEAREST),(60,114))
    if 0 < progress < 1:
        x=60+width*6
        draw.rectangle((x-2,114,x+2,977),fill='#fff2a8')
    if progress == 0:
        label, accent = 'ORIGINAL YELLOW', '#c0c9d1'
    elif progress == 1:
        label, accent = 'FULL COLOR', '#f4cd58'
    else:
        label, accent = 'ORIGINAL  →  FULL COLOR', '#f4cd58'
    draw.rounded_rectangle((60,1000,480,1046),radius=10,fill='#23333e')
    draw.ellipse((78,1017,90,1029),fill=accent)
    draw.text((106,1009),label,font=font(23,True),fill=accent)
    draw.text((658,1006),'POKÉMON YELLOW COLOR',font=font(23,True),fill='#f4f1dd')
    draw.text((810,1038),'GBC  ·  v0.1.6',font=font(18),fill='#8296a5')
    return frame


def render(name, number):
    original, color = load('original',name), load('color',name)
    entries, audio, start, end, report = timeline(name,original,color)
    # Sample exactly every second LCD frame; the true GB clock rate is retained.
    indices = list(range(0,len(entries),2))
    seconds = len(indices)/OUTPUT_FPS
    wanted = round(seconds*SAMPLE_RATE)
    audio = np.pad(audio,((0,max(0,wanted-len(audio))),(0,0)))[:wanted].astype(np.float64)
    ramp = round(SAMPLE_RATE*.08)
    audio[:ramp] *= np.linspace(0,1,ramp)[:,None]
    audio[-ramp:] *= np.linspace(1,0,ramp)[:,None]
    wav = ROOT/f'{name}.wav'
    with wave.open(str(wav),'wb') as output:
        output.setnchannels(2); output.setsampwidth(2); output.setframerate(SAMPLE_RATE)
        output.writeframes(audio.astype('<i2').tobytes())
    mp4 = OUT/f'{name}.mp4'
    cmd=[FFMPEG,'-y','-hide_banner','-loglevel','error',
         '-f','rawvideo','-pix_fmt','rgb24','-s','1080x1080','-r','2097152/70224',
         '-i','pipe:0','-i',str(wav),'-c:v','libx264','-preset','medium','-crf','18',
         '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',
         '-shortest',str(mp4)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    gif_frames, checks = [], []
    title, subtitle = TITLES[name]
    if name == 'battle':
        moments = [round(FPS*t) for t in [.9,1.6,2.5,3.3,4.6,5.0,5.5,7.0]]
    else:
        moments = [round(FPS*.9),start+(end-start)//4,start+(end-start)//2,end+20,len(entries)-35]
    moments = {min(indices, key=lambda i: abs(i-t)) for t in moments}
    try:
        for t in indices:
            old_i,new_i=entries[t]
            q = min(1,max(0,(t-start)/(end-start)))
            progress = q*q*(3-2*q)
            game,width = composite(original['video'][old_i],color['video'][new_i],progress)
            frame=presentation(game,title,subtitle,number,progress,width)
            proc.stdin.write(frame.tobytes())
            # Half-size shareable GIF: 3x game pixels, full presentation, 29.86 fps.
            gif_frames.append(frame.resize((540,540),Image.Resampling.NEAREST))
            if t in moments: checks.append((t,frame.copy()))
        proc.stdin.close()
        assert proc.wait()==0, name
    finally:
        if proc.poll() is None: proc.kill()
    # Global palette avoids frame-to-frame palette shimmer. Source colors stay exact
    # where practical; GIF is a preview, MP4 is the full-resolution deliverable.
    palette_sheet=Image.new('RGB',(540,540*12))
    for i in range(12):
        palette_sheet.paste(gif_frames[round(i*(len(gif_frames)-1)/11)],(0,i*540))
    palette=palette_sheet.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in gif_frames]
    times=[round(i/OUTPUT_FPS*100)*10 for i in range(len(indexed)+1)]
    indexed[0].save(OUT/f'{name}.gif',save_all=True,append_images=indexed[1:],
                    duration=[b-a for a,b in zip(times,times[1:])],loop=0,optimize=False,
                    disposal=1)
    # Compact chronological contact sheets support review without opening a player.
    sheet=Image.new('RGB',(540*len(checks),564),'#101922')
    draw=ImageDraw.Draw(sheet)
    for i,(t,im) in enumerate(checks):
        sheet.paste(im.resize((540,540),Image.Resampling.NEAREST),(i*540,24))
        draw.text((i*540+8,4),f'{t/FPS:.2f}s',fill='white')
    sheet.save(ROOT/f'{name}-review.png')
    gif_frames[min(len(gif_frames)-1,(start+end)//4)].save(OUT/f'{name}-poster.png')
    report.update(seconds=seconds,frames=len(indices),size=[1080,1080],fps=OUTPUT_FPS,
                  audio_peak=int(abs(audio).max()),sha256=hashlib.sha256(mp4.read_bytes()).hexdigest())
    print(name, report, flush=True)
    return report


def montage(names):
    # Scene cuts include matching short video/audio fades. Re-encode only once.
    inputs=[]
    filters=[]
    pads=[]
    for i,name in enumerate(names):
        inputs += ['-i',str(OUT/f'{name}.mp4')]
        duration=REPORT['clips'][name]['seconds']
        filters += [f'[{i}:v]fade=t=in:st=0:d=0.12,fade=t=out:st={duration-.12}:d=0.12[v{i}]',
                    f'[{i}:a]afade=t=in:st=0:d=0.12,afade=t=out:st={duration-.12}:d=0.12[a{i}]']
        pads.append(f'[v{i}][a{i}]')
    filters.append(''.join(pads)+f'concat=n={len(names)}:v=1:a=1[v][a]')
    subprocess.run([FFMPEG,'-y','-hide_banner','-loglevel','error',*inputs,
                    '-filter_complex',';'.join(filters),'-map','[v]','-map','[a]',
                    '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p',
                    '-r','2097152/70224','-c:a','aac','-b:a','192k','-movflags','+faststart',
                    str(OUT/'showcase.mp4')],check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenes',nargs='+',default=list(TITLES))
    parser.add_argument('--font',default='/System/Library/Fonts/Supplemental/Arial.ttf')
    parser.add_argument('--bold-font',default='/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    ARGS=parser.parse_args()
    assert FFMPEG, 'ffmpeg is required'
    OUT.mkdir(parents=True,exist_ok=True)
    report_path=OUT/'capture-report.json'
    REPORT=json.loads(report_path.read_text()) if report_path.exists() else {'clips':{}}
    REPORT.update(sources={v:json.loads((ROOT/v/'source.json').read_text()) for v in ['original','color']})
    for name in ARGS.scenes:
        REPORT['clips'][name]=render(name,list(TITLES).index(name)+1)
        report_path.write_text(json.dumps(REPORT,indent=2)+'\n')
    if set(TITLES)<=set(REPORT['clips']):
        montage(list(TITLES))
