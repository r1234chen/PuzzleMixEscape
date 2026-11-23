from pathlib import Path
import copy, hashlib, importlib.util, json, math, sys, types
import numpy as np
from scipy.spatial.transform import Rotation
from legacy_r01_pilot import ObjectView, CpuBackend, quat_from, load_stack
from legacy_rooms_bridge import RoomsBackend, RoomsSession, UnsupportedBinding, path_object, read, put, rule_matches, install_mechanism_hooks
BASE = Path(__file__).resolve().parent.parent
COMMON_NAMES = ('act', 'a_open', 'a_close', 'a_take', 'a_unlock', 'a_use', 'reach_item')
TILES = ('tile_1', 'tile_2', 'tile_3')

class R02Backend(RoomsBackend):

    def __init__(self, driver, owners, motions, predicates=None):
        self.labels = dict(driver.level.LABELS)
        if not hasattr(driver.game, 'LABELS'):
            driver.game.LABELS = self.labels
        super().__init__(driver, 'R02', owners, motions, predicates)
        for key, owner in [('cabinet_body', 'low_drawer_cabinet'), ('light_table', 'central_light_table')]:
            old = self.key_to_sim.pop(key, None)
            if old:
                self.objects.pop(old, None)
                self.sim_to_key.pop(old, None)
            self.key_to_sim[key] = owner
        for key in TILES:
            name = self.key_to_sim.get(key)
            if name is None:
                raise UnsupportedBinding('Missing actual photo panel ' + key)
            self.objects[name].category = 'electric switch'
        if 'battery_slot' not in self.key_to_sim:
            raise UnsupportedBinding('Missing actual battery socket')

    def visible(self, o):
        e = self.escape
        if e is not None and o.name in getattr(e, '_hidden', []):
            return False
        row = self.item_metadata.get(o.name)
        if row and e is not None:
            st = e.items.get(o.name, {})
            if st.get('gone'):
                return False
            owner = row.get('owner_id')
            part = row.get('part')
            if owner and part and (not e.is_open(self.objects[owner], 'j_part_' + str(part))):
                return False
        return super().visible(o)

