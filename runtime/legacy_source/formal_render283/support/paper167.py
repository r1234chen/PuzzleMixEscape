import math
PAPER_LEGACY_LEVELS = ('R2-38_office_typewriter', 'R4-14_office_attic')

def typewriter_paper_policy(cfg, gadget):
    if cfg.get('legacy_name', cfg.get('name')) not in PAPER_LEGACY_LEVELS:
        return {}
    keypad = cfg.get('keypad') or {}
    if keypad.get('mode') != 'typewriter' or keypad.get('gadget') != gadget.get('name') or gadget.get('type') != 'reveal' or (gadget.get('flag') != 'paper_in'):
        return {}
    sheets = [item for item in cfg.get('scene_add', []) if item.get('name') == 'decor_tw_paper' and item.get('paper_in')]
    if len(sheets) != 1:
        return {}
    sheet = sheets[0]
    pose, angles = (sheet.get('position'), sheet.get('rpy_deg'))
    if not (isinstance(pose, (list, tuple)) and len(pose) == 3 and isinstance(angles, (list, tuple)) and (len(angles) == 3) and all((isinstance(v, (int, float)) and math.isfinite(v) for v in list(pose) + list(angles)))):
        return {}
    return {'typewriter': gadget['name'], 'paper_pose': list(pose), 'paper_rpy_deg': list(angles)}
