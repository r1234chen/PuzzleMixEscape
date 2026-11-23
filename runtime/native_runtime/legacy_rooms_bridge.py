from pathlib import Path
import ast, math, re, json, hashlib, types, copy, sys
import numpy as np
from scipy.spatial.transform import Rotation
from legacy_r01_pilot import ObjectView, NativeBackend, PilotSession, load_stack
ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent

class UnsupportedBinding(RuntimeError):
    pass
AUTHORED_CAPABILITIES = {'R07': {'source_sha256': '3ed2133b8ba82738d58ed80172e23e65f028ab29517d256970de25d119996c7b', 'part_use_aliases': ['s3_cover']}, 'R12': {'source_sha256': 'cf5ee49adab4073489ff7a52b2a6a0600d0f594d64a19c48a8f63ea00894a854', 'use_targets': ['s2_lock']}, 'R14': {'source_sha256': 'd87ae2aaf89f179159901234cd66b331657f653982b0afa1d68b83e3af000392', 'part_use_aliases': ['s3_cover'], 'press_targets': ['s2_move_0_down', 's2_move_0_up', 's2_move_1_left', 's2_move_1_right', 's2_move_2_down', 's2_move_2_up']}, 'R19': {'source_sha256': '499e51e3b4dec685517dccf16c06b44f180afb0d2dcff8534d88acca7e6ce05b', 'item_categories': {'s3_tool_0': 'tracing sheet', 's3_tool_1': 'tracing sheet'}}, 'R21': {'source_sha256': '54106c2bda66f7943ffb7b6958f266385f8a033b68403db8c2fbbb1f5d7ea7d8', 'part_use_aliases': ['s2_cover']}}

def read(p):
    return json.loads(Path(p).read_text('utf-8-sig'))

def get(state, path):
    value = state
    for token in path.split('.'):
        if isinstance(value, dict):
            value = value.get(token, value.get(int(token)) if token.isdigit() else None)
        elif isinstance(value, (list, tuple)) and token.isdigit():
            value = value[int(token)]
        else:
            return None
    return value

def put(state, path, value):
    tokens = path.split('.')
    obj = state
    for token in tokens[:-1]:
        if isinstance(obj, dict):
            obj = obj.setdefault(token, {})
        else:
            obj = obj[int(token)]
    if isinstance(obj, dict):
        obj[tokens[-1]] = value
    else:
        obj[int(tokens[-1])] = value

def path_object(scene, path):
    expr = ast.parse(path, mode='eval').body

    def visit(node):
        if isinstance(node, ast.Name):
            return getattr(scene, node.id)
        if isinstance(node, ast.Attribute):
            return getattr(visit(node.value), node.attr)
        if isinstance(node, ast.Subscript):
            return visit(node.value)[visit(node.slice)]
        if isinstance(node, ast.Constant):
            return node.value
        raise UnsupportedBinding('Unsafe node access: ' + path)
    return visit(expr)

def rule_matches(rule, state, predicates=None):
    if 'all' in rule:
        return all((rule_matches(x, state, predicates) for x in rule['all']))
    if 'any' in rule:
        return any((rule_matches(x, state, predicates) for x in rule['any']))
    if 'predicate' in rule:
        fn = (predicates or {}).get(rule['predicate'])
        if fn is None:
            raise UnsupportedBinding('Predicate not installed: ' + rule['predicate'])
        args = [get(state, x['path']) if isinstance(x, dict) and 'path' in x else x for x in rule.get('args', [])]
        return bool(fn(*args))
    if 'path' not in rule:
        raise UnsupportedBinding('Unknown rule: ' + str(rule))
    value = get(state, rule['path'])
    target = rule.get('value', True)
    op = rule.get('op', 'eq')
    if op == 'eq':
        return value == target
    if op == 'contains':
        return target in (value or [])
    if op == 'not_contains':
        return target not in (value or [])
    if op == 'gte':
        return value is not None and value >= target
    raise UnsupportedBinding('Unsupported rule operation: ' + op)

class LinkedLockItem(dict):
    SHARED = {'unlocked', 'lockd', 'power', 'multi', 'derived', 'concat', 'clue_items'}

    def __init__(self, base, record):
        super().__init__(base)
        self.record = record

    def __getitem__(self, key):
        return self.record[key] if key in self.SHARED else super().__getitem__(key)

    def __setitem__(self, key, value):
        if key in self.SHARED:
            self.record[key] = value
        else:
            super().__setitem__(key, value)

    def get(self, key, default=None):
        return self.record.get(key, default) if key in self.SHARED else super().get(key, default)

    def update(self, *a, **k):
        for key, value in dict(*a, **k).items():
            self[key] = value

class MotionJoint:

    def __init__(self, backend, node, binding):
        self.backend = backend
        self.node = node
        self.binding = binding
        m = binding['motion']
        self.kind = m['kind']
        self.joint_type = 'PrismaticJoint' if self.kind == 'translate' else 'RevoluteJoint'
        self.closed = np.array(m['closed'], float)
        self.delta = np.array(m['delta'], float)
        self.length = float(np.linalg.norm(self.delta))
        assert self.length > 1e-09
        self.axis = self.delta / self.length
        self.travel = self.length if self.kind == 'translate' else math.radians(self.length)
        self.coordinate_scale = self.travel / float(m['legacy_coordinate_open']) if self.kind != 'translate' and 'legacy_coordinate_open' in m else 1.0
        self.lower_limit = 0.0
        self.upper_limit = self.travel / 0.9 if self.kind == 'translate' else self.travel / self.coordinate_scale
        self.max_velocity = 0.0

    def get_state(self):
        op = self.node['translate'] if self.kind == 'translate' else self.node['rotate']
        v = np.array(op.Get(), float) - self.closed
        q = float(np.dot(v, self.axis))
        return (np.array([q if self.kind == 'translate' else math.radians(q) / self.coordinate_scale]), np.array([0.0]), None)

    def set_pos(self, q, drive=False):
        amount = float(q) if self.kind == 'translate' else math.degrees(float(q) * self.coordinate_scale)
        v = self.closed + self.axis * amount
        self.backend.scene.transform(self.node, **{'pos': v.tolist()} if self.kind == 'translate' else {'rpy': v.tolist()})

