from pathlib import Path
import copy, hashlib, json, math, types, sys, re
import numpy as np
from legacy_rooms_bridge import RoomsBackend, RoomsSession, ObjectView, MotionJoint, UnsupportedBinding, install_mechanism_hooks, LinkedLockItem
from legacy_r01_pilot import quat_from, load_stack
BASE = Path(__file__).resolve().parent.parent

def _path(node):
    return str(node['prim'].GetPath())
PUBLIC_CATEGORY_FIXTURES = {'R31': {'source_sha256': 'f2e383d98d3f2e5c82338f239f490792462d69c009d10d9aab71b3cfebdff327', 'items': {'film_a': 'numeral film', 'film_b': 'numeral film'}}, 'R43': {'source_sha256': '541a2560e6b66e5103eb4042a075d00e2dfa61cf396f0be78647b883c6ff7d5c', 'items': {'ta': 'route tile', 'tb': 'route tile', 'tc': 'route tile', 'td': 'route tile', **{'slot' + str(i): 'route slot' for i in range(4)}}, 'dual_press_inventory': ['ta', 'tb', 'tc', 'td'], 'non_press_receivers': ['slot' + str(i) for i in range(4)], 'non_item_receivers': ['slot' + str(i) for i in range(4)]}, 'R44': {'source_sha256': '31b27b340a4755fa7f8802f8d58f0347b0c24d53dec560a070bfde399a99b6f5', 'items': {'seat' + str(i): 'sample seat' for i in range(4)}, 'non_press_receivers': ['seat' + str(i) for i in range(4)], 'non_item_receivers': ['seat' + str(i) for i in range(4)]}}

def public_label(scene, key):
    fixture = PUBLIC_CATEGORY_FIXTURES.get(getattr(scene, '_h2_source_id', None), {})
    if fixture.get('source_sha256') == getattr(scene, '_h2_source_sha256', None) and key in fixture.get('items', {}):
        return fixture['items'][key]
    explicit = getattr(scene, '_h2_explicit_labels', {})
    raw = str(explicit.get(key, scene.labels.get(key, str(key).replace('_', ' '))))
    if key in explicit:
        return raw.split(':', 1)[0].strip()
    if re.fullmatch('\\d+-unit block', raw.strip(), re.I):
        return 'weight block'
    if 'figurine' in raw.lower():
        return 'figurine'
    short = raw.split(':', 1)[0].split(' with ', 1)[0]
    short = re.sub('\\s*\\([^)]*\\)', '', short).strip()
    if ':' in raw:
        short = re.sub('\\s+[A-Z]$', '', short).strip()
    return short or 'object'

def _record_printed_text():
    from PIL import ImageDraw
    original = ImageDraw.ImageDraw.text
    if getattr(original, '_h2_print_metadata', False):
        return

    def text(draw, xy, value, *args, **kwargs):
        depth = getattr(draw, '_h2_print_depth', 0)
        draw._h2_print_depth = depth + 1
        try:
            result = original(draw, xy, value, *args, **kwargs)
        finally:
            draw._h2_print_depth = depth
        if depth == 0 and str(value).strip():
            image = draw._image
            rows = getattr(image, '_h2_printed_rows', [])
            rows.append(str(value))
            image._h2_printed_rows = rows
        return result
    text._h2_print_metadata = True
    ImageDraw.ImageDraw.text = text
    from PIL import Image
    original_rotate = Image.Image.rotate
    original_resize = Image.Image.resize

    def rotate(image, angle, *args, **kwargs):
        result = original_rotate(image, angle, *args, **kwargs)
        expand = kwargs.get('expand', args[1] if len(args) > 1 else False)
        full = float(angle) % 180 == 0 or (float(angle) % 90 == 0 and (expand or image.width == image.height))
        if full and hasattr(image, '_h2_printed_rows'):
            result._h2_printed_rows = list(image._h2_printed_rows)
        return result

    def resize(image, *args, **kwargs):
        result = original_resize(image, *args, **kwargs)
        if hasattr(image, '_h2_printed_rows'):
            result._h2_printed_rows = list(image._h2_printed_rows)
        return result
    Image.Image.rotate = rotate
    Image.Image.resize = resize

def _node_visible(scene, node):
    if not getattr(scene, 'shown', {}).get(id(node), True):
        return False
    if getattr(scene, '_h2_cpu_fixture', False):
        return bool(node.get('fixture_visible', True))
    from pxr import UsdGeom
    return str(UsdGeom.Imageable(node['prim']).ComputeVisibility()) != 'invisible'

def _read_surfaces(scene):
    screen_paths = {_path(n) for slot in getattr(scene, 'screens', {}).values() for n in slot.get('faces', {}).values()}
    rows = {k: v for k, v in scene._h2_picture_prints.items() if _path(v['node']) not in screen_paths and v['text']}
    rows.update(scene._h2_screen_prints)
    return rows

def _read_target_rows(scene, node, key):
    path = _path(node)
    rows = _read_surfaces(scene)
    exact = [r for r in rows.values() if _path(r['node']) == path]
    if exact:
        return exact
    label = public_label(scene, key).lower()
    words = (str(key) + ' ' + label).lower()
    if not re.search('paper|card|letter|envelope|booklet|photo|plan|sheet|display|readout|screen', words):
        return []
    if re.search('cabinet|drawer|box|shelf|case|desk|bench|table|socket', words):
        return []
    return [r for r in rows.values() if _path(r['node']).startswith(path + '/')]

def _add_read_surfaces(backend):
    scene = backend.scene
    backend.read_surfaces = {}
    for surface_key, row in _read_surfaces(scene).items():
        path = _path(row['node'])
        enclosing = [(len(_path(n)), k, n) for k, n in scene.target_nodes.items() if path == _path(n) or path.startswith(_path(n) + '/')]
        if enclosing:
            _, key, node = max(enclosing, key=lambda v: v[0])
            if _read_target_rows(scene, node, key):
                continue
            if key in backend.key_to_sim and backend.key_to_sim[key] in backend.gadget_sims:
                continue
        name = 'h2_printed_' + hashlib.sha256(surface_key.encode()).hexdigest()[:14]
        label = 'screen' if surface_key.startswith('screen:') else 'paper'
        obj = ObjectView(name, label, backend, node=row['node'])
        backend.objects[name] = obj
        key = '__printed_' + name.rsplit('_', 1)[1]
        if not hasattr(scene, '_h2_explicit_labels'):
            scene._h2_explicit_labels = {}
        scene._h2_explicit_labels[key] = label
        backend.key_to_sim[key] = name
        backend.sim_to_key[name] = key
        backend.read_surfaces[name] = surface_key
        backend.item_metadata[name] = {'item_key': key, 'target_key': key, 'owner_id': None, 'part': None, 'kind': 'loose', 'fixed': True, 'take_gate': [], 'read_only_label': label}

