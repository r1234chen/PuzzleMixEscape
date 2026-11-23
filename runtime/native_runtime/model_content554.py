from pathlib import Path
from PIL import Image
import json, base64
from observation1280 import WIDTH, HEIGHT, rules_for_budget
ACTION_FIELDS = ('action', 'distance', 'direction', 'degrees', 'part', 'code', 'point', 'photo', 'target', 'item', 'query')

def _paths(row, decision=False):
    if decision:
        value = row.get('decision_images') or ([row['decision_image']] if row.get('decision_image') else None)
        if value:
            return tuple((Path(p) for p in value))
    return tuple((Path(p) for p in row.get('images') or ([row['image']] if row.get('image') else [])))

def _body(row):
    action = {k: v for k, v in row.get('action', {}).items() if k in ACTION_FIELDS}
    feedback = row.get('feedback', row.get('result', ''))
    if isinstance(feedback, dict):
        feedback = feedback.get('text', '')
    return json.dumps(action, ensure_ascii=False) + ' -> ' + str(feedback or '')

def build_prompt_parts(packet, include_recent=True):
    cap = int(packet.get('action_limit', 80))
    holding = ', '.join(packet.get('holding', [])) or 'nothing'
    notes = packet.get('notes', [])
    note_text = '\nYour notes:\n' + ('\n'.join((f"{n['number']}. [step {n['step']}] {n['text']}" for n in notes)) if notes else '(none yet)')
    header = rules_for_budget(cap) + f"\n\nYou are holding: {holding}.\nActions left: {packet.get('actions_left', max(0, cap - int(packet.get('step', 0))))}.\nRecalls left: {packet.get('recalls_left', 8)}.\n" + note_text + '\n\nYour last 10 steps:'
    parts = [header]
    now = _paths(packet)
    shown = {}
    recent = packet.get('recent', [])[-10:] if include_recent else []
    if not recent:
        parts.append('\n(none yet)')
    for row in recent:
        views = _paths(row, decision=True)
        step = row['step']
        body = _body(row)
        if not views:
            parts.append(f'\n[step {step}] ' + body)
        elif views == now:
            parts.append(f'\n[step {step}] (same view as your current view) ' + body)
        elif views in shown:
            parts.append(f'\n[step {step}] (same view as step {shown[views]}) ' + body)
        else:
            shown[views] = step
            parts.extend([f'\n[step {step}]\n', *views, '\n' + body])
    recalls = packet.get('recall_log', [])
    if recalls:
        agg = {}
        for r in recalls:
            query = str(r.get('query', '')).strip()
            if query:
                agg[query] = (int(r.get('found', 0)), agg.get(query, (0, 0))[1] + 1)
        if agg:

            def entry(q, n, c):
                return json.dumps(q, ensure_ascii=False) + ' -> ' + (str(n) + (' entry' if n == 1 else ' entries') if n else 'nothing found') + (f' (asked {c} times)' if c > 1 else '')
            parts.append('\nRecalls so far this game: ' + '; '.join((entry(q, n, c) for q, (n, c) in agg.items())) + '.')
    if packet.get('recall_requested'):
        parts.append('\n\nResult of the recall you just made:\n' + str(packet.get('recall_feedback', '')))
        for row in packet.get('recall', []):
            parts.extend([f"\n  [step {row['step']}]\n", *_paths(row, decision=True), '\n  ' + _body(row)])
    if now:
        parts.extend(['\n\nYour current view:\n', *now, '\nThe last photo above is your current view; you can only act on things in it. Reply with one JSON object.'])
    else:
        parts.append('\n\nThere is no photo in front of you yet. Reply with one JSON object.')
    return parts

def build_model_user_content(packet, include_recent=True):
    content = []
    for value in build_prompt_parts(packet, include_recent):
        if isinstance(value, Path):
            if value.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
                raise ValueError('Expected a local PNG/JPEG observation')
            with Image.open(value) as im:
                if im.size != (WIDTH, HEIGHT):
                    raise ValueError('Model input must remain640x360; no resizing fallback')
            mime = 'image/png' if value.suffix.lower() == '.png' else 'image/jpeg'
            content.append({'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + base64.b64encode(value.read_bytes()).decode('ascii')}})
        else:
            content.append({'type': 'text', 'text': str(value)})
    return content