class R02Session(RoomsSession):

    def __init__(self, backend, out, E, C):
        install_mechanism_hooks(E)
        identities = {n: getattr(E.Escape, n) for n in COMMON_NAMES}
        point_identity = C._at_point
        self.backend = backend
        backend.session = self
        self.driver = backend.driver
        self.game = backend.game
        self.E = E
        self.C = C
        self.extra_images = []
        self.last_call_trace = []
        self.source_mechanism = self.game.act
        self.mechanism_state = {'powered': bool(self.game.powered), 'tiles': list(self.game.tiles), 'puzzle_solved': bool(self.game.puzzle_solved)}
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        cfg = {'name': 'legacy_bridge_R02', 'scene': 'programmatic_R02', 'start': {'xy': list(self.driver.pos[:2]), 'yaw_deg': math.degrees(self.driver.yaw)}, 'max_steps': 150, 'native_devices_visual': False, 'native_use_visual': False, 'items': [], 'part_locks': [], 'doors': [{'name': backend.exit_name, 'key': 'key', 'exit': True}], 'gadgets': []}
        for owner, part in backend.part_bindings:
            row = {'container': owner, 'part': part}
            if owner == 'camera_storage_case':
                row['lock'] = str(self.driver.level.CODE)
            cfg['part_locks'].append(row)
        for name, row in backend.item_metadata.items():
            cfg['items'].append({'id': row['item_key'], 'name': name, 'kind': 'tool', 'text': self.clue_text(row['item_key'])})
        for key in TILES + ('battery_slot',):
            cfg['gadgets'].append({'name': backend.key_to_sim[key], 'type': 'native_mechanism'})
        ctx = {'env': types.SimpleNamespace(scene=types.SimpleNamespace(objects=list(backend.objects.values()), object_registry=lambda k, n: backend.objects.get(n))), 'E': types.SimpleNamespace(quat_from=quat_from), 'pos': list(self.driver.pos), 'shot': backend.capture, 'detect': backend.detect, 'step_sim': backend.step, 'fov_h': lambda: math.pi / 2}
        e = self.esc = E.Escape(ctx, cfg, out)
        backend.escape = e
        for attribute, method in (('_native_photo_metadata_hook', 'photo_metadata'), ('_native_front_mesh_guard', 'front_mesh_guard')):
            hook = getattr(backend, method, None)
            if callable(hook):
                setattr(e, attribute, hook)
        e._native_mechanism_hook = self.mechanism
        e._native_mechanism_targets = {backend.key_to_sim[k] for k in TILES + ('battery_slot',)}
        for i, o in enumerate(backend.objects.values(), 1):
            e.objs[i] = {'id': i, 'sim': o.name, 'cat': o.category, 'center': o.aabb.mean(0).tolist()}
            e.by_sim[o.name] = i
        self.key_to_oid = {k: e.by_sim[name] for k, name in backend.key_to_sim.items()}
        for key, (owner, part) in backend.part_aliases.items():
            self.key_to_oid[key] = e.by_sim[owner]
        for name, o in backend.objects.items():
            if o.joints:
                e._parts[name] = [(jn, 'drawer' if 'Prismatic' in str(j.joint_type) else 'door') for jn, j in o.joints.items()]
                e._closed_box[name] = tuple(o.aabb.copy())
        for name, row in backend.item_metadata.items():
            owner = row.get('owner_id') or name
            part = row.get('part') or 0
            jn = 'j_part_' + str(part) if part else None
            st = {'id': row['item_key'], 'name': name, 'container': owner, 'part': part, 'joint': jn, 'kind': row.get('kind', 'loose'), 'fixed': bool(row.get('fixed')), 'text': self.clue_text(row['item_key']), 'lockd': None, 'unlocked': True, 'taken': False}
            if owner not in backend.objects:
                raise UnsupportedBinding('Unknown item container ' + owner)
            if jn:
                st['rel'] = e._rel(backend.objects[owner].links[jn[2:]], backend.objects[name])
            e.items[name] = st
        e._wallmap = np.zeros((640, 640), bool)
        res = e.GUARD_RES
        e._wallmap[320:320 + int(5.2 / res), 320:320 + int(5.2 / res)] = True
        e._semmap = np.ones((3200, 3200), np.uint8)
        e._roomcats = ['photographic_studio']
        e._door_boxes = backend._door_boxes
        e._window_boxes = {}
        e._fronts.update({'low_drawer_cabinet': np.array([1.0, 0.0]), 'central_light_table': np.array([0.0, -1.0]), 'camera_storage_case': np.array([0.0, -1.0])})
        self.generic_identity = identities
        self.point_identity = point_identity
        assert all((getattr(E.Escape, n) is f for n, f in identities.items()))
        assert C._at_point is point_identity
        self.project()

    def clue_text(self, key):
        for k, date, number in self.driver.level.PHOTOS:
            if k == key:
                return date + '\nFILE ' + number
        if key == 'rotation_note':
            return 'Press a panel to rotate it 90°.'
        return ''

    def project(self):
        e = getattr(self, 'esc', None)
        b = self.backend
        g = self.game
        if e is None:
            return
        saved = []
        for binding in list(b.part_bindings.values()) + [b.door_binding]:
            node = path_object(b.scene, binding['node_access'])
            saved.append((node, list(node['translate'].Get()), list(node['rotate'].Get())))
        for (owner, part), binding in b.part_bindings.items():
            put(g.__dict__, binding['state_path'], bool(e.is_open(b.objects[owner], 'j_part_' + str(part))))
        for key, val in self.mechanism_state.items():
            setattr(g, key, copy.deepcopy(val))
        g.case_unlocked = bool(e.part_locks['camera_storage_case', 1]['unlocked'])
        g.opened['exit'] = bool(e.is_open(b.objects[b.exit_name], 'j_panel'))
        g.exit_unlocked = bool(e.doors[b.exit_name]['unlocked'])
        g.exited = bool(e.success)
        g.holding = [b.sim_to_key[e.objs[i]['sim']] for i in e.holding]
        g.taken = {b.sim_to_key[name] for name, st in e.items.items() if st.get('taken') or st.get('gone') or e.marks.get('took ' + st['id']) is not None}
        for name, row in b.item_metadata.items():
            owner = row.get('owner_id')
            part = row.get('part')
            if owner and part:
                e.items[name]['behind_glass'] = not e.is_open(b.objects[owner], 'j_part_' + str(part))
        state = g.snapshot()
        for (owner, part), binding in b.part_bindings.items():
            rec = e.part_locks[owner, part]
            req = binding['opening_requirements']
            if req.get('status') != 'executable_structured':
                raise UnsupportedBinding('Unvalidated R02 opening gate')
            if not rec.get('lockd'):
                rec['unlocked'] = bool(rule_matches(req['rule'], state, b.predicates))
        b.scene.sync(g)
        for node, t, r in saved:
            b.scene.transform(node, t, r)

    def mechanism(self, kind, name, item_name=None, a=None):
        b = self.backend
        e = self.esc
        g = self.game
        key = b.sim_to_key.get(name)
        item = b.sim_to_key.get(item_name)
        self.driver.current_hit = {'key': key, 'source': 'actual_common_legacy_resolution'}
        if kind == 'press':
            if key not in TILES:
                raise UnsupportedBinding('Unsupported R02 press ' + str(key))
        elif kind == 'use':
            if key != 'battery_slot' or item != 'battery':
                return {'ok': False, 'text': 'You cannot use this item on this object.', 'images': []}
        else:
            raise UnsupportedBinding('Unsupported R02 mechanism action ' + str(kind))
        self.project()
        before = g.snapshot()
        a = {'action': kind, '_hit364': key, '_validated364': True}
        if item is not None:
            a['item'] = b.labels[item]
        result = self.source_mechanism(a)
        if not result.get('ok'):
            self.project()
            return result
        if kind == 'use':
            st = e.items[item_name]
            try:
                e._slot_place(e.gadgets[name], st)
            except Exception as exc:
                self.project()
                raise UnsupportedBinding('Old battery placement failed; no Game fallback') from exc
            st['gone'] = True
            e._hide(item_name)
            e.gadgets[name]['done'] = True
        self.mechanism_state.update(powered=bool(g.powered), tiles=list(g.tiles), puzzle_solved=bool(g.puzzle_solved))
        self.project()
        if hasattr(b.scene, 'animate'):
            b.scene.animate(self.driver, before)
        return result

    def act(self, action):
        self.esc._native_public_kind = action.get('action')
        self.esc.t = int(getattr(self.driver, '_legacy_action_step', int(getattr(self.driver, 'step', 0)) + 1))
        trace = []

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code.co_name in ('engine_act', 'act', '_act_core', '_at_point', '_layer', '_lock_target', 'a_open', 'a_close', 'a_unlock', 'a_take', 'a_use', 'reach_item', '_move', '_body_hits', 'set_joint', '_slot_place'):
                trace.append([frame.f_code.co_name, frame.f_code.co_filename, frame.f_code.co_firstlineno])
        prior = sys.getprofile()
        sys.setprofile(profile)
        try:
            result = self.esc.act(dict(action))
        finally:
            sys.setprofile(prior)
        self.last_call_trace = trace
        self.project()
        self.driver.pos = self.esc.pos.copy()
        self.driver.yaw = float(self.esc.yaw)
        self.driver.pitch = math.radians(getattr(self.esc, '_claw_pitch', 0.0))
        assert all((getattr(self.E.Escape, n) is f for n, f in self.generic_identity.items()))
        assert self.C._at_point is self.point_identity
        return result