def _refresh_read_surfaces(backend):
    rows = _read_surfaces(backend.scene)
    for name, key in backend.read_surfaces.items():
        row = rows.get(key)
        if row is not None:
            backend.objects[name].node = row['node']

def instrument_scene(scene):
    from read_content_policy import instrument_scene as install_read_policy
    install_read_policy(scene)
    if getattr(scene, '_h2_instrumented', False):
        return scene
    scene._h2_instrumented = True
    _record_printed_text()
    scene._h2_picture_prints = {}
    scene._h2_screen_prints = {}
    scene._h2_nodes = {}
    scene._h2_parent = {}
    scene._h2_groups = {}
    scene._h2_named_groups = {}
    scene._h2_shapes = {}
    scene._observation_nodes = {}
    scene._h2_explicit_labels = {}
    original_reg = scene.reg

    def reg(sc, key, node, label=None):
        result = original_reg(key, node, label)
        if label is not None:
            sc._h2_explicit_labels[str(key)] = str(label)
        return result
    scene.reg = types.MethodType(reg, scene)
    scene.label_for = types.MethodType(lambda sc, key: public_label(sc, key), scene)
    original_group = scene.group

    def group(sc, key, *args, **kwargs):
        node = original_group(key, *args, **kwargs)
        parent = kwargs.get('parent', args[1] if len(args) > 1 else None)
        sc._h2_groups[_path(node)] = node
        sc._h2_named_groups[str(key)] = node
        sc._h2_parent[_path(node)] = parent
        return node
    scene.group = types.MethodType(group, scene)
    for method in ['box', 'cylinder', 'sphere', 'plane']:
        if not hasattr(scene, method):
            continue
        primitive = getattr(scene, method)

        def shape(sc, key, *args, _primitive=primitive, _method=method, **kwargs):
            node = _primitive(key, *args, **kwargs)
            if isinstance(node, dict) and 'prim' in node:
                sc._h2_shapes[_path(node)] = node
                if _method == 'plane' or str(key) in {'gear_board'}:
                    sc._observation_nodes[str(key)] = node
            return node
        setattr(scene, method, types.MethodType(shape, scene))
    for method in ['picture', 'screen', 'outline']:
        if not hasattr(scene, method):
            continue
        original = getattr(scene, method)

        def observe(sc, key, *args, _original=original, _method=method, **kwargs):
            node = _original(key, *args, **kwargs)
            if isinstance(node, dict) and 'prim' in node:
                sc._observation_nodes[str(key)] = node
                image = args[0] if args else kwargs.get('im')
                printed = '\n'.join(getattr(image, '_h2_printed_rows', [])).strip()
                if _method in ('picture', 'screen'):
                    table = sc._h2_screen_prints if _method == 'screen' else sc._h2_picture_prints
                    slot = 'screen:' + str(key) if _method == 'screen' else 'picture:' + _path(node)
                    from read_content_policy import image_kind
                    table[slot] = {'node': node, 'text': printed, 'read_content_kind': image_kind(image)}
            return node
        setattr(scene, method, types.MethodType(observe, scene))

    def observation_candidates(sc, game, keys=None):
        requested = set(keys) if keys is not None else set(sc._observation_nodes)
        nodes = {k: v for k, v in sc._observation_nodes.items() if k in requested and k not in sc.target_nodes}
        for key in requested:
            if key not in nodes and key not in sc.target_nodes and (key in sc._h2_named_groups):
                nodes[key] = sc._h2_named_groups[key]
        if not nodes:
            return []
        view = copy.copy(sc)
        view.target_nodes = dict(sc.target_nodes)
        view.target_nodes.update(nodes)
        return type(sc).base_candidates(view, list(nodes))
    scene.observation_candidates = types.MethodType(observation_candidates, scene)
    return scene

def _snapshot_to_game(game, snapshot):
    game.s = copy.deepcopy(snapshot.get('state', {}))
    game.solved = list(snapshot.get('solved', [False] * 3))
    game.opened = copy.deepcopy(snapshot.get('opened', {'exit': False}))
    game.holding = list(snapshot.get('holding', []))
    game.taken = set(snapshot.get('taken', []))
    game.possessions = copy.deepcopy(snapshot.get('possessions', {}))
    game.exit_unlocked = bool(snapshot.get('exit_unlocked'))
    game.exited = bool(snapshot.get('exited'))

def authored_proposal(game, key, verb, item=None, position=None):
    probe = object.__new__(type(game))
    probe.__dict__ = {k: copy.deepcopy(v) for k, v in game.__dict__.items() if not callable(v)}
    a = {'action': verb, '_hit364': key, '_validated364': True}
    if item is not None:
        a['item'] = item
    if position is not None:
        a['_actor_position364'] = list(map(float, position))
    result = type(probe).act(probe, a)
    return (dict(result), probe.snapshot())

def column_order(rows):
    if not rows:
        return []
    widths = [max(0.02, float(r.get('local_width', 0.2))) for r in rows]
    tolerance = max(0.025, min(0.15, float(np.median(widths)) * 0.24))
    columns = []
    for row in sorted(rows, key=lambda r: (r['local_x'], -r['local_z'], r['motion_key'])):
        candidates = [(abs(row['local_x'] - c['centre']), i) for i, c in enumerate(columns) if abs(row['local_x'] - c['centre']) <= tolerance]
        if candidates:
            _, index = min(candidates)
            columns[index]['rows'].append(row)
            columns[index]['centre'] = float(np.mean([v['local_x'] for v in columns[index]['rows']]))
        else:
            columns.append({'centre': float(row['local_x']), 'rows': [row]})
    return [r for c in sorted(columns, key=lambda c: c['centre']) for r in sorted(c['rows'], key=lambda r: (-r['local_z'], r['local_x'], r['motion_key']))]

