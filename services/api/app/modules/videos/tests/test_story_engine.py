from types import SimpleNamespace
import pytest
from app.modules.videos.generation.story_engine import (
    Audit, Candidates, StoryPlan, fingerprint, load_history, novelty_issues,
    plan_story, save_history, record_feedback, audit_story, select_narrator,
)

def brief(owner=None):
    return SimpleNamespace(scope='private' if owner else 'shared_generic_candidate',owner_user_id=owner,
      objective_id='friction',approved_facts=[SimpleNamespace(fact_id='f1')],must_cover=['f1'],
      teaching_payload=lambda:{'approved_facts':[{'fact_id':'f1','statement':'Ground friction supplies traction.'}]})

def candidate(prop='phone',joke='That was an expensive gravity demonstration.'):
    lines=[
      'What happens when a familiar object suddenly loses the friction you rely on?',
      'Your phone slips from your fingers and lands on the carpet. '+joke,
      'Across the room, a chair keeps sliding because nothing supplies a horizontal stopping force.',
      'Why does this happen? Friction resists relative sliding between contacting surfaces.',
      'Watch the force arrow oppose the sliding direction while the velocity arrow shrinks.',
      'With that force removed, the velocity remains constant until another object pushes back.',
      'The same mechanism explains why ordinary ground contact lets a planted foot propel you forward.'
    ]
    return StoryPlan(title='A local example',approach='everyday_failure',central_question=lines[0],everyday_goal='Get ready for class without dropping anything',
      beats=[dict(beat_id=f'b{i}',kind=['hook','consequence','consequence','why','demonstration','demonstration','payoff'][i],
        setting='home',prop_key=f'{prop}_{i}',spoken_text=line,fact_ids=['f1'],
        visible_action='Show the object moving and its contact forces changing.',end_state='Object reaches the carpet and remains supported.',diagram_notation=[])
        for i,line in enumerate(lines)],
      jokes=[dict(beat_id='b1',technique='understatement',setup='The object slips.',punchline=joke,
        mechanism_connection='The loss of friction allows a supported object to slide.',expected_outcome='Keep the phone safely in hand',visible_reversal='The phone lands on the carpet instead',timing='after_visible_result')],voice_direction='Clear male narrator, brief matter-of-fact reaction.')

def test_exact_and_renamed_stories_are_rejected():
    b=brief();a=candidate();h=fingerprint(a,b)
    assert 'Exact story already used' in novelty_issues(a,b,[h])
    other=a.model_copy(deep=True);other.title='Different title'
    assert 'Punchline already used' in novelty_issues(other,b,[h])
    assert 'Too many repeated setting/prop combinations' in novelty_issues(other,b,[h])

def test_cross_owner_history_fails_before_any_model_call(tmp_path):
    h=fingerprint(candidate(),brief('alice'))
    class Never:
        def structured(self,*a,**kw):raise AssertionError('Must reject before model access')
    with pytest.raises(ValueError,match='Cross-owner'):
        plan_story(Never(),brief('bob'),[h])
    with pytest.raises(ValueError,match='scope'):
        save_history(tmp_path,brief('bob'),[h])
    save_history(tmp_path,brief('alice'),[h])
    assert load_history(tmp_path,brief('bob'))==[]

def test_prose_labels_and_unsaid_punchlines_are_rejected():
    notation=candidate().model_dump();notation['beats'][0]['diagram_notation']=['f_s','2v ⇒ 4F']
    assert StoryPlan.model_validate(notation).beats[0].diagram_notation==['f_s','2v ⇒ 4F']
    data=candidate().model_dump();data['beats'][0]['diagram_notation']=['GRIP ZONE']
    with pytest.raises(ValueError):StoryPlan.model_validate(data)
    data=candidate().model_dump();data['jokes'][0]['punchline']='An invented line.'
    with pytest.raises(ValueError,match='actually occur'):StoryPlan.model_validate(data)

def test_humor_pattern_rotates_after_two_uses():
    b=brief();p=candidate();history=[fingerprint(p,b),fingerprint(p,b)]
    assert any('primary joke mechanism' in x for x in novelty_issues(p,b,history))

