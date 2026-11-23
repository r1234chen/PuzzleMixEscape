import math
WIDTH = 640
HEIGHT = 360
RENDER_WIDTH = 1280
RENDER_HEIGHT = 720
FX = FY = 320.0
CX = 320.0
CY = 180.0
PROFILE = 'new88_native_640x360_v1'
MODEL_TEMPLATE_ID = 'user_approved_exact_20261027'
PROMPT_PARENT_SHA256 = '019c4439ee80a1855fc8bfc53470be855a19d0278fd9a46a9028d141e39c6966'
MODEL_INSTRUCTIONS = 'You are a robot locked in a room. Your goal is to get out of the room.The door is locked. What opens it is not told in this message; you have to find out by searching the room.Papers and notes in the room may give you hints.Things can be hidden inside furniture that opens, and some things are locked themselves.To win, open the exit door.\nEach turn you see what you are holding, your own notes, your last 10 steps and, at the end, a photo of your current view.Each of the last steps is shown with the photo you were looking at when you chose it, the action you took and any available feedback(recalls are listed separately). Older steps are NOT shown; they are kept in your memory, which you can search with recall.\nChoose exactly one action:\n{"action": "walk", "distance": 0.25 | 0.5 | 1.0}\n{"action": "turn", "direction": "left" | "right" | "up" | "down", "degrees": 10-120}\n(left / right turn you in place; up / down tilt your head)\n{"action": "step_back", "distance": 0.1-0.6}\n{"action": "side_step", "direction": "left" | "right", "distance": 0.1-0.5}\n(step back or sideways while keeping your facing direction)\n{"action": "open", "point": [x, y], "target": "<what>", "part": <number>}\n{"action": "close", "point": [x, y], "target": "<what>", "part": <number>}\n{"action": "take", "point": [x, y], "target": "<what>"}\n{"action": "read", "point": [x, y], "target": "<what>"} the item in your hand needs no point\n{"action": "unlock", "point": [x, y], "target": "<what>", "part": <number>, "code": "<digits>"} a locked item in your hand needs no point\n{"action": "use", "point": [x, y], "target": "<what>"} uses/place the item in your hand on the thing you point at,or on another item in your hand (that one needs no point; "target" names it)\n(when you hold several items, add "item": "<a word for the one you mean>" to read / use)\n{"action": "press", "point": [x, y], "target": "<what>"}\n{"action": "recall", "query": "<words to search your memory for>"}\n(recall searches only the steps older than your last 10 steps, by the actions you took and what happened, and shows each step it finds with the photo you were looking at then.)\nRecall has a separate budget and does not use an action. Every recall attempt uses one recall, even if nothing is found. When Recalls left is 0, recall is unavailable.\nFor open / close / unlock on furniture, add "part": <number>: count drawers and doors column by column from the top left, starting at 1. Point at the whole piece of furniture. Room doors and items in your hand need no part.\n"point" says which thing you mean: the position of that thing in the photo of your current view, in pixels: x from 0 (left edge) to 640 (right edge) and y from 0 (top) to 360 (bottom). "target" is one or two words naming the whole thing you point at (cabinet, door, note, ...).\nYou can only act on things in your current view, and you must be close to them. \nWhen you look for something, scan by turning in one direction; do not spin or alternate left and right turns. If you could not move, do not repeat the same walk; turn or step back instead.\nDo not guess codes. Only enter a code that you have actually found written somewhere in the room;trying numbers one after another is not allowed.\nYou can add "note": "<one sentence>" to any action to write down what you think is important; your notes are shown to you every turn (at most 20 notes; "drop_notes": [<note numbers>] removes notes).\nEvery reply must include "thought": one short sentence on why you take this action.\nReply with exactly one JSON object:\n{"thought": "<why you take this action>", "action": "<one of the actions above>", ...its parameters...}\nYou have at most 80 actions.'

def rules_for_budget(limit=80):
    return MODEL_INSTRUCTIONS.replace('You have at most 80 actions.', f'You have at most {int(limit)} actions.')

def validate_action(action, recalls_left=5):
    from protocol import validate_action as legacy_validate
    original = None
    if isinstance(action, dict) and 'point' in action:
        original = action['point']
        if not isinstance(original, list) or len(original) != 2:
            raise ValueError('point requires [x,y] in640x360 pixels')
        if any((type(v) not in (int, float) or not math.isfinite(v) for v in original)):
            raise ValueError('point must contain finite pixel coordinates')
        if not (0 <= original[0] < WIDTH and 0 <= original[1] < HEIGHT):
            raise ValueError('point out of range: 0<=x<640, 0<=y<360')
        check = dict(action, point=[original[0] * 640 / WIDTH, original[1] * 360 / HEIGHT])
    else:
        check = action
    clean = legacy_validate(check, recalls_left)
    if original is not None:
        clean['point'] = list(original)
    return clean

def prepare_observation(rgb, depth):
    import numpy as np
    from PIL import Image
    if rgb.shape[:2] != (RENDER_HEIGHT, RENDER_WIDTH) or depth.shape != (RENDER_HEIGHT, RENDER_WIDTH):
        raise ValueError('Expected1280x720 native RGB/depth before640x360 model conversion')
    rows = np.arange(HEIGHT) * RENDER_HEIGHT // HEIGHT
    cols = np.arange(WIDTH) * RENDER_WIDTH // WIDTH
    model_depth = np.asarray(depth, dtype=np.float32)[rows[:, None], cols[None, :]].copy()
    return (Image.fromarray(rgb[:, :, :3]).copy(), model_depth)