def attach(driver, out, working=BASE / 'working', owner_map=BASE / 'OWNER_PART_MAP.json', motion_map=BASE / 'MOTION_BINDINGS.json', predicates=None, E=None, C=None):
    if Path(driver.level.__file__).stem != 'level_R02':
        raise UnsupportedBinding('R02 bridge refuses another room')
    owners = read(owner_map)['levels']['R02']
    motions = read(motion_map)['levels']['R02']
    if hashlib.sha256(Path(driver.level.__file__).read_bytes()).hexdigest() != motions['source_sha256']:
        raise UnsupportedBinding('R02 source differs frozen motion SHA')
    if E is None:
        E, C = load_stack(working)
    if C is None:
        raise UnsupportedBinding('Both actual legacy E and C are required')
    backend = R02Backend(driver, owners, motions, predicates)
    session = R02Session(backend, out, E, C)
    session.native_gate()
    return session

def static_check(owner_map=BASE / 'OWNER_PART_MAP.json', motion_map=BASE / 'MOTION_BINDINGS.json'):
    owners = read(owner_map)['levels']['R02']
    motions = read(motion_map)['levels']['R02']
    expected = {(o['owner_id'], p['part']) for o in owners['owners'] for p in o['parts']}
    actual = {(x['owner_id'], x['part']) for x in motions['bindings']}
    assert expected == actual and len(actual) == 4
    assert {x['target_key'] for x in motions['contents']} == {'battery', 'key', 'photo_1', 'photo_2', 'photo_3', 'photo_4', 'rotation_note'}
    return {'room': 'R02', 'owners': 3, 'parts': 4, 'contents': 7, 'common_methods_overridden': [], 'SDK_or_GPU_started': False, 'native_verified': False}

