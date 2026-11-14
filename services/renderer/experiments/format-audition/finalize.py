"""Normalize renderer exports to browser-friendly limited-range video and level audio."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'.local/format-audition'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--only',default='')
    args=parser.parse_args()
    for spec in json.loads((OUT/'registry.json').read_text()):
        if args.only and spec['id'] not in args.only.split(','):
            continue
        folder=OUT/'output'/spec['id']; video=folder/'lesson.mp4'; report=folder/'finalization.json'
        before=sha(video)
        if report.exists() and json.loads(report.read_text()).get('output_sha256')==before:
            continue
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)],timeout=30))
        v=next(s for s in probe['streams'] if s['codec_type']=='video')
        temp=folder/'normalized.mp4'
        command=['ffmpeg','-y','-v','error','-i',str(video)]
        if v['pix_fmt']=='yuvj420p':
            command+=['-vf','scale=in_range=pc:out_range=tv','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-color_range','tv','-threads','2']
        else:
            command+=['-c:v','copy']
        command+=['-af','loudnorm=I=-16:TP=-1:LRA=11','-ar','48000','-c:a','aac','-b:a','160k','-movflags','+faststart',str(temp)]
        subprocess.run(command,check=True,capture_output=True,timeout=180)
        os.replace(temp,video)
        report.write_text(json.dumps(dict(input_sha256=before,output_sha256=sha(video),
                                        video_range='limited',audio_target_lufs=-16),indent=2))
        print(f"Finalized {spec['number']:02} {spec['id']}",flush=True)