def install_mechanism_hooks(E):
    if getattr(E, '_native_rooms_hook_v1', False):
        return
    old_observe = E.Escape.observe

    def observe(esc, *args, **kwargs):
        result = old_observe(esc, *args, **kwargs)
        hook = getattr(esc, '_native_photo_metadata_hook', None)
        if hook is not None:
            hook(result[0])
        return result
    E.Escape.observe = observe
    old_press = E.Escape.a_press
    old_use = E.Escape._gadget_use_without_visual
    old_reach = E.Escape.reach_item
    old_taken = E.Escape._on_taken
    old_layer = E.Escape._layer
    old_item = E.Escape._item
    old_lock_target = E.Escape._lock_target
    old_press_visual = E.Escape._press_switch_button

    def press(esc, a):
        obj = esc.objs.get(a.get('object'), {})
        name = obj.get('sim')
        category = obj.get('cat')
        capability = name in getattr(esc, '_native_press_capabilities', set())
        if capability:
            obj['cat'] = 'electric switch'
        try:
            result = old_press(esc, a)
        finally:
            if capability:
                obj['cat'] = category
        hook = getattr(esc, '_native_mechanism_hook', None)
        if hook is None or not result.get('ok'):
            return result
        if name not in getattr(esc, '_native_mechanism_targets', set()):
            return result
        return hook('press', name, None, a)

    def gadget_use(esc, g, st, o, tgt):
        result = old_use(esc, g, st, o, tgt)
        hook = getattr(esc, '_native_mechanism_hook', None)
        if hook is None or g.get('type') != 'native_mechanism' or (not result.get('ok')):
            return result
        return hook('use', g['name'], st['name'], {'item': o['id'], 'target': tgt['id']})

    def reach(esc, st):
        result = old_reach(esc, st)
        gate = getattr(esc, '_native_take_gate', None)
        if not result[0] or gate is None or getattr(esc, '_native_public_kind', None) != 'take':
            return result
        return result if gate(st['name']) else (False, 'This object cannot be taken.')

    def taken(esc, st):
        result = old_taken(esc, st)
        hook = getattr(esc, '_native_taken_hook', None)
        if hook is not None:
            hook(st['name'])
        return result

    def layer(esc, a, verb):
        got, error = old_layer(esc, a, verb)
        gate = getattr(esc, '_native_part_gate', None)
        if error is not None or gate is None:
            return (got, error)
        o, so, joint, part = got
        if not gate(so.name, part, verb):
            kind = getattr(esc, '_native_part_gate_failure', None)
            text = kind(so.name, part, verb) if kind is not None else None
            return (None, {'ok': False, 'text': text or 'This object cannot be ' + verb + 'ed.', 'images': []})
        return (got, error)

    def item(esc, oid, verb):
        obj, st, error = old_item(esc, oid, verb)
        reader = getattr(esc, '_native_read_text', None)
        alias = getattr(esc, '_native_item_alias', None)
        if error is None and st is not None and (verb == 'take') and (alias is not None):
            obj, st, error = alias(obj, st, verb)
        if error is None and st is not None and (verb == 'read') and (reader is not None):
            from read_content_policy import visual_only
            if not visual_only(esc, st):
                st['text'] = reader(st['name'])
        return (obj, st, error)

    def lock_target(esc, a):
        rec, name, error = old_lock_target(esc, a)
        gate = getattr(esc, '_native_unlock_gate', None)
        part_use = getattr(esc, '_native_part_use_hook', None)
        if error is None and getattr(esc, '_native_public_kind', None) == 'use' and (part_use is not None):
            intercept_result = part_use(a, rec)
            if intercept_result is not None:
                return (None, None, intercept_result)
        if error is None and gate is not None and (a.get('item') is None) and (not gate(a)):
            return (None, None, {'ok': False, 'text': 'This object cannot be unlocked.', 'images': []})
        return (rec, name, error)

    def press_visual(esc, so):
        if so.name in getattr(esc, '_native_mechanism_targets', set()):
            return None
        return old_press_visual(esc, so)
    E.Escape.a_press = press
    E.Escape._gadget_use_without_visual = gadget_use
    E.Escape.reach_item = reach
    E.Escape._on_taken = taken
    E.Escape._layer = layer
    E.Escape._item = item
    E.Escape._lock_target = lock_target
    E.Escape._press_switch_button = press_visual
    C = sys.modules.get('_escape_claw')
    if C is not None and (not getattr(C, '_native_press_capability_v1', False)):
        old_kind = C._kind_ok

        def kind_ok(esc, obj, kind):
            if obj.get('sim') in getattr(esc, '_native_read_only_data_targets', set()) and kind != 'read':
                return False
            if kind == 'press' and obj.get('sim') in getattr(esc, '_native_press_capabilities', set()):
                return True
            return old_kind(esc, obj, kind)
        C._kind_ok = kind_ok
        C._native_press_capability_v1 = True
    if C is not None and (not getattr(C, '_native_front_mesh_guard_v1', False)):
        old_front = C._front_thing

        def front(esc, photo, px, py, oid):
            result = old_front(esc, photo, px, py, oid)
            candidate = oid if result is None else result[1] if result[0] == 'named' else None
            guard = getattr(esc, '_native_front_mesh_guard', None)
            if candidate is not None and guard is not None and (not guard(esc, C, photo, px, py, candidate)):
                return ('nothing', None, None)
            return result
        C._front_thing = front
        C._native_front_mesh_guard_v1 = True
    E._native_rooms_hook_v1 = True
    E._native_rooms_originals = {'a_press': old_press, 'gadget_use': old_use, 'reach_item': old_reach, 'on_taken': old_taken, 'layer': old_layer, 'item': old_item, 'lock_target': old_lock_target}