def cpu_test(working=BASE / 'working', owner_map=BASE / 'OWNER_PART_MAP.json', motion_map=BASE / 'MOTION_BINDINGS.json'):
    import contextlib, tempfile
    from legacy_r01_pilot import PilotSession

    class Op:

        def __init__(self, v):
            self.v = list(v)

        def Get(self):
            return tuple(self.v)

        def Set(self, v):
            self.v = list(map(float, v))

    class FixtureScene:

        def __init__(self, motions):
            self.groups = {}
            self.target_nodes = {}
            boxes = {'low_drawer_cabinet': [[0.07, 3.4, 0], [0.6, 4.4, 0.7]], 'central_light_table': [[2.0, 2.2, 0], [3.3, 3.03, 0.78]], 'camera_storage_case': [[1.2, 4.5, 0.58], [2.1, 5.05, 0.92]], 'room_exit_door': [[0.03, 0.65, 0], [0.12, 1.75, 2.27]]}
            aliases = {'low_drawer_cabinet': 'cabinet_body', 'central_light_table': 'light_table', 'camera_storage_case': 'camera_case'}
            for owner, key in aliases.items():
                n = self.node(key, boxes[owner])
                self.groups[key] = n
                self.target_nodes[key] = n
            self.groups['cabinet_root'] = self.groups['cabinet_body']
            self.door_node = self.node('door_node', boxes['room_exit_door'])
            for row in motions['bindings'] + motions['door_bindings']:
                name = row['node_access']
                owner = row['owner_id']
                node = self.node(name, boxes[owner], row['motion']['closed'] if row['motion']['kind'] == 'translate' else row['pivot_local'], row['motion']['closed'] if row['motion']['kind'] == 'rotate' else [0, 0, 0])
                if name in ('battery_drawer', 'storage_drawer'):
                    node['parent_R'] = Rotation.from_euler('z', 90, degrees=True).as_matrix()
                setattr(self, name, node)
            self.groups['case_lid'] = self.lid
            content = {'battery': [[0.29, 3.84, 0.47], [0.39, 3.96, 0.54]], 'key': [[1.58, 4.79, 0.66], [1.73, 4.91, 0.69]], 'rotation_note': [[2.07, 2.33, 0.81], [2.93, 2.47, 0.82]]}
            for i in range(1, 5):
                x = 2.42 if i % 2 else 2.88
                y = 2.4 if i < 3 else 2.76
                content['photo_' + str(i)] = [[x - 0.16, y - 0.07, 0.53], [x + 0.16, y + 0.07, 0.54]]
            for key, box in content.items():
                self.target_nodes[key] = self.node(key, box)
            for i, x in enumerate([2.12, 2.48, 2.84], 1):
                self.target_nodes['tile_' + str(i)] = self.node('tile_' + str(i), [[x - 0.12, 2.6, 0.82], [x + 0.12, 2.84, 0.85]])
            self.target_nodes['battery_slot'] = self.node('battery_slot', [[3.06, 2.59, 0.82], [3.26, 2.73, 0.89]])
            self.target_nodes['case_lid'] = self.lid

        def node(self, name, box, t=(0, 0, 0), r=(0, 0, 0)):
            t = [0, 0, 0] if t is None else t
            return {'_name': name, 'box': np.array(box, float), 'offset': np.zeros(3), 'base_t': np.array(t, float), 'translate': Op(t), 'rotate': Op(r), 'parent_R': np.eye(3)}

        def transform(self, node, pos=None, rpy=None):
            if pos is not None:
                node['translate'].Set(pos)
            if rpy is not None:
                node['rotate'].Set(rpy)

        def triangles(self, node):
            shift = node['offset'] + node['parent_R'] @ (np.array(node['translate'].Get()) - node['base_t'])
            lo, hi = node['box'] + shift
            return np.array([[x, y, z] for x in [lo[0], hi[0]] for y in [lo[1], hi[1]] for z in [lo[2], hi[2]]])

        def sync(self, g):
            pass

        def animate(self, *a):
            pass

    class FixtureBackend(R02Backend):
        native = False

        def pose(self, o):
            return (self.bounds(o).mean(0), np.array([0.0, 0.0, 0.0, 1.0]))

        def set_pose(self, o, pos, q):
            if pos is not None:
                o.node['offset'] += np.asarray(pos) - self.bounds(o).mean(0)

        def step(self, n=1):
            pass

        def capture(self, *a):
            return CpuBackend.capture(self, *a)

        def detect(self, *a):
            return CpuBackend.detect(self, *a)

        def overlap_sphere(self, *a):
            return CpuBackend.overlap_sphere(self, *a)
    sp = Path(read(motion_map)['levels']['R02']['source_path'])
    sys.path.insert(0, str(working / 'native_runtime'))
    spec = importlib.util.spec_from_file_location('_r02_fixture_level', sp)
    level = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(level)
    motions = read(motion_map)['levels']['R02']
    owners = read(owner_map)['levels']['R02']
    driver = types.SimpleNamespace(level=level, game=level.Game(), scene=FixtureScene(motions), pos=np.array([1.25, 3.9, 1.35]), yaw=math.pi, pitch=0.0, step=0)
    ordinary_calls = []
    original_game_act = driver.game.act

    def mechanism_only(a):
        if not (a.get('action') == 'press' and a.get('_hit364') in TILES or (a.get('action') == 'use' and a.get('_hit364') == 'battery_slot')):
            ordinary_calls.append(dict(a))
            raise AssertionError('Native Game ordinary-action fallback')
        return original_game_act(a)
    driver.game.act = mechanism_only
    backend = FixtureBackend(driver, owners, motions)
    prior = {name: sys.modules.get(name) for name in ['omnigibson', 'omnigibson.utils', 'omnigibson.utils.asset_utils']}
    stub = types.SimpleNamespace(sim=types.SimpleNamespace(is_playing=lambda: False, psqi=types.SimpleNamespace(overlap_sphere=backend.overlap_sphere)))
    sys.modules['omnigibson'] = stub
    sys.modules['omnigibson.utils'] = types.ModuleType('omnigibson.utils')
    assets = types.ModuleType('omnigibson.utils.asset_utils')
    assets.get_dataset_path = lambda *a: (_ for _ in ()).throw(AssertionError('SDK/dataset in CPU fixture'))
    sys.modules['omnigibson.utils.asset_utils'] = assets
    try:
        with tempfile.TemporaryDirectory(prefix='r02_legacy_cpu_') as td:
            E, C = load_stack(working)
            s = R02Session(backend, td, E, C)
            e = s.esc
            checks = []

            def ck(name, value):
                if not value:
                    raise AssertionError(name)
                checks.append(name)
            ck('common legacy methods identical', all((getattr(E.Escape, n) is f for n, f in s.generic_identity.items())))
            ck('point parser unchanged', C._at_point is s.point_identity)
            ck('four old native part joints', len(backend.part_bindings) == 4)
            ck('fixed photographs and paper remain fixed', all((e.items[backend.key_to_sim[k]]['fixed'] for k in ['photo_1', 'photo_2', 'photo_3', 'photo_4', 'rotation_note'])))
            PilotSession.observe(s, [1.25, 3.9, 1.35], math.pi, -45)
            p = PilotSession.point_for(s, 'low_drawer_cabinet')
            ck('old public missing-part rejection', not s.act(dict(action='open', point=p, target='cabinet'))['ok'])
            ck('old public part99 rejection', not s.act(dict(action='open', point=p, target='cabinet', part=99))['ok'])
            opened = s.act(dict(action='open', point=p, target='cabinet', part=1))
            ck('old public upper drawer opens', opened['ok'])
            trace = list(s.last_call_trace)
            ck('old open call frames', all((any((v[0] == n for v in trace)) for n in ['_at_point', 'a_open', '_layer', 'set_joint'])))
            bid = e.by_sim[backend.key_to_sim['battery']]
            ck('old a_take actual battery inventory', e.a_take({'item': bid})['ok'] and bid in e.holding)
            s.project()
            e.pos = np.array([2.65, 1.65, 1.35])
            tid = e.by_sim[backend.key_to_sim['tile_1']]
            ck('unpowered panel rejected after old press reach', not e.a_press({'object': tid})['ok'])
            slot = e.by_sim[backend.key_to_sim['battery_slot']]
            used = e.a_use({'item': bid, 'target': slot})
            ck('old a_use commits battery slot', used['ok'] and bid not in e.holding)
            ck('battery inserted through old slot helper', e.items[backend.key_to_sim['battery']].get('gone') and s.mechanism_state['powered'])
            ck('power alone does not open archive', not e.part_locks['central_light_table', 1]['unlocked'])
            for key, times in [('tile_1', 3), ('tile_2', 1), ('tile_3', 2)]:
                for _ in range(times):
                    ck('old press ' + key, e.a_press({'object': e.by_sim[backend.key_to_sim[key]]})['ok'])
            s.project()
            ck('three panels release archive lock', s.mechanism_state['puzzle_solved'] and e.part_locks['central_light_table', 1]['unlocked'])
            ck('panel solution never autoopens archive', not e.is_open(backend.objects['central_light_table'], 'j_part_1'))
            e.pos = np.array([1.65, 3.75, 1.35])
            case = e.by_sim['camera_storage_case']
            ck('wrong code old a_unlock rejected', not e.a_unlock({'target': case, 'part': 1, 'code': '0000'})['ok'])
            ck('right code old a_unlock accepted', e.a_unlock({'target': case, 'part': 1, 'code': level.CODE})['ok'])
            s.project()
            ck('code projects case flag without autoopen', driver.game.case_unlocked and (not driver.game.opened['camera_case']))
            ck('old case open uses native joint', e.a_open({'object': case, 'part': 1})['ok'])
            s.project()
            kid = e.by_sim[backend.key_to_sim['key']]
            ck('old take actual case key', e.a_take({'item': kid})['ok'] and kid in e.holding)
            s.project()
            e.pos = np.array([0.85, 1.2, 1.35])
            door = e.by_sim[backend.exit_name]
            ck('old use key unlocks room door', e.a_use({'item': kid, 'target': door})['ok'])
            s.project()
            ck('door not autoopened by key', not driver.game.opened['exit'])
            ck('old door open completes R02', e.a_open({'object': door})['ok'])
            s.project()
            ck('legacy joint and victory projection match', driver.game.opened['exit'] and driver.game.exited)
            ck('ordinary Native Game calls never used', not ordinary_calls)
            return dict(room='R02', passed=len(checks), checks=checks, open_call_trace=trace, scope='synthetic transport CPU, actual old E/C references; not native visual acceptance', ordinary_Game_action_fallbacks=ordinary_calls, model_calls=0, SDK_or_GPU_started=False)
    finally:
        for name, old in prior.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
if __name__ == '__main__':
    print(json.dumps(cpu_test() if '--cpu' in sys.argv else static_check(), ensure_ascii=False))
