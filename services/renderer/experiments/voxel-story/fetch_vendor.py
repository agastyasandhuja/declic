"""Download only pinned public renderer bytes. No installs, scripts or reference uploads."""
import hashlib
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
FILES={
    'build/three.module.js':'ce1fa418de16a19495a9f72495580e3015d7745c296d3ce0485897f902ddedfb',
    'LICENSE':'4c40a1ef62450b857c3b2aaf294936304cd552d965fbcd9d32d4c5bcf4ba4454',
}
if __name__=='__main__':
    out=ROOT/'.local/voxel-story/vendor';out.mkdir(parents=True,exist_ok=True)
    for name,expected in FILES.items():
        target=out/Path(name).name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==expected:
            print(f'Verified cached {target.name}');continue
        with urllib.request.urlopen('https://unpkg.com/three@0.170.0/'+name,timeout=60) as response:
            data=response.read(2_000_001)
        if len(data)>2_000_000 or hashlib.sha256(data).hexdigest()!=expected:
            raise ValueError('Dependency integrity mismatch')
        target.write_bytes(data)
        print(f'Verified {target.name}')
