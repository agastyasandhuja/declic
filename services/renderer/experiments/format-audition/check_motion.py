"""Check two semantic trajectories in decoded final video frames, not just source math."""
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'.local/format-audition'


def center(image, box, color, axis=0):
    points=[(x,y) for y in range(box[1],box[3]) for x in range(box[0],box[2])
            if sum(abs(a-b) for a,b in zip(image.getpixel((x,y)),color))<65]
    if not points:
        raise ValueError('Expected moving object not found')
    return sum(point[axis] for point in points)/len(points)


def ffmpeg(*args):
    subprocess.run(['ffmpeg','-y','-v','error',*map(str,args)],check=True,capture_output=True,timeout=60)


def check_fall(sid):
    lesson=json.loads((OUT/'pack'/sid/'lesson.json').read_text())
    folder=OUT/'output'/sid; video=folder/'lesson.mp4'; frames=folder/'motion-check'
    frames.mkdir(exist_ok=True)
    scene=lesson['segments'][2];points=[]
    for i in range(7):
        time=scene['start']+(scene['end']-scene['start'])*i*.10
        file=frames/f'{i}.png'
        ffmpeg('-ss',time,'-i',video,'-frames:v',1,file)
        with Image.open(file) as src:
            image=src.convert('RGB')
            light=center(image,(180,300,275,740),(99,228,229),1)
            heavy=center(image,(420,300,520,740),(255,114,159),1)
        points.append(dict(time=time,light_y=light,heavy_y=heavy))
    separation=max(abs(p['light_y']-p['heavy_y']) for p in points)
    descent=points[-1]['light_y']-points[0]['light_y']
    assert separation<2 and descent>240
    return dict(id=sid,sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                max_vertical_separation_pixels=separation,descent_pixels=descent,passed=True)


def check_pendulum():
    sid='variable';lesson=json.loads((OUT/'pack'/sid/'lesson.json').read_text())
    folder=OUT/'output'/sid;video=folder/'lesson.mp4';frames=folder/'motion-check'
    frames.mkdir(exist_ok=True)
    ffmpeg('-ss',lesson['segments'][1]['start']+1,'-i',video,'-t',16,'-vf','fps=4,scale=360:640',frames/'frame-%03d.png')
    centers=[[],[]]
    for file in sorted(frames.glob('frame-*.png')):
        with Image.open(file) as src:
            image=src.convert('RGB')
            centers[0].append(center(image,(70,190,140,255),(99,228,229)))
            centers[1].append(center(image,(180,280,310,365),(255,114,159)))
    def mae(values,lag):
        return sum(abs(x-y) for x,y in zip(values,values[lag:]))/(len(values)-lag)
    result=dict(short_4s_repeat_error_px=mae(centers[0],16),
                long_8s_repeat_error_px=mae(centers[1],32),
                long_4s_opposite_phase_difference_px=mae(centers[1],16))
    assert result['short_4s_repeat_error_px']<1.5
    assert result['long_8s_repeat_error_px']<1.5
    assert result['long_4s_opposite_phase_difference_px']>15
    return dict(id=sid,sha256=hashlib.sha256(video.read_bytes()).hexdigest(),passed=True,**result)


if __name__=='__main__':
    results=[check_fall('myth'),check_fall('predict'),check_pendulum()]
    (OUT/'semantic-motion-checks.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
