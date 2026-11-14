"""Run the story/humor planner locally; does not render, upload or publish a video."""
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
from .generation.providers import Claude
from .generation.story_engine import VERSION, NARRATORS, load_history, plan_story, save_history
from .media import atomic_json
from .models import Brief

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--count',type=int,choices=[1,2,3],default=1)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[5]
    load_dotenv(root/'.env');load_dotenv(root/'services/api/.env')
    brief=Brief.model_validate_json(args.brief.read_text())
    args.output.mkdir(parents=True,exist_ok=True)
    folder=args.output/'history'
    history=load_history(folder,brief)
    diagnostics=[]
    atomic_json(args.output/'diagnostics.json',diagnostics)
    def diagnostic(event):
        diagnostics.append(event)
        atomic_json(args.output/'diagnostics.json',diagnostics)
    client=Claude(model='claude-opus-5-5',cache_dir=args.output/'provider-cache',
        diagnostic=diagnostic,max_tokens=16000)
    results=[]
    error=None
    try:
        for index in range(args.count):
            plan,audit,item=plan_story(client,brief,history,run_id=f'{brief.objective_id}-{len(history)}')
            path=args.output/f'story-{len(history)+1:02}.json'
            atomic_json(path,dict(version=VERSION,status='audited_plan_needs_scene_authoring_and_user_review',
              plan=plan.model_dump(),audit=audit.model_dump(),fingerprint=item.model_dump(),
              narration=dict(next(v for v in NARRATORS if v['voice_id']==item.narrator_voice_id),
                             provider='elevenlabs',status='planned_not_synthesized')))
            history.append(item);save_history(folder,brief,history)
            results.append(dict(path=str(path),title=plan.title,
              situations=item.settings_and_props,joke_mechanisms=item.joke_techniques,
              word_count=sum(len(b.spoken_text.split()) for b in plan.beats)))
            print(json.dumps(results[-1]),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        error={'type':type(exc).__name__,'message':str(exc)[:1500]}
        raise
    finally:
        atomic_json(args.output/'usage.json',client.usage)
        atomic_json(args.output/'run-report.json',dict(version=VERSION,plans=results,
          status='failed' if error else 'completed',error=error,
          rendered=False,published=False,novelty_window=20))
        client.client.close()

if __name__=='__main__':main()
