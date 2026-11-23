from pathlib import Path
from episode_plan import save
def finish_report(plan,level,out,result):
    from video_policy1104 import verify_disabled
    verify_disabled(out)
    ok=result.get('status')=='completed' and bool(result.get('protocol_verified'))
    result=dict(result,report_verified=ok,video_required=False,videos_verified=None,video_disabled_verified=True,recording_policy=plan['recording_policy'])
    save(Path(out)/'RESULT.json',result)
    return result,ok

OPENAI_MODEL_SNAPSHOTS = {
    "gpt-5": "gpt-5-2025-08-07",
    "gpt-5.1": "gpt-5.1-2025-11-13",
    "gpt-5.2": "gpt-5.2-2025-12-11",
    "gpt-5.4-mini": "gpt-5.4-mini-2026-03-17",
    "gpt-5.4-nano": "gpt-5.4-nano-2026-03-17",
    "gpt-5.4": "gpt-5.4-2026-03-05"
}

def openai_action_identity(requested, calls):
    returned = []
    rejected = []
    for step, call in enumerate(calls, 1):
        actual = call.get('returned_model')
        if isinstance(actual, str) and actual not in returned:
            returned.append(actual)
        sent = call.get('requested_model', call.get('model'))
        if not (
            call.get('provider') == 'openai_official'
            and isinstance(requested, str) and requested
            and sent == requested
            and isinstance(actual, str) and actual
            and (actual == requested or OPENAI_MODEL_SNAPSHOTS.get(requested) == actual)
        ):
            rejected.append(step)
    return {'requested_model': requested, 'returned_models': returned,
            'rejected_call_numbers': rejected, 'verified': bool(calls) and not rejected}
