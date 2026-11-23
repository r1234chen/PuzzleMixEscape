from pathlib import Path
import sys, json, importlib.util, types, math
ROOT = Path(__file__).resolve().parent

def install_driver(driver, public_id):
    import unified_protocol as P
    row = P.resolve(public_id)
    if row['kind'] != 'native_room':
        raise ValueError('Common native binding is for a new native room')
    runtime = Path(driver.level.__file__).parent
    root_runtime = ROOT / 'native_runtime'
    sys.path.insert(0, str(root_runtime))
    sys.path.insert(0, str(runtime))
    from legacy_entry import install_stack
    E, C, _ = install_stack()
    owner_path = ROOT / 'OWNER_PART_MAP.json'
    motion_path = ROOT / 'MOTION_BINDINGS.json'
    owners = json.loads(owner_path.read_text('utf8'))
    motions = json.loads(motion_path.read_text('utf8'))
    level = row['source_id']
    if row.get('room_family') == 'medium_v6':
        from legacy_h2_bridge import attach
        session = attach(driver, driver.run / 'common_executor', working=ROOT, E=E, C=C)
    elif level == 'R01':
        from legacy_r01_pilot import attach
        session = attach(driver, driver.run / 'common_executor', working=ROOT, E=E, C=C)
    elif level == 'R02':
        from legacy_r02_bridge import attach
        session = attach(driver, driver.run / 'common_executor', working=ROOT, owner_map=owner_path, motion_map=motion_path, E=E, C=C)
    else:
        from legacy_rooms_bridge import attach
        predicates = {}
        if level == 'R14':
            fn = getattr(driver.level, 'bolt_path_clear', None)
            if not callable(fn):
                raise RuntimeError('Real R14 geometry predicate is missing')
            predicates['R14.bolt_path_clear'] = fn
        session = attach(driver, driver.run / 'common_executor', working=ROOT, owner_map=owner_path, motion_map=motion_path, predicates=predicates, E=E, C=C)
    e = session.esc
    e.cfg.update(protocol='unified_v2', public_id=public_id, max_steps=row['action_cap'], recall_budget=row['recall_cap'], tip_window=row['tip_window'])
    if row.get('room_family') == 'medium_v6':
        e.cam_z = float(driver.pos[2]) - float(e.floor)
        e._cam_z0 = e.cam_z
    for key, sim in getattr(session.backend, 'key_to_sim', {}).items():
        e._display[sim] = driver.label(key)
    live_owners = getattr(session.backend, 'owner_map', None) or owners['levels'].get(level, {})
    for owner in live_owners.get('owners', []):
        if owner['owner_id'] in session.backend.objects:
            e._display[owner['owner_id']] = str(owner.get('public_label') or owner['owner_id'].replace('_', ' '))
    if hasattr(session.backend, 'exit_name'):
        e._display[session.backend.exit_name] = 'exit door'
    if hasattr(session, 'observe'):
        session.observe(driver.pos, driver.yaw, math.degrees(driver.pitch))
    else:
        e.pos = driver.pos.copy()
        e.yaw = float(driver.yaw)
        e._claw_pitch = math.degrees(driver.pitch)
        boxed, _ = C.shoot(e, 'initial')
        e._claw_photos = [boxed]
    from observation_group import attach as attach_observation_group
    attach_observation_group(driver, session)
    from legacy_driver_transport import attach as attach_transport
    attach_transport(driver, session)
    old_click = driver.click
    aliases = live_owners.get('alias_to_owner_part', {})
    if not aliases:
        aliases = {key: {'owner_id': value[0], 'part': value[1]} for key, value in getattr(session.backend, 'part_aliases', {}).items()}

    def click(d, key, kind='read', item=None, purpose='', **fields):
        if kind in ('open', 'close', 'unlock') and key in aliases:
            fields.setdefault('part', int(aliases[key]['part']))
        if item is not None:
            selected = []
            for oid in e.holding:
                sim = e.objs[oid]['sim']
                meta = getattr(session.backend, 'item_metadata', {}).get(sim, {})
                if meta.get('item_key', getattr(session.backend, 'sim_to_key', {}).get(sim)) == item:
                    selected.append(oid)
            if len(selected) == 1:
                oid = selected[0]
                category = str(e.objs[oid]['cat'])
                peers = C._held(e, category)
                if oid in peers:
                    if len(peers) == 1:
                        item = category
                    else:
                        rank = peers.index(oid) + 1
                        words = list(E.ORD_WORDS)
                        candidates = ([words[rank - 1] + ' ' + category] if rank <= len(words) else []) + [str(rank) + ' ' + category, '#' + str(rank) + ' ' + category]
                        matches = [word for word in candidates if C._held(e, word) == [oid]]
                        if not matches:
                            raise RuntimeError('Authored helper cannot express the selected inventory instance through the public old ordinal syntax')
                        item = matches[0]
        return old_click(key, kind, item, purpose, **fields)
    driver.click = types.MethodType(click, driver)
    driver.save('COMMON_EXECUTOR.json', {'public_id': public_id, 'source_id': level, 'executor_file': str(Path(E.__file__).resolve()), 'dispatcher_file': str(Path(C.__file__).resolve()), 'point_method_file': C._at_point.__code__.co_filename, 'movement_method_file': C._move.__code__.co_filename, 'part_map': str(owner_path), 'motion_map': str(motion_path), 'new_driver_action_fallback': False, 'model_calls': 0})
    return session
