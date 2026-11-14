"""Build a local, offline review gallery and contact sheets from actual renders."""
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".local/format-audition"


def build():
    registry = json.loads((OUT / 'registry.json').read_text())
    cards = []
    for spec in registry:
        folder = OUT / 'output' / spec['id']
        if not (folder / 'frame-9.png').exists():
            continue
        sheet = Image.new('RGB', (1620, 520), '#0b1425')
        for i, k in enumerate(spec.get('contact_frames', [0, 2, 4, 6, 8, 9])):
            with Image.open(folder / f'frame-{k}.png') as im:
                im.thumbnail((270, 480))
                sheet.paste(im, (i*270, 30))
        ImageDraw.Draw(sheet).text((15, 10),f"{spec['number']:02} | {spec['name']}",fill='white')
        sheet.save(folder/'contact.jpg',quality=92)
        esc = html.escape
        sid = spec['id']
        cards.append(f'''<article id="{sid}" data-id="{sid}" data-number="{spec['number']}">
<div class="number">{spec['number']:02} <span>{esc(spec['name'])}</span></div>
<video controls playsinline preload="none" poster="output/{sid}/frame-{spec.get('poster_frame', 0)}.png" src="output/{sid}/lesson.mp4"><track kind="captions" src="pack/{sid}/captions.vtt" srclang="en" label="English"></video>
<h2>{esc(spec['title'])}</h2><p class="grammar">{esc(spec['grammar'])}</p>
<div class="choices" role="group" aria-label="Rate {esc(spec['name'])}"><button data-rate="keep">Keep</button><button data-rate="potential">Potential</button><button data-rate="pass">Pass</button><button data-rate="">Clear</button></div>
<textarea rows="2" aria-label="Notes for {esc(spec['name'])}" placeholder="What works? What would you change?"></textarea>
<details><summary>{spec['duration']:.1f}s · sample details</summary><p>{esc(spec['limitation']) or 'Original programmatic illustration.'}</p><p>{esc(spec.get('credits', 'Live ElevenLabs narration; authored script and SVG scenes.'))} Experimental format, awaiting your review.</p><p><a href="output/{sid}/contact.jpg">Storyboard frames</a> · <a href="output/{sid}/lesson.mp4" download>MP4</a> · <a href="pack/{sid}/lesson.json">Script + timings</a></p></details></article>''')
    doc = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Format auditions · 19 samples</title>
<style>*{box-sizing:border-box}body{margin:0;background:#090d16;color:#eef2fa;font:16px/1.5 system-ui,sans-serif}header{max-width:1440px;margin:auto;padding:56px 28px 28px}h1{font-size:clamp(32px,5vw,58px);letter-spacing:-2px;line-height:1.1;margin:10px 0 20px}header p{color:#aab7cc;max-width:780px}header small{color:#7ce1d3;text-transform:uppercase;letter-spacing:3px}nav{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:24px 0}button,select{border:1px solid #384252;background:#151d2b;color:#eef2fa;padding:10px 16px;border-radius:8px;cursor:pointer;font:inherit}button:hover{border-color:#79d9c9}button.active{background:#174c43;border-color:#7ce1d3}button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #ffe367;outline-offset:3px}.grid{max-width:1440px;margin:auto;padding:0 28px 64px;display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:26px}article{padding:16px;background:#111827;border:1px solid #243045;border-radius:16px;align-self:start}.number{font-size:24px;font-weight:800;color:#7ce1d3;margin-bottom:14px;display:flex;gap:12px;align-items:center}.number span{font-size:14px;color:#acbdd3;font-weight:500}video{display:block;width:100%;aspect-ratio:9/16;max-height:580px;background:#0b1425;border-radius:8px}h2{font-size:20px;line-height:1.25;margin:20px 0 8px}.grammar{font-size:13px;color:#a4b4c9;min-height:40px}.choices{display:flex;gap:5px;flex-wrap:wrap}.choices button{padding:8px 11px;font-size:13px}textarea{display:block;width:100%;margin-top:12px;border-radius:8px;padding:10px;background:#0b1220;color:#eef2fa;border:1px solid #344155;font:inherit;font-size:13px;resize:vertical}details{margin-top:14px;font-size:12px;color:#a4b4c9}summary{cursor:pointer}a{color:#89b9ff}#status{font-size:13px;color:#9cabbf}.notice{padding:12px 16px;border-left:3px solid #7ce1d3;background:#111827;font-size:14px}article[hidden]{display:none}</style>
<header><small>Experimental format lab · batch 01</small><h1>Which ones should we keep?</h1><p>19 short lessons testing the formats from your research. Mark <b>Keep</b>, <b>Potential</b>, or <b>Pass</b>, or just tell me the sample numbers. Nothing is promoted into the production feed yet.</p><p class="notice">These are 2D / 2.5D format auditions. The science reveal, schematic map, causal timeline, technology diagram and illustrated POV are proxies for the more ambitious treatments in the research. A successful render does not establish learning or retention gains.</p><nav><select id="filter" aria-label="Filter ratings"><option value="all">All 19 samples</option value="keep">Keep</option><option value="potential">Potential</option><option value="pass">Pass</option><option value="unrated">Not rated</option></select><button id="export">Export feedback</button><span id="status" aria-live="polite"></span></nav></header><main class="grid">'''+''.join(cards)+'''</main>
<script>const key='hackumass-format-audition-v1';let feedback={};try{feedback=JSON.parse(localStorage.getItem(key)||'{}')}catch{}const articles=[...document.querySelectorAll('article')];const status=document.querySelector('#status');function update(){let n=0;for(const a of articles){const item=feedback[a.dataset.id]||{};if(item.rating)n++;for(const b of a.querySelectorAll('[data-rate]')){const on=b.dataset.rate!==''&&b.dataset.rate===item.rating;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on))}const f=document.querySelector('#filter').value;a.hidden=f!=='all'&&(f==='unrated'?!!item.rating:item.rating!==f)}status.textContent=n+' / '+articles.length+' rated · saved in this browser'}function save(){try{localStorage.setItem(key,JSON.stringify(feedback));update()}catch{status.textContent='Browser storage unavailable. Use Export feedback before closing.'}}for(const a of articles){const id=a.dataset.id;const note=a.querySelector('textarea');note.value=feedback[id]?.note||'';a.addEventListener('click',e=>{const b=e.target.closest('[data-rate]');if(!b)return;feedback[id]={...feedback[id],number:Number(a.dataset.number),rating:b.dataset.rate};save()});note.addEventListener('input',()=>{feedback[id]={...feedback[id],number:Number(a.dataset.number),note:note.value};save()})}document.querySelector('#filter').addEventListener('change',update);document.querySelector('#export').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({batch:'format-audition-v1',feedback},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='format-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});document.addEventListener('play',e=>{if(e.target.tagName==='VIDEO')document.querySelectorAll('video').forEach(v=>{if(v!==e.target)v.pause()})},true);update();</script></html>'''
    doc = doc.replace('19 samples', f'{len(cards)} samples').replace('19 short lessons', f'{len(cards)} short lessons')
    (OUT/'index.html').write_text(doc)
    print(f'Gallery: {len(cards)} rendered samples')


if __name__ == '__main__':
    build()