class RoomsBackend(NativeBackend):

    def __init__(self, driver, level, owner_level, motion_level, predicates=None):
        self.driver = driver
        self.scene = driver.scene
        self.game = driver.game
        self.level = level
        self.objects = {}
        self.escape = None
        self.query_count = 0
        self.predicates = predicates or {}
        self.session = None
        self.key_to_sim = {}
        self.sim_to_key = {}
        self.part_bindings = {}
        self.part_aliases = {}
        self.item_metadata = {}
        self.owner_map = owner_level
        self.motion_map = motion_level
        self.authored_capabilities = copy.deepcopy(AUTHORED_CAPABILITIES.get(level, {}))
        if self.authored_capabilities:
            actual = hashlib.sha256(Path(driver.level.__file__).read_bytes()).hexdigest()
            if actual != self.authored_capabilities['source_sha256']:
                raise UnsupportedBinding('Authored capability source SHA changed: ' + level)
        grouped = {}
        for b in motion_level['bindings']:
            typed_sha = b.get('post_open_effect_source_sha256') or b.get('gate_failure_source_sha256')
            if typed_sha is not None:
                actual = hashlib.sha256(Path(driver.level.__file__).read_bytes()).hexdigest()
                if typed_sha != actual:
                    raise UnsupportedBinding('Typed gate feedback source SHA changed: ' + level)
            grouped.setdefault(b['owner_id'], []).append(b)
        for owner in owner_level['owners']:
            oid = owner['owner_id']
            rows = grouped.get(oid, [])
            if not rows:
                raise UnsupportedBinding('Owner has no motions: ' + oid)
            nodes = []
            for name in owner.get('geometry_components', []):
                node = getattr(self.scene, 'groups', {}).get(name) or getattr(self.scene, 'target_nodes', {}).get(name)
                if node is not None and node not in nodes:
                    nodes.append(node)
            for binding in rows:
                node = path_object(self.scene, binding['node_access'])
                if not any((node is existing for existing in nodes)):
                    nodes.append(node)
            o = ObjectView(oid, 'cabinet', self, node=nodes[0])
            o.nodes = nodes
            self.objects[oid] = o
            for b in sorted(rows, key=lambda x: x['part']):
                node = path_object(self.scene, b['node_access'])
                joint = 'j_part_' + str(b['part'])
                link = ObjectView(oid + '_part_' + str(b['part']), 'part', self, node=node)
                o.links[joint[2:]] = link
                o.joints[joint] = MotionJoint(self, node, b)
                self.part_bindings[oid, b['part']] = b
                for key in [b['open_key'], b.get('close_key'), next((p.get('unlock_key') for p in owner['parts'] if p['part'] == b['part']), None)] + next((p.get('aliases', []) for p in owner['parts'] if p['part'] == b['part']), []):
                    if key:
                        self.part_aliases[key] = (oid, b['part'])
        doors = motion_level.get('door_bindings', [])
        if len(doors) != 1:
            raise UnsupportedBinding('Exactly one room exit binding is required')
        b = doors[0]
        node = path_object(self.scene, b['node_access'])
        name = b['owner_id']
        o = ObjectView(name, 'door', self, node=node)
        o.links['panel'] = ObjectView(name + '_panel', 'door', self, node=node)
        o.joints['j_panel'] = MotionJoint(self, node, b)
        self.objects[name] = o
        self.door_binding = b
        self.exit_name = name
        self.key_to_sim[b['open_key']] = name
        self.sim_to_key[name] = b['open_key']
        contents = motion_level.get('contents', [])
        for row in contents:
            key = row['target_key']
            node = self.scene.target_nodes.get(key)
            if node is None:
                raise UnsupportedBinding('Content has no actual Scene target: ' + key)
            category = self.authored_capabilities.get('item_categories', {}).get(key, self.game.LABELS.get(key, key))
            name = 'native_item_' + key
            o = ObjectView(name, str(category), self, node=node)
            self.objects[name] = o
            self.key_to_sim[key] = name
            self.sim_to_key[name] = key
            self.item_metadata[name] = row
        self.lock_endpoints = {}
        for owner in owner_level['owners']:
            for part in owner['parts']:
                alias = part.get('unlock_key')
                node = self.scene.target_nodes.get(alias)
                if not alias or node is None:
                    continue
                probe = ObjectView('_terminal_probe', 'code lock', self, node=node)
                lo, hi = self.bounds(probe)
                ol, oh = self.objects[owner['owner_id']].aabb
                if np.all(lo >= ol - 0.04) and np.all(hi <= oh + 0.04):
                    continue
                physical = []
                centre = (lo + hi) / 2
                for name in self.owner_map_ids:
                    a, z = self.objects[name].aabb
                    if np.all(centre >= a - 0.03) and np.all(centre <= z + 0.03):
                        physical.append((float(np.prod(np.maximum(z - a, 0.001))), name))
                container = min(physical)[1] if physical else None
                name = 'native_lock_terminal_' + alias
                self.objects[name] = ObjectView(name, 'code lock', self, node=node)
                self.key_to_sim[alias] = name
                self.sim_to_key[name] = alias
                self.item_metadata[name] = {'item_key': alias, 'target_key': alias, 'owner_id': container, 'part': None, 'kind': 'surface', 'fixed': True, 'take_gate': [], 'container_is_initial_source_not_permanent': False}
                self.lock_endpoints[name] = {'owner_id': owner['owner_id'], 'part': part['part'], 'unlock_key': alias}
        for key, node in self.scene.target_nodes.items():
            if key in self.part_aliases or key in self.key_to_sim:
                continue
            name = 'native_mechanism_' + key
            category = 'electric switch' if 'choice_' in key or 'control_' in key or 'tile_' in key or key.endswith(('_confirm', '_reset', '_play')) or (key in ['s2_setup']) else 'mechanism'
            self.objects[name] = ObjectView(name, category, self, node=node)
            self.key_to_sim[key] = name
            self.sim_to_key[name] = key
        self.gadget_sims = {}
        for key, name in self.key_to_sim.items():
            if key == self.door_binding['open_key']:
                continue
            if re.search('_(choice|control|slot|overlay|tile)_', key) or key.endswith(('_setup', '_tap', '_confirm', '_reset', '_play', '_feed')):
                self.gadget_sims[name] = key
                if re.search('_(choice|control|tile)_', key) or key.endswith(('_confirm', '_reset', '_play')) or (key.endswith('_setup') and (self.game.SPEC['stages'][int(key[1]) - 1].get('setup') or {}).get('item') is None):
                    self.objects[name].category = 'electric switch'
        for key, (owner, part) in self.part_aliases.items():
            if key.endswith(('_confirm', '_reset', '_play')):
                if len(self.objects[owner].joints) != 1:
                    raise UnsupportedBinding('Press alias spans multiple parts: ' + key)
                self.gadget_sims[owner] = key
                self.objects[owner].category = 'electric switch'
            m = re.fullmatch('s([123])_setup', key)
            if m and (self.game.SPEC['stages'][int(m[1]) - 1].get('setup') or {}).get('kind') != 'key':
                if len(self.objects[owner].joints) != 1:
                    raise UnsupportedBinding('Mechanism part alias is ambiguous: ' + key)
                self.gadget_sims[owner] = key
        declared_press = self.authored_capabilities.get('press_targets', [])
        for key in dict.fromkeys(self.authored_capabilities.get('use_targets', []) + declared_press):
            name = self.key_to_sim.get(key)
            if name is None:
                raise UnsupportedBinding('Authored action target has no real registered mesh: ' + key)
            self.gadget_sims[name] = key
            if key in declared_press:
                self.objects[name].category = 'electric switch'
        self._door_boxes = {name: tuple(o.aabb) for name, o in self.objects.items() if o.category == 'door'}

    def bounds(self, o):
        arrays = [self.scene.triangles(n).reshape(-1, 3) for n in getattr(o, 'nodes', [o.node])]
        arrays = [v for v in arrays if v.size]
        if not arrays:
            raise UnsupportedBinding('Object has no actual mesh: ' + o.name)
        points = np.concatenate(arrays)
        return np.array([points.min(0), points.max(0)])

    def visible(self, o):
        if self.escape is not None and o.name in getattr(self.escape, '_hidden', []):
            return False
        if o.name in self.owner_map_ids:
            return True
        key = self.sim_to_key.get(o.name)
        if key is None:
            return True
        return bool(self.scene.visible(key, self.game)) if hasattr(self.scene, 'visible') else key in self.scene.target_nodes

    def refresh_gadget_semantics(self):
        current = {}
        for key, node in self.scene.target_nodes.items():
            current.setdefault(str(node['prim'].GetPath()), []).append(key)
        updates = {}
        for name, old_key in self.gadget_sims.items():
            if name in self.owner_map_ids:
                continue
            node = self.objects[name].node
            keys = current.get(str(node['prim'].GetPath()), [])
            if old_key in keys:
                updates[name] = old_key
            elif len(keys) == 1:
                updates[name] = keys[0]
            elif len(keys) > 1:
                raise UnsupportedBinding('Ambiguous authored target aliases for ' + name)
        changed = {name: key for name, key in updates.items() if self.gadget_sims[name] != key}
        if not changed:
            return False
        mapping = {key: name for key, name in self.key_to_sim.items() if name not in updates}
        for name, key in updates.items():
            if key in mapping and mapping[key] != name:
                raise UnsupportedBinding('Authored target registration collision: ' + key)
            mapping[key] = name
        self.key_to_sim = mapping
        for name, key in updates.items():
            self.gadget_sims[name] = key
            self.sim_to_key[name] = key
        return True

    @property
    def owner_map_ids(self):
        return {x['owner_id'] for x in self.owner_map['owners']}

    def step(self, n=1):
        for _ in range(max(1, int(n))):
            self.driver.og.sim.step()

    def reconcile(self):
        if self.session is not None:
            self.session.project()

    def install_colliders(self):
        from pxr import Usd, UsdGeom, UsdPhysics
        sim = self.driver.og.sim
        if getattr(sim, 'psqi', None) is None:
            raise UnsupportedBinding('Live PhysX service missing; no fallback')
        count = 0
        with sim.editing_usd():
            for prim in Usd.PrimRange(sim.stage.GetPrimAtPath('/World/redesign364')):
                if prim.IsA(UsdGeom.Mesh):
                    UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
                    UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr('convexHull')
                    count += 1
            for (owner, part), b in self.part_bindings.items():
                node = path_object(self.scene, b['node_access'])
                api = UsdPhysics.RigidBodyAPI.Apply(node['prim'])
                api.CreateKinematicEnabledAttr(True)
                api.CreateRigidBodyEnabledAttr(True)
            node = path_object(self.scene, self.door_binding['node_access'])
            api = UsdPhysics.RigidBodyAPI.Apply(node['prim'])
            api.CreateKinematicEnabledAttr(True)
            api.CreateRigidBodyEnabledAttr(True)
        sim.play()
        sim.update_handles()
        self.step(30)
        return count