def _local_part_geometry(scene, node, parent):
    if getattr(scene, '_h2_cpu_fixture', False):
        points = np.asarray(scene.local_geometry(node, parent), float).reshape(-1, 3)
    else:
        points = np.asarray(scene.triangles(node), float).reshape(-1, 3)
        inverse = scene.G.XformCache().GetLocalToWorldTransform(parent['prim']).GetInverse()
        points = np.array([inverse.Transform(scene.F.Vec3d(*map(float, p))) for p in points], float)
    if not points.size or not np.isfinite(points).all():
        raise UnsupportedBinding('Part lacks finite owner-local physical geometry')
    low, high = (points.min(0), points.max(0))
    return ((low + high) / 2, high - low)
CUSTOM_PUBLIC_PARTS = {'R24': {'chest_lid': [-100.0, 0.0, 0.0]}, 'R25': {'canister_lid': [0.0, -100.0, 0.0], 'card_box': [-100.0, 0.0, 0.0]}, 'R29': {'case_lid': [-100.0, 0.0, 0.0]}, 'R36': {'chest_lid': [-100.0, 0.0, 0.0], 'cover': [-100.0, 0.0, 0.0]}, 'R38': {'board_cover': [0.0, 0.0, -100.0]}, 'R44': {'table_cover': [0.0, 0.0, -100.0]}}

def _physical(scene, source_id=None):
    if not getattr(scene, '_h2_instrumented', False):
        raise UnsupportedBinding('instrument_scene must run before Scene.build')
    parts = []
    for key, (node, closed, opened) in scene.hinges.items():
        parts.append((key, node, {'kind': 'rotate', 'closed': [0.0, 0.0, float(closed)], 'delta': [0.0, 0.0, float(opened - closed)]}))
    for key, (node, c, pull) in scene.slides.items():
        parts.append((key, node, {'kind': 'translate', 'closed': list(map(float, c)), 'delta': [0.0, -float(pull), 0.0]}))
    for key, delta in CUSTOM_PUBLIC_PARTS.get(source_id, {}).items():
        if key not in scene.target_nodes:
            raise UnsupportedBinding('Authored custom part has no real target: ' + key)
        node = scene.target_nodes[key]
        if any((_path(node) == _path(existing) for _, existing, _ in parts)):
            continue
        parts.append((key, node, {'kind': 'rotate', 'closed': list(map(float, node['rotate'].Get())), 'delta': list(delta)}))
    owner_nodes = {}
    part_rows = []
    for key, node, motion in parts:
        parent = scene._h2_parent.get(_path(node))
        if parent is None:
            parent = scene._h2_groups.get(str(node['prim'].GetParent().GetPath()))
        if parent is None and key in CUSTOM_PUBLIC_PARTS.get(source_id, {}):
            parent = node
        if parent is None:
            raise UnsupportedBinding('Openable has no actual recorded parent: ' + key)
        path = _path(parent)
        owner = 'h2_owner_' + hashlib.sha256(path.encode()).hexdigest()[:12]
        owner_nodes[owner] = parent
        aliases = [k for k, n in scene.target_nodes.items() if _path(n) == _path(node)]
        if key in scene.target_nodes and key not in aliases:
            aliases.insert(0, key)
        open_key = key if key in aliases else aliases[0] if aliases else key
        local, size = _local_part_geometry(scene, node, parent)
        part_rows.append({'owner_id': owner, 'node': node, 'motion_key': key, 'open_key': open_key, 'close_key': open_key, 'aliases': aliases, 'motion': motion, 'local_x': float(local[0]), 'local_z': float(local[2]), 'local_width': float(size[0])})
    for path, node in scene._h2_groups.items():
        if scene._h2_parent.get(path) is not None:
            continue
        if node is scene.exit_node or any((node is target for target in scene.target_nodes.values())):
            continue
        try:
            tri = scene.triangles(node)
        except Exception:
            continue
        if np.asarray(tri).size == 0:
            continue
        owner = 'h2_owner_' + hashlib.sha256(path.encode()).hexdigest()[:12]
        owner_nodes.setdefault(owner, node)
    owners = []
    bindings = []
    for owner, node in owner_nodes.items():
        scene._h2_nodes[owner] = node
        rows = column_order([x for x in part_rows if x['owner_id'] == owner])
        ospec = {'owner_id': owner, 'node_access': '_h2_nodes[' + repr(owner) + ']', 'parts': []}
        for index, row in enumerate(rows, 1):
            key = row['motion_key']
            token = 'part_' + owner + '_' + str(index)
            scene._h2_nodes[token] = row['node']
            ospec['parts'].append({'part': index, 'open_key': row['open_key'], 'aliases': row['aliases']})
            rule = {'status': 'executable_structured', 'rule': {'path': '__h2_permission_placeholder', 'value': True}}
            bindings.append({'owner_id': owner, 'part': index, 'node_access': '_h2_nodes[' + repr(token) + ']', 'state_path': '_h2_physical.' + key, 'open_key': row['open_key'], 'close_key': row['close_key'], 'aliases': row['aliases'], 'motion_key': key, 'motion': row['motion'], 'opening_requirements': rule, 'closing_requirements': rule})
        owners.append(ospec)
    scene._h2_nodes['exit'] = scene.exit_node
    return ({'owners': owners}, {'bindings': bindings, 'door_bindings': [{'owner_id': 'h2_exit', 'node_access': "_h2_nodes['exit']", 'open_key': 'exit', 'state_path': 'opened.exit', 'motion': {'kind': 'rotate', 'closed': [0.0, 0.0, 90.0], 'delta': [0.0, 0.0, 100.0]}}]})
INSIDE_READ_PARTS = {'R24': {'sheet': 'crank_cab', 'grid_plate': 'read_door'}, 'R26': {'grid': 'arch_door'}, 'R27': {'plate': 'case_door'}, 'R29': {'gauge0': 'case_lid', 'gauge1': 'case_lid', 'gauge2': 'case_lid'}, 'R30': {'grid': 'rec_door'}, 'R32': {'ring': 'wheel_door'}, 'R34': {'b_table': 'read_door'}, 'R38': {'nb_face': 'board_cover'}, 'R40': {'base_face': 'locker_door'}, 'R44': {'b_table': 'table_cover'}}
INSIDE_READ_POSES = {'R40': {'stock_face': {'custom_key': 'hatch', 'component': 'rotate', 'closed': [0.0, 0.0, 0.0], 'open': [90.0, 0.0, 0.0]}}, 'R41': {'numbers': {'custom_key': 'lock_bar', 'component': 'translate', 'closed': [0.0, -0.215, 0.86], 'open': [0.0, -0.215, 0.72]}}}

