import math
FAILURES = {'take': 'You cannot take this object.', 'open': 'This object cannot be opened.', 'close': 'This object cannot be closed.', 'use': 'You cannot use this item here.', 'unlock': 'This object cannot be unlocked.', 'press': 'This object cannot be pressed.', 'read': 'This object cannot be read.', 'recall': 'No relevant records found.'}
NO_OBJECT = 'No interactable object selected.'
TOO_FAR = 'Too far away to reach.'
NO_ITEM = 'You do not have this item.'
NO_RECALLS = 'No recalls remaining.'
COMMON = {NO_OBJECT, TOO_FAR, NO_ITEM, NO_RECALLS}

def failure_for(action):
    return FAILURES.get(action, 'Invalid action parameters.')

def movement_feedback(moved):
    amount = f'{max(0.0, float(moved)):.2f}'.rstrip('0').rstrip('.') or '0'
    return f'You moved {amount} m before being blocked. You cannot move farther.'

def input_failure(action, reason):
    if reason.startswith('Current target beyond'):
        return TOO_FAR
    if reason.startswith('Public standard walk blocked'):
        return movement_feedback(0)
    return NO_OBJECT

def public_feedback(action, result):
    if action == 'read' or not result.get('ok', False):
        return result.get('text', '') or failure_for(action)
    return ''

def swept_endpoint(start, delta, blocked, spacing=0.025):
    start = [float(x) for x in start]
    delta = [float(x) for x in delta]
    distance = math.sqrt(sum((x * x for x in delta)))
    n = max(1, math.ceil(distance / spacing))
    end = list(start)
    was_blocked = False
    for i in range(1, n + 1):
        p = [start[j] + delta[j] * i / n for j in range(len(start))]
        if blocked(p[0], p[1]):
            was_blocked = True
            break
        end = p
    moved = math.sqrt(sum(((end[j] - start[j]) ** 2 for j in range(len(start)))))
    return (end, moved, was_blocked)
