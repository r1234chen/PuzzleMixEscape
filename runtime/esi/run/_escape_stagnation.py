import hashlib
import json
import math
import os
import re
DEFAULT_RATIO = 0.25
FIFTY_ACTION_WINDOW = 20
STATE_VERSION = 1

def _event(kind, value):
    return kind + ':' + json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def progress_events(record, marks=None):
    result = record.get('result') or {}
    action = record.get('action') or {}
    ids = record.get('action_ids') or result.get('action_ids') or action
    kind, step = (action.get('action'), record.get('turn'))
    events = set()
    if isinstance(step, int):
        events.update((_event('milestone', key) for key, at in (marks or {}).items() if isinstance(at, int) and 0 <= at <= step))
    for boxes in (record.get('photo_boxes') or {}).values():
        for box in boxes:
            if isinstance(box, (list, tuple)) and box:
                events.add(_event('visible', box[0]))
    if not result.get('ok'):
        return events
    target = ids.get('object', ids.get('target', ids.get('item', action.get('target'))))
    part = ids.get('part', action.get('part'))
    if kind == 'open':
        events.add(_event('opened', result.get('opened') or [target, part]))
    elif kind == 'take':
        events.add(_event('taken', ids.get('item', target)))
    elif kind == 'read':
        text = str(result.get('text') or '')
        suffix = str(result.get('text_suffix') or '')
        if suffix and text.endswith(suffix):
            text = text[:-len(suffix)]
        for marker in ('It says:', 'In the mirror it read:'):
            if marker in text:
                text = text.split(marker, 1)[1].strip()
                if text.startswith('"') and '"' in text[1:]:
                    text = text[1:text.rfind('"')]
                break
        digest = hashlib.sha256(' '.join(text.split()).encode('utf-8')).hexdigest()
        events.add(_event('read', [ids.get('item', target), digest]))
    elif kind == 'unlock':
        events.add(_event('unlocked', [target, part]))
    elif kind in ('use', 'press'):
        noop = re.search('\\b(?:nothing happens|already full|is empty|no change)\\b', str(result.get('text') or ''), re.I)
        if not noop:
            events.add(_event('interaction', [kind, ids.get('item'), target, part]))
        rotated = result.get('rotated')
        if isinstance(rotated, dict) and rotated.get('turns') is not None:
            events.add(_event('orientation', [rotated.get('name', target), int(rotated['turns']) % 4]))
        for key in ('cycled', 'jug', 'slot'):
            if isinstance(result.get(key), dict) and (key != 'jug' or not noop):
                events.add(_event(key, result[key]))
        seq = (result.get('press') or {}).get('seq')
        if isinstance(seq, int) and seq > 0:
            events.add(_event('sequence', seq))
    return events

class StagnationMonitor:

    def __init__(self, max_actions, ratio=DEFAULT_RATIO, enabled=True, state=None):
        self.max_actions, self.ratio = (int(max_actions), float(ratio))
        if self.max_actions <= 0 or not math.isfinite(self.ratio) or (not 0 <= self.ratio <= 1):
            raise ValueError('Stagnation requires a positive action cap and a ratio from 0 to 1.')
        self.enabled = bool(enabled and self.ratio > 0)
        self.window = (FIFTY_ACTION_WINDOW if self.max_actions == 50 else max(1, math.ceil(self.max_actions * self.ratio))) if self.enabled else None
        state = state or {}
        self.seen = set(state.get('seen_progress') or [])
        self.actions = int(state.get('actions', 0))
        self.no_progress_actions = int(state.get('no_progress_actions', 0))
        self.last_progress_action = int(state.get('last_progress_action', 0))
        self.last_progress_events = list(state.get('last_progress_events') or [])
        self.won = bool(state.get('won', False))

    def observe(self, record, events=(), success=False):
        kind = (record.get('action') or {}).get('action')
        counted = bool(record.get('counted')) and kind != 'recall'
        if not self.enabled:
            return self.status()
        if record.get('turn') == 0 and (not counted):
            self.seen.update(events)
            return self.status()
        if not counted:
            return self.status()
        self.actions += 1
        new = sorted(set(events) - self.seen)
        self.seen.update(events)
        if new:
            self.no_progress_actions = 0
            self.last_progress_action = self.actions
            self.last_progress_events = new
        else:
            self.no_progress_actions += 1
        self.won = bool(success)
        status = self.status()
        status['new_progress'] = new
        return status

    def status(self):
        return {'enabled': self.enabled, 'ratio': self.ratio, 'window': self.window, 'actions': self.actions, 'no_progress_actions': self.no_progress_actions, 'last_progress_action': self.last_progress_action, 'triggered': bool(self.enabled and (not self.won) and (self.no_progress_actions >= self.window))}

    def early_stop(self):
        if not self.status()['triggered']:
            return None
        return {'reason': 'no_progress_or_loop', 'action': self.actions, 'window': self.window, 'ratio': self.ratio, 'no_progress_actions': self.no_progress_actions, 'last_progress_action': self.last_progress_action}

    def export_state(self):
        return {**self.status(), 'version': STATE_VERSION, 'seen_progress': sorted(self.seen), 'last_progress_events': self.last_progress_events, 'won': self.won}