def _bind_read_access(backend):
    backend.read_access = {}

    def matches(name, selector):
        key = backend.sim_to_key.get(name)
        surface = backend.read_surfaces.get(name, '')
        return key == selector or surface == 'screen:' + selector or bool(re.search('/' + re.escape(selector) + '(?:_|/|$)', _path(backend.objects[name].node)))
    for name in backend.item_metadata:
        rules = []
        for selector, cover in INSIDE_READ_PARTS.get(backend.level, {}).items():
            if not matches(name, selector):
                continue
            if cover not in backend.part_aliases:
                raise UnsupportedBinding('Inside read cover lacks its actual physical part: ' + cover)
            owner, part = backend.part_aliases[cover]
            rules.append({'kind': 'part_open', 'owner_id': owner, 'part': part, 'cover_key': cover, 'source_surface': selector})
        for selector, pose in INSIDE_READ_POSES.get(backend.level, {}).items():
            if not matches(name, selector):
                continue
            node = backend.scene.custom.get(pose['custom_key'])
            if node is None or pose['component'] not in node:
                raise UnsupportedBinding('Inside read cover lacks its actual authored USD op: ' + selector)
            rules.append(dict(pose, kind='pose_equal', source_surface=selector))
        if rules:
            backend.read_access[name] = rules

def _read_access_allowed(session, name):
    backend = session.backend
    for rule in backend.read_access.get(name, []):
        if rule['kind'] == 'part_open':
            if not session.esc.is_open(backend.objects[rule['owner_id']], 'j_part_' + str(rule['part'])):
                return False
        elif rule['kind'] == 'pose_equal':
            node = backend.scene.custom[rule['custom_key']]
            if not np.allclose(np.asarray(node[rule['component']].Get(), float), rule['open'], rtol=0.0, atol=1e-05):
                return False
        else:
            raise UnsupportedBinding('Unknown inside-readable access kind')
    return True

class H2Backend(RoomsBackend):

    def __init__(self, driver, working=BASE):
        self.working = Path(working).resolve()
        self.driver = driver
        self.scene = driver.scene
        self.game = driver.game
        self.level = str(getattr(driver.level, 'ID', Path(driver.level.__file__).stem.replace('level_', '')))
        roles = json.loads((self.working / 'H2_TARGET_ROLES.json').read_text('utf8'))['levels'][self.level]
        if roles['source_sha256'] != hashlib.sha256(Path(driver.level.__file__).read_bytes()).hexdigest():
            raise UnsupportedBinding('H2 semantic role source SHA mismatch')
        self.scene._h2_source_id = self.level
        self.scene._h2_source_sha256 = roles['source_sha256']
        self.inventory_items = set(roles['original_inventory_items'])
        fixture = PUBLIC_CATEGORY_FIXTURES.get(self.level, {})
        if fixture.get('source_sha256') != roles['source_sha256']:
            fixture = {}
        self.non_press_targets = set()
        self.non_item_targets = set()
        self.objects = {}
        self.escape = None
        self.query_count = 0
        self.predicates = {}
        self.session = None
        self.key_to_sim = {}
        self.sim_to_key = {}
        self.part_bindings = {}
        self.part_aliases = {}
        self.item_metadata = {}
        self.lock_endpoints = {}
        self.owner_map, self.motion_map = _physical(self.scene, self.level)
        for owner in sorted(self.owner_map['owners'], key=lambda row: row['owner_id']):
            oid = owner['owner_id']
            node = self.scene._h2_nodes[oid]
            label = str(node['prim'].GetName()).lower()
            category = 'table' if any((x in label for x in ['table', 'bench'])) else 'rack' if any((x in label for x in ['shelf', 'rack'])) else 'board' if any((x in label for x in ['board', 'picture', 'frame'])) else 'cabinet'
            obj = ObjectView(oid, category, self, node=node)
            rootpath = _path(node)
            partpaths = [_path(self.scene._h2_nodes['part_' + oid + '_' + str(b['part'])]) for b in self.motion_map['bindings'] if b['owner_id'] == oid]
            excluded = [_path(n) for k, n in self.scene.target_nodes.items() if _path(n) != rootpath and (not any((_path(n) == p or _path(n).startswith(p + '/') for p in partpaths)))]
            geometry = [n for path, n in self.scene._h2_shapes.items() if path.startswith(rootpath + '/') and (not any((path == q or path.startswith(q + '/') for q in excluded)))]
            if geometry:
                obj.nodes = geometry
            owner['public_label'] = category
            self.objects[oid] = obj
        for binding in self.motion_map['bindings']:
            owner = binding['owner_id']
            part = binding['part']
            node = self.scene._h2_nodes['part_' + owner + '_' + str(part)]
            joint = 'j_part_' + str(part)
            obj = self.objects[owner]
            obj.links[joint[2:]] = ObjectView(owner + '_part_' + str(part), 'part', self, node=node)
            obj.joints[joint] = MotionJoint(self, node, binding)
            self.part_bindings[owner, part] = binding
            for key in list(dict.fromkeys([binding['open_key']] + binding['aliases'])):
                self.part_aliases[key] = (owner, part)
        self.door_binding = self.motion_map['door_bindings'][0]
        self.exit_name = 'h2_exit'
        node = self.scene.exit_node
        door = ObjectView(self.exit_name, 'door', self, node=node)
        door.links['panel'] = ObjectView(self.exit_name + '_panel', 'door', self, node=node)
        door.joints['j_panel'] = MotionJoint(self, node, self.door_binding)
        door.metadata['openable_joint_ids'] = {'panel': 'j_panel'}
        self.objects[self.exit_name] = door
        self.key_to_sim['exit'] = self.exit_name
        self.sim_to_key[self.exit_name] = 'exit'
        self.gadget_sims = {}
        self.original_poses = {}
        self.take_geometry_aliases = {}
        for key, node in sorted(self.scene.target_nodes.items()):
            if key in self.part_aliases or key == 'exit':
                continue
            name = 'h2_item_' + key
            category = 'code lock' if key == 'exit_lock' else public_label(self.scene, key) if key in self.inventory_items or key in fixture.get('items', {}) else 'electric switch'
            obj = ObjectView(name, category, self, node=node)
            self.objects[name] = obj
            self.key_to_sim[key] = name
            self.sim_to_key[name] = key
            enclosing = [(len(_path(self.objects[owner].node)), owner) for owner in self.owner_map_ids if _path(node) == _path(self.objects[owner].node) or _path(node).startswith(_path(self.objects[owner].node) + '/')]
            container = max(enclosing)[1] if enclosing else None
            self.item_metadata[name] = {'item_key': key, 'target_key': key, 'owner_id': container, 'part': None, 'kind': 'loose', 'fixed': key == 'exit_lock', 'take_gate': []}
            if key != 'exit_lock':
                self.gadget_sims[name] = key
            if key in fixture.get('non_press_receivers', []):
                self.non_press_targets.add(name)
            if key in fixture.get('non_item_receivers', []):
                if key in self.inventory_items or any((r['text'] for r in _read_target_rows(self.scene, node, key))):
                    raise UnsupportedBinding('Use-only receiver is actually a tool/readable: ' + key)
                self.non_item_targets.add(name)
            self.original_poses[name] = self.pose(obj)
        _add_read_surfaces(self)
        _bind_read_access(self)
        self._door_boxes = {self.exit_name: tuple(door.aabb)}

    def bounds(self, obj):
        alias = self.take_geometry_aliases.get(obj.name)
        if alias is not None and self.escape is not None and (not self.escape.items[obj.name].get('taken')):
            points = self.scene.triangles(alias).reshape(-1, 3)
            if not points.size:
                raise UnsupportedBinding('Take alias has no physical target mesh')
            return np.array([points.min(0), points.max(0)])
        return super().bounds(obj)

    def pose(self, obj):
        alias = self.take_geometry_aliases.get(obj.name)
        if alias is not None and self.escape is not None and (not self.escape.items[obj.name].get('taken')):
            proxy = ObjectView(obj.name, obj.category, self, node=alias)
            return super().pose(proxy)
        return super().pose(obj)

    def step(self, n=1):
        for _ in range(max(1, int(n))):
            self.driver.og.sim.step()

    def visible(self, obj):
        if self.escape is not None and obj.name in getattr(self.escape, '_hidden', []):
            return False
        if obj.name in self.owner_map_ids:
            return True
        if obj.name in self.read_surfaces:
            row = _read_surfaces(self.scene).get(self.read_surfaces[obj.name])
            return bool(row and _node_visible(self.scene, row['node']))
        key = self.sim_to_key.get(obj.name)
        return key is None or bool(self.scene.visible(key, self.game))

