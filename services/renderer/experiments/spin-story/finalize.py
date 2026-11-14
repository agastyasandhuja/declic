"""Normalize Remotion's full-range export to ordinary phone-compatible H.264."""
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'.local/spin-story/output/spinning-chair'
if __name__=='__main__':
    movie=OUT/'lesson.mp4'
    result=subprocess.run(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=pix_fmt','-of','json',str(movie)],capture_output=True,text=True,check=True,timeout=30)
    if json.loads(result.stdout)['streams'][0]['pix_fmt']=='yuv420p':
        print('Already normalized');raise SystemExit(0)
    temporary=OUT/'lesson-normalized.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-vf',
        'scale=in_range=pc:out_range=tv,format=yuv420p','-c:v','libx264','-preset','medium',
        '-crf','18','-color_range','tv','-c:a','copy','-movflags','+faststart',str(temporary)],
        check=True,timeout=600)
    # Preserve the original render for audit; only replace the final after success.
    movie.replace(OUT/'render-original.mp4')
    temporary.replace(movie)
    print('Normalized full-range render to yuv420p')
