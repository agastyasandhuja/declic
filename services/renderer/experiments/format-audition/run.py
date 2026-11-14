"""Bounded isolated audition render. Does not build images, publish or modify the feed."""
import argparse
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).resolve().parent
LOCAL = ROOT / '.local/format-audition'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['stills', 'video'])
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    if args.only:
        ids = {p.name for p in (LOCAL/'pack').iterdir() if p.is_dir()}
        if not set(args.only.split(',')) <= ids:
            parser.error('Unknown sample ID')
    (LOCAL/'output').mkdir(parents=True, exist_ok=True)
    suffix = '-' + hashlib.sha256(args.only.encode()).hexdigest()[:8] if args.only else ''
    name = f'format-audition-{args.mode}{suffix}'
    command = ['docker','run','--rm','--name',name,'--network','none','--read-only',
               '--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges',
               '--cpus','4','--memory','4g','--pids-limit','256','--shm-size','512m',
               '--ulimit','fsize=1073741824:1073741824','--tmpfs','/tmp:rw,nosuid,size=1536m,mode=1777',
               '--mount',f'type=bind,src={SOURCE},dst=/opt/renderer/audition,readonly',
               '--mount',f'type=bind,src={ROOT}/services/renderer/src/PopCaptions.tsx,dst=/opt/renderer/PopCaptions.tsx,readonly',
               '--mount',f'type=bind,src={LOCAL}/pack,dst=/job,readonly',
               '--mount',f'type=bind,src={LOCAL}/output,dst=/output',
               '-e',f'AUDITION_MODE={args.mode}','-e',f'AUDITION_ONLY={args.only}',
               '--entrypoint','node','hackumass-renderer:reference-v7','/opt/renderer/audition/render.mjs']
    try:
        subprocess.run(command,check=True,timeout=3600)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        subprocess.run(['docker','stop',name],check=False,timeout=20)
        raise