class RoomsSession:

    def __init__(self, backend, out, E, C):
        self.backend = backend
        backend.session = self
        self.driver = backend.driver
        self.game = backend.game
        self.E = E
        self.C = C
        self.extra_images = []
        self.placements = {}
        self.lock_effects = {}
        self.last_call_trace = []
        install_mechanism_hooks(E)
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        cfg = {'name': 'native_bridge_' + backend.level, 'scene': 'programmatic_' + backend.level, 'start': {'xy': list(self.driver.pos[:2]), 'yaw_deg': math.degrees(self.driver.yaw)}, 'max_steps': 150, 'native_devices_visual': False, 'native_use_visual': False, 'items': [], 'part_locks': [], 'doors': [{'name': backend.exit_name, 'key': 'key', 'exit': True}], 'gadgets': []}
        stages = getattr(self.game, 'SPEC', {}).get('stages', [])
        for (owner, part), b in backend.part_bindings.items():
            original = next((p for o in backend.owner_map['owners'] if o['owner_id'] == owner for p in o['parts'] if p['part'] == part))
            key = original.get('unlock_key')
            entry = {'container': owner, 'part': part}
            effects = []
            if key:
                index = int(key[1]) - 1
                stage = stages[index]
                if stage.get('answer') is None:
                    raise UnsupportedBinding('Code lock has no declared answer: ' + key)
                entry['lock'] = str(stage['answer'])
                effects = ['solved.' + str(index)]
            match = re.fullmatch('s([123])_setup', b['open_key'])
            if match:
                i = int(match[1]) - 1
                setup = stages[i].get('setup') or {}
                if setup.get('kind') == 'key':
                    entry['key'] = 's' + str(i + 1) + '_tool'
                    effects = ['states.' + str(i) + '.setup_unlocked', 'states.' + str(i) + '.setup_used']
            if backend.level == 'R13' and b['open_key'] == 's3_cover':
                entry['key'] = 's3_tool'
                effects = ['states.2.cover_key_used']
            if backend.level == 'R04' and b['open_key'] == 's3_cover':
                entry['key'] = 's2_float_key'
                effects = ['solved.1']
            cfg['part_locks'].append(entry)
            self.lock_effects[owner, part] = effects
        for name, row in backend.item_metadata.items():
            cfg['items'].append({'id': row['item_key'], 'name': name, 'kind': 'tool', 'text': ''})
        for name in backend.gadget_sims:
            cfg['gadgets'].append({'name': name, 'type': 'native_mechanism'})
        from legacy_r01_pilot import quat_from
        ctx = {'env': types.SimpleNamespace(scene=types.SimpleNamespace(objects=list(backend.objects.values()), object_registry=lambda k, n: backend.objects.get(n))), 'E': types.SimpleNamespace(quat_from=quat_from), 'pos': list(self.driver.pos), 'shot': backend.capture, 'detect': backend.detect, 'step_sim': backend.step, 'fov_h': lambda: math.pi / 2}
        self.esc = E.Escape(ctx, cfg, out)
        backend.escape = self.esc
        e = self.esc
        e._native_photo_metadata_hook = backend.photo_metadata
        e._native_front_mesh_guard = backend.front_mesh_guard
        e._native_part_use_hook = self.part_use
        e._native_part_gate_failure = self.part_gate_failure
        e._native_mechanism_hook = self.mechanism
        e._native_mechanism_targets = {g['name'] for g in cfg['gadgets']}
        e._native_take_gate = self.take_gate
        e._native_taken_hook = self.on_taken
        e._native_part_gate = self.part_gate
        e._native_read_text = self.read_text
        e._native_read_kind = self.read_kind
        e._native_unlock_gate = self.unlock_gate
        for i, o in enumerate(backend.objects.values(), 1):
            e.objs[i] = {'id': i, 'sim': o.name, 'cat': o.category, 'center': o.aabb.mean(0).tolist()}
            e.by_sim[o.name] = i
        self.key_to_oid = {k: e.by_sim[v] for k, v in backend.key_to_sim.items()}
        self.oid_to_key = {v: k for k, v in self.key_to_oid.items()}
        for key, (owner, part) in backend.part_aliases.items():
            if backend.key_to_sim.get(key) not in backend.lock_endpoints:
                self.key_to_oid[key] = e.by_sim[owner]
        for owner, o in backend.objects.items():
            if o.joints:
                e._parts[owner] = [(j, 'drawer' if 'Prismatic' in str(v.joint_type) else 'door') for j, v in o.joints.items()]
                e._closed_box[owner] = tuple(o.aabb.copy())
        for name, row in backend.item_metadata.items():
            parent = row.get('owner_id') or name
            part = row.get('part') or 0
            jn = 'j_part_' + str(part) if part else None
            kind = row.get('kind', 'loose')
            st = {'id': row['item_key'], 'name': name, 'container': parent, 'part': part, 'joint': jn, 'kind': kind, 'fixed': bool(row.get('fixed')), 'text': self.clue_text(row['item_key']), 'lockd': None, 'unlocked': True, 'taken': False}
            if parent not in backend.objects:
                raise UnsupportedBinding('Unknown content owner ' + str(parent))
            if jn:
                st['rel'] = e._rel(backend.objects[parent].links[jn[2:]], backend.objects[name])
            if name in backend.lock_endpoints:
                endpoint = backend.lock_endpoints[name]
                st = LinkedLockItem(st, e.part_locks[endpoint['owner_id'], endpoint['part']])
            e.items[name] = st
        e._wallmap = np.zeros((640, 640), bool)
        size = getattr(self.game, 'SPEC', {}).get('size', [6.0, 6.0])
        res = e.GUARD_RES
        e._wallmap[320:320 + int(size[1] / res), 320:320 + int(size[0] / res)] = True
        e._door_boxes = backend._door_boxes
        e._window_boxes = {}
        e._semmap = np.ones((3200, 3200), np.uint8)
        e._roomcats = ['native_room']
        for owner in backend.owner_map_ids:
            e._fronts[owner] = np.array([0.0, -1.0])
        self.generic_identity = {name: getattr(E.Escape, name) for name in ['act', 'a_open', 'a_close', 'a_take', 'a_unlock', 'a_use']}
        self.project()

    def clue_text(self, key):
        match = re.fullmatch('s([123])_clue', key)
        return str(self.game.SPEC['stages'][int(match[1]) - 1].get('clue_text', '')) if match else ''

    def take_gate(self, name):
        row = self.backend.item_metadata[name]
        st = self.esc.items[name]
        if st.get('slot') and row.get('container_is_initial_source_not_permanent'):
            return True
        state = self.game.snapshot()
        return all((rule_matches(x, state, self.backend.predicates) for x in row.get('take_gate', [])))

    def part_gate(self, owner, part, verb):
        binding = self.backend.part_bindings.get((owner, part))
        if binding is None:
            raise UnsupportedBinding('Missing part capability binding')
        req = binding['opening_requirements' if verb == 'open' else 'closing_requirements']
        if req.get('status') != 'executable_structured':
            raise UnsupportedBinding('Part capability rule not validated')
        return rule_matches(req['rule'], self.game.snapshot(), self.backend.predicates)

    def part_gate_failure(self, owner, part, verb):
        if verb != 'open':
            return None
        binding = self.backend.part_bindings.get((owner, part), {})
        if getattr(self.backend, 'level', '') in getattr(self, '_authored_h2_lock_feedback', {}):
            row = self._authored_h2_lock_feedback[self.backend.level]
            rule = row['rules'].get(binding.get('open_key'))
            if rule is None:
                return None
            return None if rule_matches(rule, self.game.snapshot(), self.backend.predicates) else 'This object is locked.'
        if binding.get('gate_failure_kind') != 'locked' or not binding.get('locked_if_release_rule_false'):
            return None
        if rule_matches(binding['lock_release_rule'], self.game.snapshot(), self.backend.predicates):
            return None
        return 'This object is locked.'

    def unlock_gate(self, a):
        obj = self.esc.objs.get(a.get('target'), {})
        owner = obj.get('sim')
        part = a.get('part')
        if owner in self.backend.lock_endpoints:
            endpoint = self.backend.lock_endpoints[owner]
            owner = endpoint['owner_id']
            part = endpoint['part']
        alias = next((p.get('unlock_key') for o in self.backend.owner_map['owners'] if o['owner_id'] == owner for p in o['parts'] if p['part'] == part), None)
        if alias and re.fullmatch('s[123]_lock', alias):
            return bool(self.game.states[int(alias[1]) - 1].get('setup_ready', True))
        return True

    def read_kind(self, name):
        from read_content_policy import node_kind
        obj = self.backend.objects.get(name)
        return node_kind(self.backend.scene, obj.node, include_hidden=bool(self.esc.items.get(name, {}).get('taken'))) if obj is not None else None

    def read_text(self, name):
        key = self.backend.sim_to_key[name]
        result = self.game.act({'action': 'read', '_hit364': key, '_validated364': True})
        return str(result.get('text', '')) if result.get('ok') else ''

    def on_taken(self, name):
        key = self.backend.sim_to_key.get(name, '')
        match = re.fullmatch('s([123])_item_(\\d+)', key)
        if match:
            assignment = self.game.states[int(match[1]) - 1].get('assignment', {})
            item = int(match[2])
            for slot, v in list(assignment.items()):
                if int(v) == item:
                    assignment.pop(slot)

    def project(self):
        e = self.esc
        g = self.game
        b = self.backend
        for owner, part in b.part_bindings:
            rec = e.part_locks[owner, part]
            if rec['unlocked']:
                for path in self.lock_effects[owner, part]:
                    put(g.__dict__, path, True)
        saved = []
        for (owner, part), binding in b.part_bindings.items():
            node = path_object(b.scene, binding['node_access'])
            saved.append((node, list(node['translate'].Get()), list(node['rotate'].Get())))
            opened = bool(e.is_open(b.objects[owner], 'j_part_' + str(part)))
            put(g.__dict__, binding['state_path'], opened)
            if opened:
                for effect in binding.get('post_open_state_effects', []):
                    put(g.__dict__, effect['path'], copy.deepcopy(effect['value']))
            setup_match = re.fullmatch('states\\.(\\d+)\\.setup_open', binding['state_path'])
            if setup_match:
                g.states[int(setup_match[1])]['setup_ready'] = opened
        door_node = path_object(b.scene, b.door_binding['node_access'])
        saved.append((door_node, list(door_node['translate'].Get()), list(door_node['rotate'].Get())))
        g.opened['exit'] = b.exit_name in e.passed_doors
        g.exit_unlocked = e.doors[b.exit_name]['unlocked']
        g.exited = bool(e.success)
        g.holding = [b.sim_to_key[e.objs[i]['sim']] for i in e.holding]
        g.taken = {b.sim_to_key[n] for n, st in e.items.items() if st.get('taken') or e.marks.get('took ' + st['id']) is not None}
        state = g.snapshot()
        for (owner, part), binding in b.part_bindings.items():
            rec = e.part_locks[owner, part]
            req = binding['opening_requirements']
            if req.get('status') != 'executable_structured':
                raise UnsupportedBinding('Unvalidated open gate')
            if not rec.get('lockd') and rule_matches(req['rule'], state, b.predicates):
                rec['unlocked'] = True
        b.scene.sync(g)
        if b.refresh_gadget_semantics():
            self.key_to_oid = {key: e.by_sim[name] for key, name in b.key_to_sim.items()}
            self.oid_to_key = {value: key for key, value in self.key_to_oid.items()}
            for key, (owner, part) in b.part_aliases.items():
                if b.key_to_sim.get(key) not in b.lock_endpoints:
                    self.key_to_oid[key] = e.by_sim[owner]
            for name, key in b.gadget_sims.items():
                label = getattr(b.scene, 'labels', {}).get(key)
                if label:
                    e._display[name] = str(label)
        for node, t, r in saved:
            b.scene.transform(node, t, r)
        if b.native:
            from pxr import Usd, UsdPhysics
            with self.driver.og.sim.editing_usd():
                for name, st in e.items.items():
                    obj = b.objects[name]
                    enabled = not st.get('taken') and (not st.get('gone'))
                    for prim in Usd.PrimRange(obj.node['prim']):
                        if prim.HasAPI(UsdPhysics.CollisionAPI):
                            UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Set(enabled)

    def part_use(self, action, record):
        b = self.backend
        owner = record.get('container')
        part = record.get('part')
        aliases = [key for key in getattr(b, 'authored_capabilities', {}).get('part_use_aliases', []) if b.part_aliases.get(key) == (owner, part)]
        if not aliases:
            return None
        if len(aliases) != 1:
            raise UnsupportedBinding('Ambiguous authored part-use capability')
        item = self.esc.objs.get(action.get('item'), {}).get('sim')
        if item is None:
            return None
        return self.mechanism('use', owner, item, action, authored_key=aliases[0])

    def mechanism(self, kind, name, item_name, a, authored_key=None):
        b = self.backend
        g = self.game
        key = authored_key if authored_key is not None else b.gadget_sims[name]
        self.project()
        before = g.snapshot()
        item = b.sim_to_key.get(item_name)
        internal = {'action': kind, '_hit364': key, '_validated364': True, '_actor_position364': self.esc.pos.tolist()}
        if item is not None:
            internal['item'] = g.LABELS.get(item, item)
        result = g.act(internal)
        result['native_resolved_key_private'] = key
        if not result.get('ok'):
            self.project()
            return result
        after = g.snapshot()
        for (owner, part), binding in b.part_bindings.items():
            old = get(before, binding['state_path'])
            new = get(after, binding['state_path'])
            if old != new:
                req = binding['opening_requirements' if new else 'closing_requirements']
                if not rule_matches(req['rule'], after, b.predicates):
                    raise UnsupportedBinding('Mechanism requested a forbidden part movement')
                self.esc.set_joint(b.objects[owner], 'j_part_' + str(part), bool(new))
        removed = set(before['holding']) - set(g.holding)
        for consumed in removed:
            sim = b.key_to_sim.get(consumed)
            if sim is None:
                raise UnsupportedBinding('Unknown inventory effect ' + consumed)
            st = self.esc.items[sim]
            target = self.esc.gadgets.get(name)
            if target is None:
                if authored_key is None:
                    raise UnsupportedBinding('Consumed tool has no canonical placement target')
                target = {'name': name, 'type': 'native_mechanism'}
            self.esc._slot_place(target, st)
            setup = {}
            m = re.match('s([123])_', key)
            if m:
                setup = g.SPEC['stages'][int(m[1]) - 1].get('setup') or {}
            if setup.get('consume') or '_overlay_' in key or '_slot_' not in key:
                st['gone'] = True
            if authored_key is not None and name not in self.esc.gadgets:
                if not st.get('gone'):
                    raise UnsupportedBinding('Persistent part placement needs a declared native slot')
                st.pop('slot', None)
        self.driver.current_hit = {'key': key, 'source': 'actual_common_legacy_resolution'}
        extra_before = len(getattr(self.driver, 'current_visual_feedback', []))
        self.project()
        if hasattr(b.scene, 'animate'):
            b.scene.animate(self.driver, before)
        self.extra_images.extend(getattr(self.driver, 'current_visual_feedback', [])[extra_before:])
        return result

    def act(self, action):
        e = self.esc
        e._native_public_kind = action.get('action')
        self.extra_images = []
        e.t = int(getattr(self.driver, '_legacy_action_step', self.driver.step + 1))
        result = e.act(dict(action))
        code_alias = None
        if action.get('action') == 'unlock':
            ids = result.get('action_ids') or result.get('action_ids_private') or {}
            oid = ids.get('target')
            part = ids.get('part')
            if oid in e.objs:
                owner = e.objs[oid]['sim']
                if owner in self.backend.lock_endpoints:
                    endpoint = self.backend.lock_endpoints[owner]
                    owner = endpoint['owner_id']
                    part = endpoint['part']
                binding = self.backend.part_bindings.get((owner, part))
                alias = next((p.get('unlock_key') for o in self.backend.owner_map['owners'] if o['owner_id'] == owner for p in o['parts'] if p['part'] == part), None)
                if alias and re.match('s[123]_lock$', alias):
                    self.game.states[int(alias[1]) - 1]['entered_code'] = str(action.get('code', ''))
                    code_alias = alias
        self.project()
        self.driver.pos = e.pos.copy()
        self.driver.yaw = float(e.yaw)
        self.driver.pitch = math.radians(getattr(e, '_claw_pitch', 0.0))
        if code_alias is not None or not result.get('images'):
            boxed, _ = self.C.shoot(e, 'native_code_entry' if code_alias else 'native_current_result')
            e._claw_photos = [boxed]
            result['images'] = [self.C._small(e, boxed)]
        if self.extra_images:
            result['images'] = list(dict.fromkeys(self.extra_images + list(result.get('images') or [])))
            result['native_mechanism_sequence_preserved'] = True
        return result

    def native_gate(self):
        count = self.backend.install_colliders()
        tested = []
        for owner in list(self.backend.owner_map_ids)[:3]:
            obj = self.backend.objects[owner]
            nodes = getattr(obj, 'nodes', [obj.node])
            expected = set()
            samples = []
            for node in nodes:
                path = str(node['prim'].GetPath())
                parts = path.split('/')
                if len(parts) > 3:
                    expected.add(parts[3])
                tri = self.backend.scene.triangles(node)
                if tri.size:
                    centroids = tri.mean(axis=1)
                    centroids = centroids[(centroids[:, 2] > 0.18) & (centroids[:, 2] < 1.45)]
                    for centre in centroids[:3]:
                        samples.append(centre[:2])
            lo, hi = obj.aabb
            samples.insert(0, (lo + hi)[:2] / 2)
            for xy in samples[:4]:
                hits = self.C._body_hits(self.esc, *xy)
                matched = expected.intersection(hits or set())
                tested.append({'owner': owner, 'xy': list(map(float, xy)), 'expected_actual_prim_ancestors': sorted(expected), 'hits': sorted(hits or []), 'matched': sorted(matched)})
                if matched:
                    return {'collision_meshes': count, 'body_probe': tested, 'native_visual_verified': False}
        raise UnsupportedBinding('No PhysX hit on an actual registered owner prim ancestor; cannot use old movement safely')