class H2Session(RoomsSession):

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
        self._part_proposals = {}
        self._take_proposals = {}
        self._projecting = False
        self._restoring = False
        self._alias_originals = {}
        self._authored_door_open = self.driver.scene.door_open
        self._authored_h2_lock_feedback = json.loads((backend.working / 'native_runtime/H2_LOCK_FEEDBACK.json').read_text('utf8'))['levels']
        lock_row = self._authored_h2_lock_feedback.get(backend.level)
        if lock_row is None or lock_row['source_sha256'] != hashlib.sha256(Path(self.driver.level.__file__).read_bytes()).hexdigest():
            raise UnsupportedBinding('Lock feedback source SHA mismatch')
        install_mechanism_hooks(E)
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        cfg = {'name': 'native_bridge_' + backend.level, 'scene': 'programmatic_' + backend.level, 'start': {'xy': list(self.driver.pos[:2]), 'yaw_deg': math.degrees(self.driver.yaw)}, 'max_steps': 250, 'recall_budget': 25, 'tip_window': 60, 'native_devices_visual': False, 'native_use_visual': False, 'items': [], 'part_locks': [{'container': o, 'part': p} for o, p in backend.part_bindings], 'doors': [{'name': backend.exit_name, 'lock': str(self.game.SPEC['door_code']), 'exit': True}], 'gadgets': [{'name': name, 'type': 'native_mechanism'} for name in backend.gadget_sims]}
        for name, row in backend.item_metadata.items():
            if name not in backend.non_item_targets:
                cfg['items'].append({'id': row['item_key'], 'name': name, 'kind': 'tool', 'text': ''})
        ctx = {'env': types.SimpleNamespace(scene=types.SimpleNamespace(objects=list(backend.objects.values()), object_registry=lambda k, n: backend.objects.get(n))), 'E': types.SimpleNamespace(quat_from=quat_from), 'pos': list(self.driver.pos), 'shot': backend.capture, 'detect': backend.detect, 'step_sim': backend.step, 'fov_h': lambda: math.pi / 2}
        self.esc = E.Escape(ctx, cfg, out)
        backend.escape = self.esc
        e = self.esc
        e._native_read_only_data_targets = set(backend.read_surfaces)
        e.floor = 0.0
        e._cam_z0 = e.cam_z
        e._hidden = []
        e._native_photo_metadata_hook = backend.photo_metadata
        e._native_front_mesh_guard = backend.front_mesh_guard
        if getattr(getattr(self.driver, 'og', None), 'env', None) is not None:
            e._video_native_scene = self.driver.og.env.scene
        e._native_mechanism_hook = self.mechanism
        e._native_mechanism_targets = set(backend.gadget_sims)
        e._native_press_capabilities = set(backend.gadget_sims) - backend.non_press_targets
        e._native_take_gate = self.take_gate
        e._native_taken_hook = self.on_taken
        e._native_part_gate = self.part_gate
        e._native_part_gate_failure = self.part_gate_failure
        e._native_read_text = self.read_text
        e._native_read_kind = self.read_kind
        e._native_unlock_gate = self.unlock_gate
        e._native_item_alias = self.item_alias
        for index, obj in enumerate(backend.objects.values(), 1):
            e.objs[index] = {'id': index, 'sim': obj.name, 'cat': obj.category, 'center': obj.aabb.mean(0).tolist()}
            e.by_sim[obj.name] = index
        self.key_to_oid = {k: e.by_sim[v] for k, v in backend.key_to_sim.items()}
        self.oid_to_key = {v: k for k, v in self.key_to_oid.items()}
        for key, (owner, part) in backend.part_aliases.items():
            self.key_to_oid[key] = e.by_sim[owner]
        for owner, obj in backend.objects.items():
            if obj.joints:
                e._parts[owner] = [(j, 'drawer' if 'Prismatic' in str(v.joint_type) else 'door') for j, v in obj.joints.items()]
                e._closed_box[owner] = tuple(obj.aabb.copy())
        for name, row in backend.item_metadata.items():
            if name in backend.non_item_targets:
                e._display[name] = public_label(self.driver.scene, row['item_key'])
                continue
            st = {'id': row['item_key'], 'name': name, 'container': row.get('owner_id') or name, 'part': 0, 'joint': None, 'kind': 'loose', 'fixed': row['fixed'], 'text': '', 'lockd': None, 'unlocked': True, 'taken': False}
            if row['item_key'] == 'exit_lock':
                st = LinkedLockItem(st, e.doors[backend.exit_name])
            e.items[name] = st
            e._display[name] = row.get('read_only_label') or self.driver.label(row['item_key'])
        from scipy.spatial.transform import Rotation
        for owner in backend.owner_map_ids:
            key = next((b['open_key'] for (o, p), b in backend.part_bindings.items() if o == owner), None)
            e._display[owner] = self.driver.label(key) if key else backend.objects[owner].category
            e._fronts[owner] = Rotation.from_quat(backend.pose(backend.objects[owner])[1]).apply([0.0, -1.0, 0.0])[:2]
        e._display[backend.exit_name] = 'exit door'
        e._wallmap = np.zeros((640, 640), bool)
        res = e.GUARD_RES
        e._wallmap[320:320 + int(5.0 / res), 320:320 + int(9.6 / res)] = True
        x = 320 + int(round(4.8 / res))
        e._wallmap[320:320 + int(5.0 / res), x - 1:x + 2] = False
        e._wallmap[320 + int(1.8 / res):320 + int(2.95 / res), x - 1:x + 2] = True
        e._door_boxes = backend._door_boxes
        e._window_boxes = {}
        e._semmap = np.ones((3200, 3200), np.uint8)
        e._roomcats = ['room_A', 'room_B']
        self.generic_identity = {name: getattr(E.Escape, name) for name in ['act', 'a_open', 'a_close', 'a_take', 'a_unlock', 'a_use']}
        original = self._authored_door_open

        def door_open(scene, key, g):
            if g is self.game:
                entry = next(((o, p) for (o, p), b in backend.part_bindings.items() if b['motion_key'] == key), None)
                if entry:
                    return bool(e.is_open(backend.objects[entry[0]], 'j_part_' + str(entry[1])))
            return original(key, g)
        self.driver.scene.door_open = types.MethodType(door_open, self.driver.scene)
        self.project()

    def _proposal(self, key, verb, item=None):
        return authored_proposal(self.game, key, verb, item, self.esc.pos)

    def _commit(self, snapshot):
        _snapshot_to_game(self.game, snapshot)

    def part_gate(self, owner, part, verb):
        binding = self.backend.part_bindings[owner, part]
        key = binding['open_key']
        result, state = self._proposal(key, verb)
        if result.get('ok'):
            previous = bool(self.esc.is_open(self.backend.objects[owner], 'j_part_' + str(part)))
            self._part_proposals[owner, part] = {'state': state, 'before_open': previous, 'want_open': verb == 'open'}
            self.esc.part_locks[owner, part]['unlocked'] = True
            return True
        return False

    def item_alias(self, obj, st, verb):
        key = self.backend.sim_to_key.get(st['name'])
        if key is None:
            return (obj, st, None)
        result, state = self._proposal(key, 'take')
        if not result.get('ok'):
            return (obj, st, None)
        added = [v for v in state['holding'] if v not in self.game.holding]
        if len(added) != 1:
            raise UnsupportedBinding('Authored take has ambiguous inventory identity: ' + key)
        item = added[0]
        if item == key:
            return (obj, st, None)
        canonical = self.backend.key_to_sim.get(item)
        if canonical is None or canonical not in self.esc.items:
            raise UnsupportedBinding('Recovered item lacks an authored original mesh: ' + item)
        target = self.esc.items[canonical]
        self._alias_originals[canonical] = {'state': copy.deepcopy(dict(target)), 'center': copy.deepcopy(self.esc.objs[self.esc.by_sim[canonical]]['center'])}
        target['gone'] = False
        target['taken'] = False
        target['container'] = st['container']
        target.pop('slot', None)
        self.backend.take_geometry_aliases[canonical] = self.backend.objects[st['name']].node
        self._take_proposals[canonical] = state
        newobj = self.esc.objs[self.esc.by_sim[canonical]]
        newobj['center'] = self.backend.bounds(self.backend.objects[canonical]).mean(0).tolist()
        return (newobj, target, None)

    def take_gate(self, name):
        if name in self.backend.take_geometry_aliases and name in self._take_proposals:
            return True
        key = self.backend.sim_to_key[name]
        result, state = self._proposal(key, 'take')
        if result.get('ok'):
            delta = [v for v in state['holding'] if v not in self.game.holding]
            if len(delta) != 1:
                raise UnsupportedBinding('Authored take must produce one inventory item: ' + key)
            self._take_proposals[name] = state
            self.backend.item_metadata[name]['item_key'] = delta[0]
            self.esc.items[name]['id'] = delta[0]
        return bool(result.get('ok'))

    def on_taken(self, name):
        state = self._take_proposals.pop(name, None)
        if state is None:
            raise UnsupportedBinding('Canonical take has no successful authored puzzle effect')
        self._commit(state)
        key = self.backend.item_metadata[name]['item_key']
        label = public_label(self.driver.scene, key)
        self.backend.objects[name].category = label
        self.esc.objs[self.esc.by_sim[name]]['cat'] = label
        self.esc._display[name] = label
        self.esc.items[name]['gone'] = False

    def read_kind(self, name):
        if not _read_access_allowed(self, name):
            return None
        b = self.backend
        scene = b.scene
        if name in b.read_surfaces:
            row = _read_surfaces(scene).get(b.read_surfaces[name])
            rows = [row] if row else []
        else:
            obj = b.objects.get(name)
            rows = _read_target_rows(scene, obj.node, b.sim_to_key.get(name, '')) if obj is not None else []
        rows = [r for r in rows if self.esc.items.get(name, {}).get('taken') or _node_visible(scene, r['node'])]
        if not rows:
            return None
        return 'visual_only' if any((r.get('read_content_kind') != 'text_only' for r in rows)) else 'text_only'

    def read_text(self, name):
        b = self.backend
        scene = b.scene
        if not _read_access_allowed(self, name):
            return ''
        if name in b.read_surfaces:
            row = _read_surfaces(scene).get(b.read_surfaces[name])
            rows = [row] if row else []
        else:
            obj = b.objects.get(name)
            rows = _read_target_rows(scene, obj.node, b.sim_to_key.get(name, '')) if obj is not None else []
        return '\n'.join((r['text'] for r in rows if r['text'] and _node_visible(scene, r['node']))).strip()

    def clue_text(self, key):
        return ''

    def unlock_gate(self, a):
        obj = self.esc.objs.get(a.get('target'), {})
        sim = obj.get('sim')
        key = self.backend.sim_to_key.get(sim)
        if sim == self.backend.exit_name or key == 'exit_lock':
            self.game.possessions['door_input'] = str(a.get('code', ''))
        return True

    def project(self):
        if self._projecting or self._restoring:
            return
        self._projecting = True
        try:
            e = self.esc
            b = self.backend
            g = self.game
            for (owner, part), proposal in list(self._part_proposals.items()):
                now = bool(e.is_open(b.objects[owner], 'j_part_' + str(part)))
                if now == proposal['want_open'] and now != proposal['before_open']:
                    self._commit(proposal['state'])
                    self._part_proposals.pop((owner, part), None)
            g.holding = [b.item_metadata[e.objs[i]['sim']]['item_key'] for i in e.holding]
            for name, row in b.item_metadata.items():
                if name in e.items and e.items[name].get('taken'):
                    g.taken.add(row['item_key'])
            g.opened['exit'] = b.exit_name in e.passed_doors
            g.exit_unlocked = bool(e.doors[b.exit_name]['unlocked'])
            g.exited = bool(e.success)
            saved = []
            for (owner, part), binding in b.part_bindings.items():
                node = b.objects[owner].links['part_' + str(part)].node
                saved.append((node, list(node['translate'].Get()), list(node['rotate'].Get())))
            node = b.scene.exit_node
            saved.append((node, list(node['translate'].Get()), list(node['rotate'].Get())))
            b.scene.sync(g)
            _refresh_read_surfaces(b)
            for node, pos, rpy in saved:
                b.scene.transform(node, pos=pos, rpy=rpy)
            if b.native:
                from pxr import Usd, UsdPhysics
                with self.driver.og.sim.editing_usd():
                    for name, st in e.items.items():
                        obj = b.objects[name]
                        enabled = not st.get('taken') and (b.visible(obj) if name in b.read_surfaces else bool(b.scene.visible(b.sim_to_key[name], g)))
                        for prim in Usd.PrimRange(obj.node['prim']):
                            if prim.HasAPI(UsdPhysics.CollisionAPI):
                                UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Set(enabled)
        finally:
            self._projecting = False

    def mechanism(self, kind, name, item_name, a):
        if kind not in ('press', 'use'):
            raise UnsupportedBinding('Only puzzle press/use callbacks may run live Game.act')
        self.project()
        b = self.backend
        g = self.game
        key = b.gadget_sims[name]
        before = g.snapshot()
        logical_before = {entry['motion_key']: bool(self._authored_door_open(entry['motion_key'], g)) for entry in b.part_bindings.values()}
        internal = {'action': kind, '_hit364': key, '_validated364': True, '_actor_position364': self.esc.pos.tolist()}
        if item_name is not None:
            internal['item'] = b.item_metadata[item_name]['item_key']
        result = type(g).act(g, internal)
        if not result.get('ok'):
            return result
        after = g.snapshot()
        for (owner, part), binding in b.part_bindings.items():
            now = bool(self._authored_door_open(binding['motion_key'], g))
            if now != logical_before[binding['motion_key']]:
                self.esc.set_joint(b.objects[owner], 'j_part_' + str(part), now)
        removed = set(before['holding']) - set(after['holding'])
        added = set(after['holding']) - set(before['holding'])
        for item in removed:
            names = [n for n, row in b.item_metadata.items() if row['item_key'] == item and self.esc.items[n].get('taken')]
            if len(names) != 1:
                raise UnsupportedBinding('Inventory effect does not identify one real held object: ' + item)
            st = self.esc.items[names[0]]
            self.esc._slot_place(self.esc.gadgets[name], st)
            st['gone'] = False
        for item in added:
            names = [n for n, row in b.item_metadata.items() if row['item_key'] == item]
            if len(names) != 1:
                raise UnsupportedBinding('Returned item does not identify one authored object: ' + item)
            st = self.esc.items[names[0]]
            st.update(taken=True, gone=False)
            st.pop('slot', None)
            oid = self.esc.by_sim[names[0]]
            if oid not in self.esc.holding:
                self.esc.holding.append(oid)
            if names[0] not in getattr(self.esc, '_hidden', []):
                self.esc._hide(names[0])
        for item in set(before['taken']) - set(after['taken']):
            for n, row in b.item_metadata.items():
                if row['item_key'] != item:
                    continue
                st = self.esc.items[n]
                st.update(taken=False, gone=False)
                st.pop('slot', None)
                oid = self.esc.by_sim[n]
                self.esc.holding[:] = [v for v in self.esc.holding if v != oid]
                self.esc._hidden[:] = [v for v in getattr(self.esc, '_hidden', []) if v != n]
                b.set_pose(b.objects[n], *b.original_poses[n])
        self.driver.current_hit = {'key': key, 'source': 'actual_common_legacy_resolution'}
        count = len(getattr(self.driver, 'current_visual_feedback', []))
        self.project()
        if hasattr(b.scene, 'animate'):
            b.scene.animate(self.driver, before)
        self.extra_images.extend(getattr(self.driver, 'current_visual_feedback', [])[count:])
        return result

    def act(self, action):
        e = self.esc
        self._part_proposals.clear()
        self._take_proposals.clear()
        e._native_public_kind = action.get('action')
        self.extra_images = []
        from observation_group import begin
        begin(self)
        e.t = int(getattr(self.driver, '_legacy_action_step', self.driver.step + 1))
        result = e.act(dict(action))
        for name, prior in self._alias_originals.items():
            if not result.get('ok'):
                e.items[name].clear()
                e.items[name].update(prior['state'])
            if result.get('ok'):
                e.items[name]['container'] = prior['state']['container']
            e.objs[e.by_sim[name]]['center'] = prior['center']
        self._alias_originals.clear()
        self.backend.take_geometry_aliases.clear()
        if action.get('action') == 'unlock' and result.get('unlock_monitor') is not None:
            self.game.possessions['door_input'] = str(action.get('code', ''))
        self.project()
        self.driver.pos = e.pos.copy()
        self.driver.yaw = float(e.yaw)
        self.driver.pitch = math.radians(getattr(e, '_claw_pitch', 0.0))
        result = dict(result)
        if not result.get('images'):
            boxed, _ = self.C.shoot(e, 'h2_current_result')
            e._claw_photos = [boxed]
            result['images'] = [self.C._small(e, boxed)]
        if self.extra_images:
            result['images'] = list(dict.fromkeys(self.extra_images + result['images']))
        from observation_group import finalize
        finalize(self, result['images'])
        self._part_proposals.clear()
        self._take_proposals.clear()
        return result

    def checkpoint_state(self):
        e = self.esc
        b = self.backend
        return {'bridge_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'roles_sha256': hashlib.sha256((b.working / 'H2_TARGET_ROLES.json').read_bytes()).hexdigest(), 'joint_values': [{'owner': o, 'joint': name, 'position': float(np.asarray(joint.get_state()[0]).ravel()[0]), 'lower': float(joint.lower_limit), 'upper': float(joint.upper_limit), 'max_velocity': float(joint.max_velocity)} for o, obj in b.objects.items() for name, joint in obj.joints.items()], 'door_closed_positions': copy.deepcopy(getattr(e, '_door_closed_pos', {})), 'door_flipped': list(getattr(e, '_door_flipped', set())), 'objects': copy.deepcopy(e.objs), 'display': copy.deepcopy(e._display), 'observation_group': __import__('observation_group').checkpoint(self), 'source_sha256': hashlib.sha256(Path(self.driver.level.__file__).read_bytes()).hexdigest(), 'game': copy.deepcopy(self.game.snapshot()), 'part_open': [{'owner': o, 'part': p, 'open': bool(e.is_open(b.objects[o], 'j_part_' + str(p)))} for o, p in b.part_bindings], 'exit_open': b.exit_name in e.passed_doors, 'exit_unlocked': bool(e.doors[b.exit_name]['unlocked']), 'success': bool(e.success), 'holding_sims': [e.objs[i]['sim'] for i in e.holding], 'items': {n: {k: copy.deepcopy(st[k]) for k in st} for n, st in e.items.items()}, 'inventory_keys': {n: v['item_key'] for n, v in b.item_metadata.items()}, 'part_locks': [{'owner': o, 'part': p, 'record': copy.deepcopy(v)} for (o, p), v in e.part_locks.items()], 'doors': copy.deepcopy(e.doors), 'hidden': list(getattr(e, '_hidden', [])), 'marks': copy.deepcopy(e.marks), 'read_texts': copy.deepcopy(e.read_texts), 'memory': copy.deepcopy(e.memory), 'recalls': int(e.recalls), 't': int(e.t), 'gadgets': copy.deepcopy(e.gadgets)}

    def restore_checkpoint_state(self, value):
        assert value['source_sha256'] == hashlib.sha256(Path(self.driver.level.__file__).read_bytes()).hexdigest(), 'H2 source changed since checkpoint'
        assert value.get('bridge_sha256') == hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'H2 bridge changed since checkpoint'
        e = self.esc
        b = self.backend
        assert value.get('roles_sha256') == hashlib.sha256((b.working / 'H2_TARGET_ROLES.json').read_bytes()).hexdigest(), 'H2 identity data changed since checkpoint'
        assert set(value['items']) == set(e.items)
        self._restoring = True
        try:
            _snapshot_to_game(self.game, value['game'])
            for row in value['joint_values']:
                joint = b.objects[row['owner']].joints[row['joint']]
                joint.lower_limit = float(row['lower'])
                joint.upper_limit = float(row['upper'])
                joint.max_velocity = float(row['max_velocity'])
                joint.set_pos(float(row['position']), drive=False)
            e._door_closed_pos = copy.deepcopy(value['door_closed_positions'])
            e._door_flipped = set(value['door_flipped'])
            for oid, obj in value['objects'].items():
                oid = int(oid)
                assert e.objs[oid]['sim'] == obj['sim'], 'H2 object identity changed'
                e.objs[oid].update(copy.deepcopy(obj))
            e._display = copy.deepcopy(value['display'])
            for row in value['part_locks']:
                e.part_locks[row['owner'], row['part']].update(copy.deepcopy(row['record']))
            for n, record in value['doors'].items():
                e.doors[n].update(copy.deepcopy(record))
            for n, record in value['items'].items():
                e.items[n].update(copy.deepcopy(record))
            for n, key in value.get('inventory_keys', {}).items():
                b.item_metadata[n]['item_key'] = key
            e.holding = [e.by_sim[n] for n in value['holding_sims']]
            e.passed_doors = {b.exit_name} if value['exit_open'] else set()
            e.success = bool(value['success'])
            e._hidden = list(value['hidden'])
            e.marks = copy.deepcopy(value['marks'])
            e.read_texts = copy.deepcopy(value['read_texts'])
            e.memory = copy.deepcopy(value['memory'])
            e.recalls = int(value['recalls'])
            e.t = int(value['t'])
            for n, record in value.get('gadgets', {}).items():
                e.gadgets[n].update(copy.deepcopy(record))
        finally:
            self._restoring = False
        self.project()
        __import__('observation_group').restore(self, value.get('observation_group'))

def attach(driver, out, working=BASE, E=None, C=None):
    if E is None:
        E, C = load_stack(Path(working))
    if not getattr(driver.scene, '_h2_instrumented', False):
        raise UnsupportedBinding('H2 scene was not instrumented before build')
    backend = H2Backend(driver, working=working)
    session = H2Session(backend, out, E, C)
    session.native_gate()
    from observation_group import attach as attach_photos
    attach_photos(driver, session)
    driver.save('H2_COMMON_BINDINGS.json', {'source_id': backend.level, 'source_sha256': hashlib.sha256(Path(driver.level.__file__).read_bytes()).hexdigest(), 'owner_map': backend.owner_map, 'motion_map': backend.motion_map, 'actual_E_file': str(Path(E.__file__).resolve()), 'actual_C_file': str(Path(C.__file__).resolve()), 'public_Game_act_fallback': False, 'model_calls': 0})
    labels = {}
    for key in driver.scene.target_nodes:
        sim = backend.key_to_sim.get(key)
        if sim is None and key in backend.part_aliases:
            sim = backend.part_aliases[key][0]
        oid = session.esc.by_sim.get(sim)
        labels[key] = {'scene_label': driver.scene.label_for(key), 'driver_label': driver.label(key), 'category': session.esc.objs.get(oid, {}).get('cat'), 'public_display': session.esc._display.get(sim), 'original_inventory_item': key in backend.inventory_items, 'explicit_scene_label': getattr(driver.scene, '_h2_explicit_labels', {}).get(key)}
    driver.save('PUBLIC_LABELS.json', {'source_id': backend.level, 'labels': labels, 'owner_public_labels': {x['owner_id']: x['public_label'] for x in backend.owner_map['owners']}, 'private_verification_only': True, 'sent_to_model': False, 'model_calls': 0})
    return session
