from pathlib import Path
from functools import lru_cache
import hashlib, json, re
ROOT = Path(__file__).resolve().parent
POLICY = 'required_marks_exclude_decoys_rest_and_traps268_v1'
METRIC_KEYS = {'milestones', 'milestone_total', 'milestone_completed', 'milestone_completion_rate', 'first_milestone_step', 'last_milestone_step', 'next_progress_after_tip_step', 'actions_until_progress_after_tip', 'milestone_policy', 'milestone_exclusions'}

def read(p):
    return json.loads(Path(p).read_text('utf8'))

def normalized(value):
    return ' '.join(str(value).strip().casefold().split())

@lru_cache(maxsize=1)
def catalog():
    default = read(ROOT / 'frozen_default.json')
    for host in ('local', 'server'):
        support = Path(default['host_settings'][host]['ESI_BUDGET_SUPPORT'])
        if (support / 'manifest.json').is_file():
            return (support, read(support / 'manifest.json'), read(support / 'level_aliases157.json'))
    raise RuntimeError('Frozen catalog missing; do not infer milestone roles from names')

def config_for(value):
    support, manifest, aliases = catalog()
    name = value.get('config_file') or value.get('config') or value.get('name')
    key = str(name).replace('\\', '/').rsplit('/', 1)[-1].removesuffix('.json')
    name = next((aliases[k][key] for k in ('by_new_name', 'by_new_id', 'by_legacy_name', 'by_legacy_id') if key in aliases.get(k, {})), None)
    if name is None:
        raise ValueError('Unknown level config: ' + key)
    p = support / 'catalog' / (name + '.json')
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert manifest['resource_hashes']['catalog/' + p.name] == digest, 'Frozen catalog hash mismatch'
    if value.get('config_sha256'):
        assert value['config_sha256'] == digest
    return read(p)

def exclusions_for(summary, cfg):
    excluded = {}

    def add(obj, reason):
        for k in ('id', 'name', 'display'):
            if obj.get(k) is not None:
                excluded[normalized(obj[k])] = reason
    collections = [cfg.get(k, []) for k in ('items', 'scene_add', 'gadgets', 'doors')]
    collections.append((summary.get('scoring_only') or {}).get('items', []))
    for objects in collections:
        for obj in objects:
            if normalized(obj.get('role', '')) in ('decoy', 'distractor') or normalized(obj.get('kind', '')) in ('decoy', 'distractor') or obj.get('decoy') is True or (obj.get('distractor') is True):
                add(obj, 'explicit_distractor')
    rest = {group for group, info in cfg.get('slot_groups', {}).items() if info.get('kind') == 'rest'}
    for group in rest:
        excluded[normalized(group)] = 'optional_rest_slot'
    for gadget in cfg.get('gadgets', []):
        if gadget.get('type') == 'slot' and gadget.get('group') in rest:
            for key in ('id', 'name'):
                if gadget.get(key) is not None:
                    excluded[normalized(gadget[key])] = 'optional_rest_slot'
    trap_locks = {(str(name), int(part)) for trap in cfg.get('traps', []) for name, part in trap.get('locks', [])}
    for lock in cfg.get('part_locks', []):
        if lock.get('latent') is True and (str(lock.get('container')), int(lock.get('part', 1))) in trap_locks:
            add(lock, 'trap_only_latent_lock')
    return excluded

def milestone_items(summary, cfg):
    excluded = exclusions_for(summary, cfg)
    kept = {}
    removed = {}
    for key, value in (summary.get('milestones') or {}).items():
        pieces = str(key).split(maxsplit=1)
        verb = normalized(pieces[0]) if pieces else ''
        target = normalized(pieces[1]) if len(pieces) > 1 else ''
        reason = 'negative_trap_event' if verb == 'trap' else excluded.get(target)
        if reason is None and ':' in target:
            reason = excluded.get(target.split(':', 1)[0])
        if reason:
            removed[key] = dict(reason=reason, step=value)
        else:
            kept[key] = value
    return (kept, removed)

def corrected_metrics(record, cfg, summary=None):
    from metrics268 import step
    s = summary or record.get('raw_summary') or dict(milestones=record.get('milestones', {}))
    kept, removed = milestone_items(s, cfg)
    achieved = {k: v for k, v in kept.items() if v is not None}
    progress = sorted({step(v) for v in achieved.values() if step(v) is not None})
    trigger = record.get('hint_trigger_step')
    nxt = min((x for x in progress if trigger is not None and x > trigger), default=None)
    out = dict(record)
    out.update(milestones=kept, milestone_total=len(kept), milestone_completed=len(achieved), milestone_completion_rate=len(achieved) / len(kept) if kept else None, first_milestone_step=min(progress, default=None), last_milestone_step=max(progress, default=None), next_progress_after_tip_step=nxt, actions_until_progress_after_tip=nxt - trigger if nxt is not None else None, milestone_policy=POLICY, milestone_exclusions=removed)
    return out