def attach(driver, out, working=BASE / 'working', owner_map=BASE / 'OWNER_PART_MAP.json', motion_map=BASE / 'MOTION_BINDINGS.json', predicates=None, E=None, C=None):
    if E is None:
        E, C = load_stack(working)
    level = Path(getattr(driver.level, '__file__', '')).stem.replace('level_', '')
    if level in ('R01', 'R02'):
        raise UnsupportedBinding(level + ' uses its dedicated data bridge; not silently adapted as EasyScene')
    owners = read(owner_map)['levels'][level]
    motions = read(motion_map)['levels'][level]
    actual = hashlib.sha256(Path(driver.level.__file__).read_bytes()).hexdigest()
    if actual != motions['source_sha256']:
        raise UnsupportedBinding('Source SHA does not match frozen motion bindings: ' + level)
    predicates = dict(predicates or {})

    def scan(rule):
        if isinstance(rule, dict):
            if 'predicate' in rule:
                name = rule['predicate']
                prefix, _, symbol = name.partition('.')
                if prefix == level and callable(getattr(driver.level, symbol, None)):
                    predicates.setdefault(name, getattr(driver.level, symbol))
            for value in rule.values():
                scan(value)
        elif isinstance(rule, list):
            for value in rule:
                scan(value)
    scan(motions)
    backend = RoomsBackend(driver, level, owners, motions, predicates)
    session = RoomsSession(backend, out, E, C)
    session.native_gate()
    return session

