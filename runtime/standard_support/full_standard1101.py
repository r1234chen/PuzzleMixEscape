from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, os, sys, time, traceback, types

def load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan', required=True)
    p.add_argument('--level', required=True)
    p.add_argument('--recipe-file')
    p.add_argument('--no-video', action='store_true')
    p.add_argument('--probes', action='store_true')
    p.add_argument('--child', action='store_true')
    a = p.parse_args()
    plan = __import__("episode_plan").read_plan(a.plan)
    root = Path(plan['benchmark_root'])
    sys.path.insert(0, str(root))
    from episode_plan import validate_plan, save, ensure_startup_environment
    validate_plan(plan, a.level, verify_sources=True)
    if plan.get('launch_authorized'):
        raise PermissionError('This harness accepts only explicit unapproved zero-API plans')
    ensure_startup_environment(plan, a.level)
    out = Path(plan['effective_runs'][a.level])
    out.mkdir(parents=True, exist_ok=True)
    receipt = out / 'FULL_STANDARD_RESULT.json'
    if not a.child:
        if receipt.exists() or (out / 'FROZEN_EPISODE_PLAN.json').exists():
            raise FileExistsError('Immutable validation attempt already exists')
        save(out / 'FROZEN_EPISODE_PLAN.json', dict(plan, execution_mode='zero_api_full_standard', source_harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), recipe_sha256=hashlib.sha256(Path(a.recipe_file).read_bytes()).hexdigest() if a.recipe_file else None))
        from native_process import supervise_script
        from resource_gate import ResourceLease
        cmd = [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()), *sys.argv[1:], '--child']
        with ResourceLease(plan, level=a.level):
            return supervise_script(cmd, receipt, ledger_path=out / 'FULL_STANDARD_HOST_EXIT.json')
    import native_model_episode as N

    def standard_loop(d, session, plan, client=None, **kw):
        if client is not None or not kw.get('smoke'):
            raise PermissionError('No model mode is permitted in the validation recipe')
        ledger = []
        probes = []
        active = {'probe': None}
        old = d.execute
        oldclick = d.click
        error = None
        initial = session.packet()
        N.explicit_contents(initial)
        N.initial_photo_equivalence(d, initial, out)
        ledger.append({'turn': 0, 'counted': False, 'action': {'action': 'start'}, 'result': {'ok': True, 'text': '', 'images': initial['images']}, 'pos': d.pos.tolist()})

        def execute(driver, action, purpose='', allow_failure=False):
            action = copy.deepcopy(action)
            if action.get('action') in ('open', 'close', 'unlock') and 'part' not in action:
                b = driver.shared_legacy_session.backend
                aliases = getattr(b, 'part_aliases', {})
                matches = []
                for key, binding in aliases.items():
                    try:
                        label = driver.label(key)
                    except (KeyError, AttributeError):
                        continue
                    if label == action.get('target'):
                        matches.append((key, binding))
                parts = {int(v[1]['part'] if isinstance(v[1], dict) else v[1][1]) for v in matches}
                if len(parts) == 1:
                    action['part'] = parts.pop()
                    save(out / 'ORACLE_PART_SELECTION_LAST.json', {'target': action['target'], 'part': action['part'], 'matching_authored_aliases': [x[0] for x in matches], 'oracle_only': True, 'model_mode_unchanged': True})
            if a.probes and (not active['probe']) and (action.get('action') == 'unlock') and ('unlock' not in done):
                done.add('unlock')
                fields = {k: v for k, v in action.items() if k in ('point', 'target', 'part', 'photo')}
                probe_action('locked_open', dict(fields, action='open'))
                code = str(action.get('code', ''))
                wrong = ('0' if not code or code[0] != '0' else '1') + code[1:]
                probe_action('wrong_code', dict(action, code=wrong))
            before_packet = session.packet()
            N.explicit_contents(before_packet)
            start = time.time()
            before = copy.deepcopy(driver.game.snapshot())
            pose = {'position': driver.pos.tolist(), 'yaw': driver.yaw, 'pitch': driver.pitch}
            exception = None
            result = None
            try:
                prior_dispatch = driver.execute
                driver.execute = old
                try:
                    after_packet = session.execute(action)
                finally:
                    driver.execute = prior_dispatch
                result = copy.deepcopy(driver.current_result)
                if not result.get('ok') and (not allow_failure):
                    raise RuntimeError('Standard action rejected by common executor: ' + json.dumps({'action': action, 'result': result}, ensure_ascii=False))
                if action.get('action') in ('walk', 'side_step', 'step_back') and abs(float(result.get('moved', action['distance'])) - float(action['distance'])) > 0.025 and (not active['probe']):
                    raise RuntimeError('Authored route was blocked; stop rather than cascade stale coordinates')
                return result
            except BaseException as exc:
                exception = type(exc).__name__ + ': ' + str(exc)
                raise
            finally:
                row = copy.deepcopy(driver.rows[-1]) if driver.rows and driver.rows[-1]['step'] == driver.step else None
                result = result or (row or {}).get('result') or {'ok': False, 'text': '', 'tool_error': exception}
                event = {'turn': driver.step, 'counted': True, 'action': copy.deepcopy(action), 'result': copy.deepcopy(result), 'purpose': purpose, 'probe': active['probe'], 'before': before, 'after': copy.deepcopy(driver.game.snapshot()), 'pose_before': pose, 'pos': driver.pos.tolist(), 'yaw_deg': __import__('math').degrees(driver.yaw), 'seconds': time.time() - start, 'exception': exception, 'common_action_only': bool(row and row.get('common_action_only')), 'model_input_contents': before_packet.get('model_input_contents', []), 'decision_packet': before_packet, 'after_packet': session.packet() if row else None}
                ledger.append(event)
                save(out / 'PUBLIC_ACTION_TRACE.json', ledger)
                save(out / 'FULL_STANDARD_LIVE.json', {'phase': 'negative_probe' if active['probe'] else 'authored_standard', 'level': a.level, 'turn': driver.step, 'action': action, 'result': result, 'pid': os.getpid(), 'heartbeat': time.time(), 'api_calls': 0})
                if a.probes and (not active['probe']) and result.get('ok') and (action.get('action') == 'read') and ('fixed_take' not in done):
                    e = driver.shared_legacy_session.esc
                    ids = result.get('action_ids') or {}
                    oid = ids.get('item')
                    sim = e.objs.get(oid, {}).get('sim')
                    st = e.items.get(sim, {})
                    if st.get('fixed'):
                        done.add('fixed_take')
                        probe_action('fixed_object_take', dict(action, action='take'))
        d.execute = types.MethodType(execute, d)
        import oracle560
        original_route = oracle560.plan_route

        def public_turn_actions(delta):
            import math
            degrees = int(round(math.degrees(delta)))
            if not degrees:
                return []
            way = 'left' if degrees > 0 else 'right'
            other = 'right' if degrees > 0 else 'left'
            amount = abs(degrees)
            if amount < 10:
                return [{'action': 'turn', 'direction': way, 'degrees': amount + 10}, {'action': 'turn', 'direction': other, 'degrees': 10}]
            turns = []
            while amount > 120:
                turns.append({'action': 'turn', 'direction': way, 'degrees': 110 if amount - 120 < 10 else 120})
                amount -= turns[-1]['degrees']
            if amount:
                turns.append({'action': 'turn', 'direction': way, 'degrees': amount})
            return turns
        oracle560._turn_actions = public_turn_actions

        def authoritative_route(start, dest, blocked, yaw=0.0):
            e = d.shared_legacy_session.esc
            C = d.shared_legacy_session.C
            E = d.shared_legacy_session.E
            start_hits = C._body_hits(e, float(start[0]), float(start[1])) or set()
            cache = {}
            shrink = {}
            region = e.region_of(*start)
            for name in start_hits:
                for radius in (0.15, 0.1, 0.05, 0.02):
                    hit = C._body_hits(e, float(start[0]), float(start[1]), radius)
                    if hit is not None and name not in hit:
                        shrink[name] = radius
                        break

            def query(x, y):
                key = (round(float(x), 5), round(float(y), 5))
                if key not in cache:
                    if __import__('math').dist([x, y], start) < 1e-05:
                        cache[key] = False
                        return False
                    hits = C._body_hits(e, float(x), float(y))
                    collision = bool(e._cell_blocked(x, y, E.PATH_R)) if hits is None else bool(hits - start_hits)
                    if hits is not None:
                        for radius in sorted(set(shrink.values())):
                            thinner = C._body_hits(e, float(x), float(y), radius) or set()
                            collision = collision or any((shrink.get(name) == radius for name in thinner))
                    outside = e.cfg.get('outside_rooms') or ['garden']
                    cache[key] = bool(e.region_of(x, y) == 0 or e.region_of(x, y) != region or e.room_name(x, y) in outside or collision)
                return cache[key]
            import math
            requested = list(dest)
            dest = [float(start[k]) + round((float(dest[k]) - float(start[k])) / 0.25) * 0.25 for k in range(2)]
            candidates = [list(dest)]
            if query(*dest):
                offsets = [(dx, dy) for dx in (-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75) for dy in (-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75) if dx or dy]
                offsets.sort(key=lambda q: (math.hypot(*q), math.dist(start, [dest[0] + q[0], dest[1] + q[1]])))
                candidates = [[dest[0] + dx, dest[1] + dy] for dx, dy in offsets if not query(dest[0] + dx, dest[1] + dy)]
            failure = []
            for selected in candidates:
                try:
                    result = original_route([0.0, 0.0], [selected[0] - start[0], selected[1] - start[1]], lambda x, y: query(start[0] + x, start[1] + y), yaw=yaw)
                    break
                except (ValueError, RuntimeError) as exc:
                    failure.append({'point': selected, 'error': str(exc)})
            else:
                raise RuntimeError('No physically clear public route endpoint near authored view: ' + json.dumps({'requested': requested, 'failures': failure}))
            expanded = []
            for action in result:
                if action['action'] in ('side_step', 'step_back') and action['distance'] > 0.5:
                    remain = action['distance']
                    while remain > 1e-05:
                        piece = min(0.5, remain)
                        expanded.append(dict(action, distance=piece))
                        remain -= piece
                else:
                    expanded.append(action)
            result = expanded
            save(out / 'AUTHORITATIVE_ROUTE_LAST.json', {'start': list(start), 'requested_destination': requested, 'selected_clear_destination': list(selected), 'goal_error_m': math.dist(requested, selected), 'grid_origin': list(start), 'no_pose_snapping': True, 'body_query_samples': len(cache), 'public_actions': result, 'no_position_write': True, 'oracle_only': True, 'scene_blocked_heuristic_ignored': True, 'collision_contract': 'Original C._body_hits/start-contact shrink, region, outside, fallback cell; actual public movement unchanged'})
            return result
        oracle560.plan_route = authoritative_route

        def probe(label, key, kind, **fields):
            active['probe'] = label
            try:
                before = copy.deepcopy(d.game.snapshot())
                result = oldclick(key, kind, **fields)
                probes.append({'name': label, 'action': kind, 'accepted': bool(result.get('ok')), 'feedback': result.get('text', ''), 'unchanged_game': before == d.game.snapshot(), 'step': d.step})
            except RuntimeError as exc:
                if d.rows and (not d.rows[-1]['result'].get('ok')) and (not d.rows[-1]['result'].get('tool_error')):
                    probes.append({'name': label, 'action': kind, 'accepted': False, 'feedback': d.rows[-1]['result'].get('text', ''), 'step': d.step})
                else:
                    raise
            finally:
                active['probe'] = None
                save(out / 'NEGATIVE_PROBES.json', probes)
        done = set()

        def probe_action(label, action):
            active['probe'] = label
            try:
                before = copy.deepcopy(d.game.snapshot())
                result = d.execute(action, 'Explicit public failure probe', allow_failure=True)
                probes.append({'name': label, 'action': copy.deepcopy(action), 'accepted': bool(result.get('ok')), 'feedback': result.get('text', ''), 'unchanged_game': before == d.game.snapshot(), 'step': d.step, 'expected_accepted': False, 'expected_failure_observed': not bool(result.get('ok')) and bool(result.get('text'))})
                if result.get('ok'):
                    raise RuntimeError('Failure probe unexpectedly succeeded: ' + label)
                if result.get('tool_error'):
                    raise RuntimeError('Native tool error during negative probe')
            finally:
                active['probe'] = None
                save(out / 'NEGATIVE_PROBES.json', probes)

        def click(driver, key, kind='read', item=None, purpose='', **fields):
            return oldclick(key, kind, item, purpose, **fields)
        d.click = types.MethodType(click, d)
        terminal = {}
        try:
            if a.recipe_file:
                recipe = load(Path(a.recipe_file), '_full_public_recipe')
                fn = recipe.run
            else:
                fn = d.level.standard
            fn(d)
        except BaseException as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            terminal['traceback'] = traceback.format_exc()
        finally:
            common = d.shared_legacy_session
            e = common.esc
            b = common.backend
            name = getattr(b, 'exit_name', 'exit')
            obj = getattr(b, 'objects', {}).get(name)
            joints = []
            if obj is not None:
                for j, joint in obj.joints.items():
                    value = joint.get_state()[0]
                    position = [float(x) for x in __import__('numpy').asarray(value).ravel()]
                    joints.append({'name': j, 'position': position, 'open_by_original_E': bool(e.is_open(obj, j))})
            actual_open = bool(name in e.passed_doors and any((j['open_by_original_E'] for j in joints)))
            terminal.update(public_id=a.level, passed=error is None and bool(e.success) and actual_open, actual_Escape_success=bool(e.success), exit_name=name, exit_passed=name in e.passed_doors, actual_exit_joint_open=actual_open, exit_joint_states=joints, game_state=copy.deepcopy(d.game.snapshot()), actions=d.step, public_actions_only=all((x.get('common_action_only') for x in ledger[1:])), model_calls=0, model_calls_authorized=False, positive_chain_complete=error is None, negative_probes=probes, negative_coverage_complete=False, negative_coverage={name: any((x.get('name') == name and x.get('expected_failure_observed') for x in probes)) for name in ('locked_open', 'wrong_code', 'fixed_object_take', 'wrong_item', 'too_far', 'close_reopen')}, error=error, source_sha256=hashlib.sha256(Path(d.level.__file__).read_bytes()).hexdigest(), harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), images=list(d.current_observation_images), known_answer_oracle=True, not_model_evaluation=True)
            terminal['model_input_private_key_absent'] = all(('native_resolved_key_private' not in json.dumps(x.get('model_input_contents', []), ensure_ascii=False) for x in ledger))
            terminal['passed'] = terminal['passed'] and terminal['public_actions_only'] and terminal['model_input_private_key_absent'] and all((x.get('expected_failure_observed') for x in probes))
            terminal['negative_coverage_complete'] = all(terminal['negative_coverage'].values())
            save(receipt, terminal)
            save(out / 'PUBLIC_ACTION_TRACE.json', ledger)
        if error:
            raise RuntimeError(error)
        if not terminal['passed']:
            raise RuntimeError('Authored standard did not open the actual original Escape exit door')
        return (ledger, session.packet())
    N.run_loop = standard_loop
    return N.run(plan, a.level, smoke=True, no_video=a.no_video)
if __name__ == '__main__':
    raise SystemExit(main())
