from pathlib import Path
import copy

def action_turn(row, tip_event=None):
    result = copy.deepcopy(row['result'])
    tip = None
    if tip_event and int(tip_event['step']) == int(row['step']):
        tip = str(tip_event['text'])
        text = str(result.get('text', ''))
        if text.endswith(tip):
            result['text'] = text[:-len(tip)].rstrip()
    result['images'] = list(row['model_images'])
    turn = {'turn': row['step'], 'counted': True, 'action': copy.deepcopy(row['action']), 'result': result, 'pos': row['camera_position']}
    if tip:
        turn['no_progress_hint'] = {'turn': row['step'], 'feedback_text': tip}
    return turn

class PromptView:

    def __init__(self, esc):
        self._esc = esc

    def __getattr__(self, name):
        return getattr(self._esc, name)

def compose(session):
    d = session.d
    if not hasattr(d, 'shared_legacy_session'):
        raise RuntimeError('Production native model prompt requires the real shared legacy executor')
    shared = d.shared_legacy_session
    e = shared.esc
    view = PromptView(e)
    from episode_plan import protocol
    window = protocol(session.bank_path.parent).budget(session.level)[2]
    view.cfg = dict(e.cfg, protocol='unified_v2', public_id=session.level, max_steps=session.action_cap, recall_budget=session.recall_cap, tip_window=window)
    view.t = d.step + 1
    view.notes = lambda: [(n['number'], n['step'], n['text']) for n in session.notes]
    first = list(d.rows[0].get('decision_images', [])) if d.rows else list(d.current_observation_images)
    turns = [{'turn': 0, 'counted': False, 'action': {'action': 'start'}, 'result': {'ok': True, 'text': '', 'images': first}}]
    logs = list(session.recall_log)
    current = logs[-1] if session.recall_requested and logs else None
    older = logs[:-1] if current is not None else logs
    for i, log in enumerate(older):
        turns.append({'turn': '0r' + str(i + 1), 'counted': False, 'action': {'action': 'recall', 'query': log.get('query', '')}, 'result': {'ok': not log.get('rejected', False), 'text': log.get('raw_feedback', ''), 'images': [], 'recalled': [[k, 0] for k in range(int(log.get('found', 0)))]}})
    for row in d.rows:
        turns.append(action_turn(row, session.policy.tip_event))
    memory = []
    if current is not None:
        found = []
        for row in session.recalled:
            key = int(row['step'])
            found.append([key, 0])
            memory.append({'mid': key, 'turn': key, 'text': ''})
        turns.append({'turn': str(d.step) + 'r' + str(session.recalls), 'counted': False, 'action': {'action': 'recall', 'query': current.get('query', '')}, 'result': {'ok': not current.get('rejected', False), 'text': session.recall_feedback, 'images': [], 'recalled': found}})
    view.turns = turns
    view.memory = memory
    session._composed_current_images = list(shared.C._views(view)[1])
    text = shared.C.prompt(view)
    parts = list(view._claw_contents)
    e._claw_contents = parts
    return (parts, text)