def validate_static(owner_map=BASE / 'OWNER_PART_MAP.json', motion_map=BASE / 'MOTION_BINDINGS.json'):
    owners = read(owner_map)
    motions = read(motion_map)
    rows = []
    for level, data in motions['levels'].items():
        expected = {(o['owner_id'], p['part']) for o in owners['levels'][level]['owners'] for p in o['parts']}
        actual = {(b['owner_id'], b['part']) for b in data['bindings']}
        if actual != expected:
            raise UnsupportedBinding('Owner/part mismatch ' + level)
        for b in data['bindings']:
            if b['opening_requirements'].get('status') != 'executable_structured':
                raise UnsupportedBinding('Unknown gate ' + level)
            ast.parse(b['node_access'], mode='eval')
        rows.append({'level': level, 'parts': len(actual), 'contents': len(data.get('contents', [])), 'source_sha256': data['source_sha256']})
    return {'levels': len(rows), 'parts': sum((x['parts'] for x in rows)), 'contents': sum((x['contents'] for x in rows)), 'rows': rows, 'runtime_installed': False, 'native_verified': False, 'unsupported_explicit': ['R01/R02 require dedicated bridge', 'Any predicate without supplied implementation', 'Missing actual Scene node/content owner or mismatched source SHA']}
if __name__ == '__main__':
    print(json.dumps(validate_static(), ensure_ascii=False))