def initialize(esc, enabled=True):
    ratio = os.environ.get('ESI_ESCAPE_STAGNATION_RATIO')
    ratio = esc.cfg.get('stagnation_ratio', DEFAULT_RATIO) if ratio in (None, '') else float(ratio)
    saved = getattr(esc, '_stagnation_checkpoint', None)
    if not isinstance(saved, dict) or saved.get('version') != STATE_VERSION:
        saved = None
    monitor = StagnationMonitor(esc.cfg.get('max_steps', 40), ratio, enabled, saved)
    if saved is None and monitor.enabled:
        for record in esc.turns:
            events = progress_events(record, getattr(esc, 'marks', {}))
            events.update((record.get('stagnation') or {}).get('new_progress') or [])
            if record.get('turn') == 0:
                result = record.get('result') or {}
                for gadget in esc.cfg.get('gadgets') or []:
                    if gadget.get('type') == 'rotator':
                        events.add(_event('orientation', [gadget['name'], int(gadget.get('turns', 0)) % 4]))
                    elif gadget.get('type') == 'cycle':
                        events.add(_event('cycled', {'name': gadget['name'], 'state': gadget.get('state', 0)}))
                for photo in result.get('images_boxed') or result.get('images') or []:
                    boxes = (getattr(esc, '_photo_dets', {}).get(str(photo)) or {}).get('boxes') or []
                    events.update((_event('visible', box[0]) for box in boxes if box))
            monitor.observe(record, events)
    monitor.won = bool(getattr(esc, 'success', False))
    esc._stagnation = monitor
    if monitor.early_stop() and (not esc.success) and (not getattr(esc, '_game_over', None)):
        esc._game_over = 'stagnation'
    return monitor

def update(esc, record):
    monitor = getattr(esc, '_stagnation', None)
    if monitor is None or not monitor.enabled:
        return
    events = progress_events(record, esc.marks)
    sequence = getattr(esc, 'switch_seq', None) or {}
    if isinstance(sequence.get('progress'), int) and sequence['progress'] > 0:
        events.add(_event('sequence', sequence['progress']))
    record['stagnation'] = monitor.observe(record, events, success=esc.success)
    if monitor.early_stop() and (not esc.success) and (not getattr(esc, '_game_over', None)):
        esc._game_over = 'stagnation'

def prompt_rule(esc):
    monitor = getattr(esc, '_stagnation', None)
    if monitor is None or not monitor.enabled:
        return ''
    percentage = monitor.window / monitor.max_actions if monitor.max_actions == 50 else monitor.ratio
    return f'\n\nYou lose if you make no new progress for {monitor.window} consecutive actions ({percentage:.0%} of your action budget). New progress means discovering a new object or clue, opening a previously unexamined part, obtaining an item, or advancing a puzzle. Repeated movement and already completed interactions do not reset this limit. Recall does not count toward this limit.'
