"""Inspect actual exports and bind technical reports to media hashes."""
import hashlib
import json
import re
import subprocess
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'.local/friction-story'


def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=120)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--only',default='')
    args=parser.parse_args()
    reports=[]
    for spec in json.loads((OUT/'registry.json').read_text()):
        if args.only and spec['id'] not in args.only.split(','):
            continue
        folder=OUT/'output'/spec['id']
        video=folder/'lesson.mp4'
        lesson=json.loads((OUT/'pack'/spec['id']/'lesson.json').read_text())
        digest=hashlib.sha256(video.read_bytes()).hexdigest()
        cached=folder/'technical-report.json'
        if cached.exists():
            saved=json.loads(cached.read_text())
            if saved.get('sha256')==digest:
                reports.append(saved)
                print(f"Unchanged verified export: {spec['id']}",flush=True)
                continue
        data=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout)
        vs=next(s for s in data['streams'] if s['codec_type']=='video')
        au=next(s for s in data['streams'] if s['codec_type']=='audio')
        assert (vs['width'],vs['height'],vs['codec_name'],vs['pix_fmt'])==(720,1280,'h264','yuv420p')
        assert vs['r_frame_rate']=='30/1' and au['codec_name']=='aac'
        duration=float(data['format']['duration'])
        assert abs(duration-lesson['duration'])<.12
        assert all(0<=w['start']<=w['end']<=duration+.1 for c in lesson['captions'] for w in c['words'])
        audio=run(['ffmpeg','-hide_banner','-nostats','-i',str(video),'-af','volumedetect','-vn','-f','null','-']).stderr
        peak=float(re.search(r'max_volume: ([-\d.]+) dB',audio).group(1))
        mean=float(re.search(r'mean_volume: ([-\d.]+) dB',audio).group(1))
        assert -45<mean<-3 and peak<=0
        # Decode every video frame, not only a header probe.
        run(['ffmpeg','-v','error','-i',str(video),'-an','-f','null','-'])
        report=dict(id=spec['id'],sha256=digest,
                    duration=duration,width=720,height=1280,fps=30,video='h264',audio='aac',
                    audio_mean_db=mean,audio_peak_db=peak,full_video_decode=True,
                    caption_bounds=True,automatic_technical_checks='passed',
                    human_creative_review='pending',device_playback='not_tested')
        (folder/'technical-report.json').write_text(json.dumps(report,indent=2))
        reports.append(report)
        print(f"Verified {spec['number']:02} {spec['id']}: {duration:.1f}s, peak {peak} dB",flush=True)
    (OUT/'technical-report.json').write_text(json.dumps(reports,indent=2))
