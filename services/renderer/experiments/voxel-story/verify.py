"""Check the encoded artifact, not just a successful rendering process."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[4]
LOCAL=ROOT/'.local/voxel-story'

def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=180)

if __name__=='__main__':
    lesson=json.loads((LOCAL/'pack/commons-lake/lesson.json').read_text())
    folder=LOCAL/'output/commons-lake';video=folder/'lesson.mp4'
    probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout)
    vs=next(s for s in probe['streams'] if s['codec_type']=='video')
    au=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (vs['width'],vs['height'],vs['codec_name'],vs['pix_fmt'])==(720,1280,'h264','yuv420p')
    assert vs['r_frame_rate']=='30/1' and au['codec_name']=='aac'
    duration=float(probe['format']['duration'])
    assert 30<=duration<=60 and abs(duration-lesson['duration'])<.15
    assert all(0<=w['start']<=w['end']<=duration for w in lesson['words'])
    assert all(a['end']<=b['start']+.001 for a,b in zip(lesson['words'],lesson['words'][1:]))
    audio=run(['ffmpeg','-hide_banner','-nostats','-i',str(video),'-af','volumedetect','-vn','-f','null','-']).stderr
    peak=float(re.search(r'max_volume: ([-\d.]+) dB',audio).group(1))
    mean=float(re.search(r'mean_volume: ([-\d.]+) dB',audio).group(1))
    assert -40<mean<-3 and peak<0
    run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'])
    # Re-extract inspection frames from the encoded MP4, replacing preliminary stills.
    indices=json.loads((folder/'frame-index.json').read_text())
    for i,f in enumerate(indices):
        run(['ffmpeg','-v','error','-y','-ss',str(f/30),'-i',str(video),'-frames:v','1',str(folder/f'frame-{i}.png')])
    sheet=Image.new('RGB',(1296,1632),'#172933');draw=ImageDraw.Draw(sheet)
    for i,f in enumerate(indices):
        with Image.open(folder/f'frame-{i}.png') as im:
            im.thumbnail((216,384));x=i%6*216;y=i//6*408;sheet.paste(im,(x,y));draw.text((x+6,y+388),f'{f/30:.2f}s',fill='white')
    sheet.save(folder/'contact.jpg',quality=92)
    report=dict(sha256=hashlib.sha256(video.read_bytes()).hexdigest(),duration=duration,width=720,height=1280,
        fps=30,video_codec='h264',audio_codec='aac',audio_peak_db=peak,audio_mean_db=mean,
        full_decode=True,word_timing_bounds=True,encoded_contact_frames=len(indices),
        automatic_technical_checks='passed',creative_approval='pending_user_review',
        physical_iphone_playback='not_tested',production_integration='not_implemented')
    (folder/'technical-report.json').write_text(json.dumps(report,indent=2))
    (folder/'CREDITS.txt').write_text('Original procedural voxel models, pixel textures, animation and water/splash sounds.\n'
        'Narrator: Brian, licensed stock voice via ElevenLabs; '+lesson['narration_model']+'.\n'
        'Renderer: Remotion; Three.js 0.170.0 (MIT; license included alongside).\n'
        'Visual reference: user-supplied stock-market Minecraft video; no original media/assets reused.\n'
        'Lesson: illustrative common-pool resource story; compressed ecological time and fictional catch limits.\n'
        'Sources:\n'+'\n'.join(lesson['sources'])+'\n')
    (folder/'THREE-LICENSE.txt').write_bytes((LOCAL/'vendor/LICENSE').read_bytes())
    print(json.dumps(report,indent=2))