def test_false_pass_with_factual_issues_never_escapes():
    # Bypass candidate generation validation to isolate the downstream audit gate.
    class BadAudit:
        def structured(self,schema,system,payload,*args):
            if schema is Candidates:return Candidates(candidates=[candidate(),candidate(),candidate()])
            if schema is StoryPlan:return candidate()
            return Audit(passed=True,factual_issues=['Unsupported mechanism'],visual_issues=[],humor_issues=[])
    with pytest.raises(ValueError,match='STORY_REVIEW_REQUIRED'):
        plan_story(BadAudit(),brief())

def test_missing_fact_coverage_is_rejected():
    class Missing:
        def structured(self,schema,system,payload,validate):
            plans=[candidate(),candidate(),candidate()]
            plans[0].beats[0].fact_ids=['invented']
            return validate(Candidates(candidates=plans))
    with pytest.raises(ValueError,match='approved facts'):
        plan_story(Missing(),brief())

def test_user_feedback_is_preserved_and_scope_bound(tmp_path):
    owner=brief('alice');item=fingerprint(candidate(),owner)
    save_history(tmp_path,owner,[item])
    assert item.user_verdict=='unreviewed'
    record_feedback(tmp_path,owner,item.plan_digest,'potential','Good structure; improve animation.')
    assert load_history(tmp_path,owner)[0].feedback_notes=='Good structure; improve animation.'
    with pytest.raises(ValueError,match='Unknown plan'):
        record_feedback(tmp_path,brief('bob'),item.plan_digest,'keep','')

def test_audit_gets_scoped_history_for_semantic_joke_comparison():
    b=brief();p=candidate();h=fingerprint(p,b)
    class Spy:
        def structured(self,schema,system,payload):
            assert payload['recent'][0]['punchlines']==h.punchlines
            assert 'semantic repeats' in system
            return Audit(passed=False,factual_issues=[],visual_issues=[],humor_issues=['Same joke with new wording'])
    assert audit_story(Spy(),b,p,[h]).humor_issues

def test_direct_audit_rejects_cross_owner_history():
    class Never:
        def structured(self,*args):raise AssertionError('No model access')
    with pytest.raises(ValueError,match='Cross-owner'):
        audit_story(Never(),brief('bob'),candidate(),[fingerprint(candidate(),brief('alice'))])

def test_repair_is_grounded_and_reaudited_before_return():
    class RepairClient:
        audits=0
        repairs=0
        def structured(self,schema,system,payload,*args):
            # This test isolates repair orchestration from the alternative-variety gate.
            if schema is Candidates:return Candidates(candidates=[candidate(),candidate(),candidate()])
            if schema is StoryPlan:
                self.repairs+=1
                p=candidate();p.beats[1].end_state='The phone lands supported on the carpet after contact.'
                return args[0](p)
            self.audits+=1
            if self.audits==1:
                return Audit(passed=False,factual_issues=[],visual_issues=['Show the landing'],humor_issues=[])
            assert 'after contact' in payload['story']['beats'][1]['end_state']
            return Audit(passed=True,factual_issues=[],visual_issues=[],humor_issues=[])
    client=RepairClient();p,a,h=plan_story(client,brief())
    assert a.passed and client.audits==2 and client.repairs==1
    assert 'after contact' in p.beats[1].end_state
    assert h.comic_situations

def test_male_narrator_rotation_avoids_two_recent_leads_and_owner_mixing():
    b=brief();history=[];voices=[]
    for _ in range(6):
        voice=select_narrator(b,history)['voice_id']
        assert voice not in voices[-2:]
        voices.append(voice)
        h=fingerprint(candidate(),b);h.narrator_voice_id=voice;history.append(h)
    assert len(set(voices[:4]))==4
    with pytest.raises(ValueError,match='Cross-owner'):
        select_narrator(brief('bob'),[fingerprint(candidate(),brief('alice'))])

def test_scene_directions_cannot_smuggle_in_extra_caption_text():
    data=candidate().model_dump()
    data['beats'][0]['visible_action']="Show the room. Pop caption: 'Zero grip zone'."
    with pytest.raises(ValueError,match='Caption text'):
        StoryPlan.model_validate(data)
