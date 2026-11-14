"""Render only staged original content in the existing bounded, secret-free container."""
import argparse
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
SOURCE=Path(__file__).resolve().parent
LOCAL=ROOT/'.local/voxel-story'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['stills','video'])
    args=parser.parse_args()
    (LOCAL/'output').mkdir(exist_ok=True,parents=True)
    name=f'voxel-story-{args.mode}'
    command=['docker','run','--rm','--name',name,'--network','none','--read-only',
        '--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges',
        '--cpus','4','--memory','4g','--pids-limit','256','--shm-size','512m',
        '--ulimit','fsize=1073741824:1073741824','--tmpfs','/tmp:rw,nosuid,size=1536m,mode=1777',
        '--mount',f'type=bind,src={SOURCE},dst=/opt/renderer/audition,readonly',
        '--mount',f'type=bind,src={ROOT}/services/renderer/src/PopCaptions.tsx,dst=/opt/renderer/PopCaptions.tsx,readonly',
        '--mount',f'type=bind,src={LOCAL}/vendor,dst=/vendor,readonly',
        '--mount',f'type=bind,src={LOCAL}/pack,dst=/job,readonly',
        '--mount',f'type=bind,src={LOCAL}/output,dst=/output',
        '-e',f'AUDITION_MODE={args.mode}','--entrypoint','node',
        'hackumass-renderer:reference-v7','/opt/renderer/audition/render.mjs']
    try:
        subprocess.run(command,check=True,timeout=3600)
    except (subprocess.TimeoutExpired,KeyboardInterrupt):
        subprocess.run(['docker','stop',name],check=False,timeout=20)
        raise
