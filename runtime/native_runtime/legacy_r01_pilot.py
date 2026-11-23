from pathlib import Path
import copy
import sys, os, math, json, types, importlib.util, contextlib, hashlib
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
ROOT = Path(__file__).resolve().parent
WORKING = ROOT.parent if (ROOT.parent / 'legacy_entry.py').is_file() else ROOT.parent / 'working'

def load_stack(working=WORKING):
    os.environ['ESI_ESCAPE_REFS'] = 'claw'
    os.environ['ESI_ESCAPE_PERSIST'] = '1'
    os.environ['ESI_ESCAPE_VIDEO'] = '0'
    sys.path.insert(0, str(working))
    spec = importlib.util.spec_from_file_location('_pilot_legacy_entry', working / 'legacy_entry.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.install_stack()[:2]

def quat_from(yaw, pitch):
    p = math.radians(pitch)
    f = np.array([math.cos(p) * math.cos(yaw), math.cos(p) * math.sin(yaw), math.sin(p)])
    right = np.array([math.sin(yaw), -math.cos(yaw), 0.0])
    up = np.cross(right, f)
    return Rotation.from_matrix(np.column_stack([right, up, -f])).as_quat()

class ObjectView:

    def __init__(self, name, category, backend, node=None, bounds=None):
        self.name = name
        self.category = category
        self.backend = backend
        self.node = node
        self._bounds = np.array(bounds, float) if bounds is not None else None
        self.links = {}
        self.joints = {}
        self.metadata = {}

    @property
    def aabb(self):
        return self.backend.bounds(self)

    def get_position_orientation(self):
        return self.backend.pose(self)

    def set_position_orientation(self, position=None, orientation=None):
        self.backend.set_pose(self, position, orientation)

    def keep_still(self):
        pass

    def disable_gravity(self):
        pass

class CpuJoint:

    def __init__(self, part, kind, upper=0.5):
        self.part = part
        self.joint_type = kind
        self.lower_limit = 0.0
        self.upper_limit = upper
        self.q = 0.0
        self.max_velocity = 0.0

    def get_state(self):
        return (np.array([self.q]), np.array([0.0]), None)

    def set_pos(self, q, drive=False):
        delta = float(q) - self.q
        self.q = float(q)
        if 'Prismatic' in self.joint_type:
            self.part._bounds[:, 1] -= delta

class XformJoint:

    def __init__(self, backend, node, kind, axis, sign, upper):
        self.backend = backend
        self.node = node
        self.joint_type = kind
        self.axis = axis
        self.sign = sign
        self.lower_limit = 0.0
        self.upper_limit = float(upper)
        self.max_velocity = 0.0
        self.closed = np.array((node['translate'] if 'Prismatic' in kind else node['rotate']).Get(), float)

    def get_state(self):
        op = self.node['translate'] if 'Prismatic' in self.joint_type else self.node['rotate']
        now = np.array(op.Get(), float)
        q = (now[self.axis] - self.closed[self.axis]) * self.sign
        if 'Revolute' in self.joint_type:
            q = math.radians(q)
        return (np.array([q]), np.array([0.0]), None)

    def set_pos(self, q, drive=False):
        op = self.node['translate'] if 'Prismatic' in self.joint_type else self.node['rotate']
        now = np.array(op.Get(), float)
        now[self.axis] = self.closed[self.axis] + self.sign * (float(q) if 'Prismatic' in self.joint_type else math.degrees(float(q)))
        self.backend.scene.transform(self.node, **{'pos': now.tolist()} if 'Prismatic' in self.joint_type else {'rpy': now.tolist()})

class CpuBackend:
    native = False

    def __init__(self):
        self.objects = {}
        self.escape = None
        self.pos = np.array([0.8, 4.0, 1.35])
        self.depth = None
        self.query_count = 0
        self.add('cabinet', 'cabinet', [[0.4, 4.8, 0.1], [1.2, 5.35, 1.45]])
        for i, z in enumerate([1.12, 0.78, 0.44], 1):
            part = self.add('drawer' + str(i), 'drawer', [[0.42, 4.8, z - 0.14], [1.18, 5.32, z + 0.14]])
            j = 'j_drawer' + str(i)
            self.objects['cabinet'].links[j[2:]] = part
            self.objects['cabinet'].joints[j] = CpuJoint(part, 'PrismaticJoint')
        for name, cat, box in [('toolbox', 'cabinet', [[2.4, 4.8, 0.7], [3.3, 5.3, 1.1]]), ('vent', 'cabinet', [[0.65, 0.02, 0.6], [1.6, 0.16, 1.3]]), ('exit', 'door', [[3.18, 0.02, 0], [4.22, 0.12, 2.25]])]:
            o = self.add(name, cat, box)
            o.links['panel'] = o
            o.joints['j_panel'] = CpuJoint(o, 'RevoluteJoint', 1.75)
        self.add('screwdriver', 'screwdriver', [[2.7, 4.9, 0.83], [2.95, 5.05, 0.88]])
        self.add('key', 'key', [[1.0, -0.005, 0.85], [1.18, 0.04, 0.94]])
        self.add('logic_note', 'paper', [[2.0, 2.8, 0.75], [2.3, 3.0, 0.76]])
        self.add('paper', 'paper', [[0.65, 4.98, 0.79], [0.95, 5.17, 0.8]])
        for i in range(1, 5):
            self.add('vent_screw_' + str(i), 'screw', [[0.67 + i // 3 * 0.82, 0.03, 0.64 + (i - 1) % 2 * 0.59], [0.73 + i // 3 * 0.82, 0.1, 0.7 + (i - 1) % 2 * 0.59]])

    def add(self, name, category, bounds):
        o = ObjectView(name, category, self, bounds=bounds)
        self.objects[name] = o
        return o

    def bounds(self, o):
        return o._bounds.copy()

    def pose(self, o):
        return (o._bounds.mean(0), np.array([0.0, 0.0, 0.0, 1.0]))

    def set_pose(self, o, pos, q):
        if pos is not None:
            o._bounds += np.asarray(pos) - o._bounds.mean(0)

    def step(self, n=1):
        pass

    def capture(self, path, pos, q):
        Image.new('RGB', (1280, 720), (120, 120, 120)).save(path)
        self.pos = np.array(pos)
        self.q = np.array(q)

    def visible(self, o):
        e = self.escape
        if o.name == 'paper' and (not e.is_open(self.objects['cabinet'], 'j_drawer2')):
            return False
        if o.name == 'screwdriver' and (not e.is_open(self.objects['toolbox'], 'j_panel')):
            return False
        return o.name not in getattr(e, '_hidden', [])

    def detect(self, path, pos, q):
        out = []
        R = Rotation.from_quat(q).as_matrix()
        for o in self.objects.values():
            if o.name.startswith('drawer') or not self.visible(o):
                continue
            lo, hi = o.aabb
            v = np.array([[x, y, z] for x in [lo[0], hi[0]] for y in [lo[1], hi[1]] for z in [lo[2], hi[2]]])
            v = (v - pos) @ R
            d = -v[:, 2]
            if np.any(d <= 0.02):
                continue
            px = 640 + 640 * v[:, 0] / d
            py = 360 - 640 * v[:, 1] / d
            r = [max(0, int(px.min())), max(0, int(py.min())), min(1279, int(px.max())), min(719, int(py.max()))]
            if r[0] < r[2] and r[1] < r[3]:
                out.append({'cat': o.category, 'center': list((lo + hi) / 2), 'bbox': r})
        return (out, np.full((720, 1280), np.inf, np.float32))

    def overlap_sphere(self, r, pos, callback, flag):
        self.query_count += 1
        p = np.array(pos)
        for o in self.objects.values():
            if o.name.startswith('drawer'):
                continue
            lo, hi = o.aabb
            if np.linalg.norm(p - np.clip(p, lo, hi)) <= r:
                callback(types.SimpleNamespace(rigid_body='/World/redesign364/' + o.name + '/mesh'))

class NativeBackend(CpuBackend):
    native = True

    def __init__(self, driver):
        self.driver = driver
        self.scene = driver.scene
        self.objects = {}
        self.escape = None
        self.query_count = 0
        s = self.scene

        def add(name, cat, node):
            o = ObjectView(name, cat, self, node=node)
            self.objects[name] = o
            return o
        cab = add('cabinet', 'cabinet', s.furniture_roots['cabinet'])
        for i in range(1, 4):
            node = s.drawers['drawer' + str(i)]
            p = add('drawer' + str(i), 'drawer', node)
            jn = 'j_drawer' + str(i)
            cab.links[jn[2:]] = p
            cab.joints[jn] = XformJoint(self, node, 'PrismaticJoint', 1, -1, 0.5)
        for name, cat, node, part, axis, sign, upper in [('toolbox', 'cabinet', s.case, s.lid, 0, -1, math.radians(80)), ('vent', 'cabinet', s.grille, s.grille, 2, 1, math.radians(105)), ('exit', 'door', s.door_node, s.door_node, 2, -1, math.radians(103))]:
            o = add(name, cat, node)
            link = ObjectView(name + '_panel', cat, self, node=part)
            o.links['panel'] = link
            o.joints['j_panel'] = XformJoint(self, part, 'RevoluteJoint', axis, sign, upper)
        for name in ['screwdriver', 'key', 'paper', 'logic_note'] + ['vent_screw_' + str(i) for i in range(1, 5)]:
            add(name, 'screw' if name.startswith('vent_screw') else 'paper' if name in ('paper', 'logic_note') else name, s.target_nodes[name])
        self.source_module = driver.level
        self.extra_item_defs = []
        source = getattr(driver.level, 'SOURCES', {})
        labels = getattr(driver.level, 'LABELS', {})
        takeable = set(getattr(driver.level, 'TAKEABLE', ()))
        for key, node in s.target_nodes.items():
            if key in self.objects or key.startswith('drawer') or key == 'cabinet_body':
                continue
            if key not in source and key not in ('round_table', 'workbench', 'rack'):
                continue
            category = 'ball' if key.startswith('ball_') else 'table' if key in ('round_table', 'workbench') else 'rack' if key == 'rack' else str(labels.get(key, key))
            add(key, category, node)
            if key in source:
                parent = source[key]
                jn = None
                part = 0
                if parent and parent.startswith('drawer'):
                    part = int(parent[-1])
                    parent = 'cabinet'
                    jn = 'j_drawer' + str(part)
                elif parent in ('toolbox', 'vent'):
                    jn = 'j_panel'
                    part = 1
                self.extra_item_defs.append((key, parent or key, jn, part, key not in takeable, ''))

    def visible(self, o):
        e = self.escape
        if o.name in getattr(e, '_hidden', []):
            return False
        source = getattr(self.source_module, 'SOURCES', {})
        parent = source.get(o.name)
        if o.name == 'key':
            return True
        if parent and parent.startswith('drawer'):
            return e.is_open(self.objects['cabinet'], 'j_drawer' + parent[-1])
        if parent in ('toolbox', 'vent'):
            return e.is_open(self.objects[parent], 'j_panel')
        return True

    def bounds(self, o):
        tri = self.scene.triangles(o.node).reshape(-1, 3)
        return np.array([tri.min(0), tri.max(0)])

    def pose(self, o):
        mat = self.scene.G.XformCache().GetLocalToWorldTransform(o.node['prim'])
        p = np.array(mat.ExtractTranslation())
        M = np.array(mat)[:3, :3].T
        M = M / np.maximum(np.linalg.norm(M, axis=0), 1e-12)
        return (p, Rotation.from_matrix(M).as_quat())

    def set_pose(self, o, pos, q):
        node = o.node
        parent = node['prim'].GetParent()
        mat = self.scene.G.XformCache().GetLocalToWorldTransform(parent)
        kwargs = {}
        if pos is not None:
            kwargs['pos'] = list(mat.GetInverse().Transform(self.scene.F.Vec3d(*map(float, pos))))
        if q is not None:
            M = np.array(mat)[:3, :3].T
            M = M / np.maximum(np.linalg.norm(M, axis=0), 1e-12)
            kwargs['rpy'] = (Rotation.from_matrix(M).inv() * Rotation.from_quat(q)).as_euler('xyz', degrees=True).tolist()
        self.scene.transform(node, **kwargs)

    def reconcile(self):
        e = self.escape
        if e is None:
            return
        g = self.driver.game
        nodes = list(self.scene.drawers.values()) + [self.scene.lid, self.scene.grille, self.scene.door_node]
        poses = [(n, np.array(n['translate'].Get()), np.array(n['rotate'].Get())) for n in nodes]
        for i in range(1, 4):
            g.opened['drawer' + str(i)] = e.is_open(self.objects['cabinet'], 'j_drawer' + str(i))
        for name in ['toolbox', 'vent']:
            g.opened[name] = e.is_open(self.objects[name], 'j_panel')
        g.opened['exit'] = 'exit' in e.passed_doors
        e.items['key']['behind_glass'] = not e.is_open(self.objects['vent'], 'j_panel')
        g.drawer_unlocked = e.part_locks['cabinet', 2]['unlocked']
        g.toolbox_unlocked = e.part_locks['toolbox', 1]['unlocked']
        g.vent_freed = e.part_locks['vent', 1]['unlocked']
        g.exit_unlocked = e.doors['exit']['unlocked']
        g.exited = bool(e.success)
        g.holding = [e.objs[i]['sim'] for i in e.holding]
        g.taken = {st['name'] for st in e.items.values() if st['taken']}
        self.scene.sync(g)
        for n, p, q in poses:
            self.scene.transform(n, p.tolist(), q.tolist())

    def step(self, n=1):
        self.reconcile()
        for _ in range(max(1, int(n))):
            self.driver.og.sim.step()

    def capture(self, path, pos, q):
        self.reconcile()
        R = Rotation.from_quat(q).as_matrix()
        self.driver.raw(pos, np.array(pos) - R[:, 2], warm=8)
        self.driver.clean.save(path)
        self.pos = np.array(pos)
        self.q = np.array(q)

    def detect(self, path, pos, q):
        out, _ = CpuBackend.detect(self, path, np.asarray(pos, float), np.asarray(q, float))
        pos = np.asarray(pos, float)
        R = Rotation.from_quat(q).as_matrix()
        near = 0.02
        guard_geometry = {}
        for obj in self.objects.values():
            if obj.name.startswith('drawer') or not self.visible(obj):
                continue
            lo, hi = obj.aabb
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            corner_depth = -((corners - pos) @ R)[:, 2]
            if not (np.any(corner_depth <= near) and np.any(corner_depth > near)):
                continue
            arrays = [self.scene.triangles(n) for n in getattr(obj, 'nodes', [obj.node])]
            arrays = [a for a in arrays if a.size]
            if not arrays:
                continue
            triangles = np.concatenate(arrays)
            world = triangles.reshape(-1, 3)
            guard_geometry[obj.name] = triangles.copy()
            camera = (triangles - pos) @ R
            distance = -camera[:, :, 2]
            points = [camera[distance >= near]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                da, db = (distance[:, a], distance[:, b])
                crossing = (da >= near) != (db >= near)
                if crossing.any():
                    fraction = ((near - da[crossing]) / (db[crossing] - da[crossing]))[:, None]
                    points.append(camera[crossing, a] + fraction * (camera[crossing, b] - camera[crossing, a]))
            points = np.concatenate(points)
            if not len(points):
                continue
            px = 640 + 640 * points[:, 0] / -points[:, 2]
            py = 360 - 640 * points[:, 1] / -points[:, 2]
            rect = [max(0, int(px.min())), max(0, int(py.min())), min(1279, int(px.max())), min(719, int(py.max()))]
            if rect[0] < rect[2] and rect[1] < rect[3]:
                out.append({'cat': obj.category, 'center': list((world.min(0) + world.max(0)) / 2), 'bbox': rect})
        self._native_detection_snapshot = {'clean': str(path), 'geometry': guard_geometry}
        depth = np.asarray(self.driver.depth, np.float32)
        return (out, np.repeat(np.repeat(depth, 2, 0), 2, 1))

    def photo_metadata(self, boxed):
        snapshot = getattr(self, '_native_detection_snapshot', None)
        if snapshot is None:
            return
        boxed = str(boxed)
        path = Path(boxed)
        clean = str(path.with_name(path.stem + '_clean' + path.suffix))
        if clean != snapshot['clean']:
            raise RuntimeError('Native triangle guard is not from this observation')
        self.escape._photo_dets[boxed]['native_near_geometry'] = copy.deepcopy(snapshot['geometry'])

    def front_mesh_guard(self, esc, C, photo, px, py, oid):
        record = (getattr(esc, '_photo_dets', {}) or {}).get(str(photo), {})
        sim = esc.objs.get(oid, {}).get('sim')
        triangles = (record.get('native_near_geometry') or {}).get(sim)
        if triangles is None:
            return True
        triangles = np.asarray(triangles, float)
        origin, direction, raw = C._ray_at(esc, photo, px, py)
        depth = C._depth_at(esc, photo, px, py)
        if depth is None or not len(triangles):
            return False
        v0 = triangles[:, 0]
        a = triangles[:, 1] - v0
        b = triangles[:, 2] - v0
        cross = np.cross(direction, b)
        det = np.sum(a * cross, axis=1)
        inv = np.divide(1.0, det, out=np.zeros_like(det), where=np.abs(det) > 1e-09)
        relative = origin - v0
        u = np.sum(relative * cross, axis=1) * inv
        q = np.cross(relative, a)
        v = np.sum(q * direction, axis=1) * inv
        t = np.sum(b * q, axis=1) * inv
        hit = (np.abs(det) > 1e-09) & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        if not hit.any():
            return False
        visible = float(depth) * float(np.linalg.norm(raw))
        return bool(np.any(np.abs(t[hit] - visible) <= float(C.FRONT_MARGIN)))

    def install_colliders(self):
        from pxr import Usd, UsdGeom, UsdPhysics
        og = self.driver.og
        stage = og.sim.stage
        if getattr(og.sim, 'psqi', None) is None:
            raise RuntimeError('Live PhysX query service is required; no silent grid fallback')
        count = 0
        with og.sim.editing_usd():
            root = stage.GetPrimAtPath('/World/redesign364')
            for prim in Usd.PrimRange(root):
                if prim.IsA(UsdGeom.Mesh):
                    UsdPhysics.CollisionAPI.Apply(prim).CreateCollisionEnabledAttr(True)
                    UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr('convexHull')
                    count += 1
            for name in ['cabinet', 'toolbox', 'vent', 'exit']:
                for link in self.objects[name].links.values():
                    api = UsdPhysics.RigidBodyAPI.Apply(link.node['prim'])
                    api.CreateKinematicEnabledAttr(True)
                    api.CreateRigidBodyEnabledAttr(True)
        og.sim.play()
        og.sim.update_handles()
        self.step(30)
        return count

class PilotSession:

    def __init__(self, backend, out, working=WORKING, E=None, C=None):
        if E is None:
            E, C = load_stack(working)
        from legacy_rooms_bridge import install_mechanism_hooks
        install_mechanism_hooks(E)
        self.E, self.C, self.backend = (E, C, backend)
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        scene = types.SimpleNamespace(objects=list(backend.objects.values()), object_registry=lambda key, name: backend.objects.get(name))
        ctx = {'env': types.SimpleNamespace(scene=scene), 'E': types.SimpleNamespace(quat_from=quat_from), 'pos': [2.25, 2.25, 1.35], 'shot': backend.capture, 'detect': backend.detect, 'step_sim': backend.step, 'fov_h': lambda: math.pi / 2}
        source = getattr(backend, 'source_module', None)
        note = getattr(source, 'COUNT_NOTE', 'Count coloured balls: RED BLUE YELLOW GREEN.')
        code = getattr(source, 'CODE', '4826')
        drawer_code = getattr(source, 'DRAWER_CODE', '2314')
        item_defs = [('logic_note', 'logic_note', None, 0, True, note), ('paper', 'cabinet', 'j_drawer2', 2, True, code), ('screwdriver', 'toolbox', 'j_panel', 1, False, ''), ('key', 'vent', 'j_panel', 1, False, '')] + list(getattr(backend, 'extra_item_defs', []))
        cfg = {'name': 'legacy_bridge_R01', 'scene': 'programmatic_R01', 'start': {'xy': [2.25, 2.25], 'yaw_deg': 90}, 'max_steps': 150, 'native_use_visual': False, 'native_devices_visual': False, 'items': [{'id': n, 'name': n, 'kind': 'tool' if not fixed else 'paper', 'text': text} for n, parent, jn, part, fixed, text in item_defs], 'part_locks': [{'container': 'cabinet', 'part': 2, 'lock': drawer_code}, {'container': 'toolbox', 'part': 1, 'lock': code}, {'container': 'vent', 'part': 1}], 'doors': [{'name': 'exit', 'key': 'key', 'exit': True}], 'gadgets': [{'name': 'vent_screw_' + str(i), 'type': 'reveal', 'tool': 'screwdriver', 'flag': 'vent_screws_freed'} for i in range(1, 5)]}

        class NativeEscape(E.Escape):

            def _visual_flag_complete(esc, flag, on):
                if flag == 'vent_screws_freed':
                    esc._unlock_parts([['vent', 1]])
                    return True
                return super()._visual_flag_complete(flag, on)
        self.esc = NativeEscape(ctx, cfg, self.out)
        backend.escape = self.esc
        e = self.esc
        for attribute, method in (('_native_photo_metadata_hook', 'photo_metadata'), ('_native_front_mesh_guard', 'front_mesh_guard')):
            hook = getattr(backend, method, None)
            if callable(hook):
                setattr(e, attribute, hook)
        for i, o in enumerate(backend.objects.values(), 1):
            e.objs[i] = {'id': i, 'sim': o.name, 'cat': getattr(source, 'LABELS', {}).get('toolbox', 'metal toolbox') if o.name == 'toolbox' else o.category, 'center': o.aabb.mean(0).tolist()}
            e.by_sim[o.name] = i
        for name, parent, jn, part, fixed, text in item_defs:
            st = {'id': name, 'name': name, 'container': parent, 'joint': jn, 'part': part, 'kind': 'drawer' if name == 'paper' else 'loose', 'taken': False, 'fixed': fixed, 'text': text, 'lockd': None, 'unlocked': True}
            if jn:
                st['rel'] = e._rel(backend.objects[parent].links[jn[2:]], backend.objects[name])
            e.items[name] = st
        e._wallmap = np.zeros((320, 320), bool)
        e._wallmap[160:270, 160:250] = True
        e._door_boxes = {'exit': tuple(backend.objects['exit'].aabb)}
        e._window_boxes = {}
        e._semmap = np.ones((1600, 1600), np.uint8)
        e._roomcats = ['workroom']
        e._fronts.update({name: np.array([0.0, -1.0]) for name in ['cabinet', 'toolbox', 'vent']})
        e.items['key']['behind_glass'] = True
        self.key_to_oid = {name: oid for name, oid in e.by_sim.items()}
        self.key_to_oid.update({key: e.by_sim['cabinet'] for key in ['drawer1', 'drawer2', 'drawer3', 'cabinet_body']})
        self.backend.key_to_sim = {key: e.objs[oid]['sim'] for key, oid in self.key_to_oid.items()}
        self.backend.sim_to_key = {name: name for name in self.backend.objects}
        self.backend.part_aliases = {key: ('cabinet', i) for i, key in enumerate(['drawer1', 'drawer2', 'drawer3'], 1)}
        self.identity = {name: getattr(E.Escape, name) for name in ['act', 'a_open', 'a_close', 'a_take', 'a_unlock', 'a_use']}

    def observe(self, pos, yaw, pitch=0.0):
        e = self.esc
        e.pos = np.array(pos, float)
        e.cam_z = float(pos[2])
        e.yaw = float(yaw)
        e._claw_pitch = float(pitch)
        path, _ = self.C.shoot(e, 'pilot_observe')
        e._claw_photos = [path]
        return path

    def point_for(self, name):
        e = self.esc
        oid = e.by_sim[name]
        box = e._photo_dets[e._claw_photos[-1]]['rects'][oid]
        return [(box[0] + box[2]) / 4, (box[1] + box[3]) / 4]

    def act(self, a):
        e = self.esc
        e.t += 1
        trace = []

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code.co_name in ('engine_act', 'act', '_act_core', '_at_point', '_front_thing', '_layer', '_lock_target', 'a_open', 'a_close', 'a_unlock', 'a_take', 'a_use', '_move', '_body_hits', 'set_joint') and frame.f_code.co_filename.endswith(('_escape_bind_ownedvisual1010.py', '_escape_claw_nativefresh1009.py', 'unified_protocol.py')):
                trace.append([frame.f_code.co_name, frame.f_code.co_filename, frame.f_code.co_firstlineno])
        previous = sys.getprofile()
        sys.setprofile(profile)
        try:
            result = e.act(dict(a))
        finally:
            sys.setprofile(previous)
        e.items['key']['behind_glass'] = not e.is_open(self.backend.objects['vent'], 'j_panel')
        self.last_call_trace = trace
        if not e.turns or e.turns[-1].get('turn') != e.t:
            e.turns.append({'turn': e.t, 'action': dict(a), 'result': dict(result)})
        if isinstance(self.backend, NativeBackend):
            self.backend.reconcile()
        return result

    def notes(self):
        return self.esc.notes()

    def native_gate(self):
        if not self.backend.native:
            raise RuntimeError('CPU fixture cannot pass native gate')
        count = self.backend.install_colliders()
        hits = self.C._body_hits(self.esc, 2.15, 2.9)
        if not hits:
            raise RuntimeError('R01 central table produced no PhysX body hit; colliders are not verified')
        return {'collision_meshes': count, 'physx_obstacle_probe': sorted(hits), 'native_visual_verified': False}

def attach(driver, out, working=WORKING, E=None, C=None):
    session = PilotSession(NativeBackend(driver), out, working, E, C)
    session.native_gate()
    return session

def cpu_test():
    import tempfile
    backend = CpuBackend()
    stub = types.SimpleNamespace(sim=types.SimpleNamespace(is_playing=lambda: False, psqi=types.SimpleNamespace(overlap_sphere=backend.overlap_sphere)))
    original = sys.modules.get('omnigibson')
    sys.modules['omnigibson'] = stub
    utilities = types.ModuleType('omnigibson.utils')
    assets = types.ModuleType('omnigibson.utils.asset_utils')
    assets.get_dataset_path = lambda *a: (_ for _ in ()).throw(RuntimeError('CPU fixture attempted dataset access'))
    prior_utils = sys.modules.get('omnigibson.utils')
    prior_assets = sys.modules.get('omnigibson.utils.asset_utils')
    sys.modules['omnigibson.utils'] = utilities
    sys.modules['omnigibson.utils.asset_utils'] = assets
    try:
        with tempfile.TemporaryDirectory(prefix='cpu_', dir=ROOT) as td:
            s = PilotSession(backend, td)
            s.observe([0.8, 4.0, 1.35], math.pi / 2, -30)
            p = s.point_for('cabinet')
            checks = []

            def ck(name, value):
                assert value, name
                checks.append(name)
            ck('actual inherited a_open', type(s.esc).a_open is s.E.Escape.a_open)
            ck('actual inherited a_take', type(s.esc).a_take is s.E.Escape.a_take)
            ck('missing part rejected', not s.act({'action': 'open', 'point': p, 'target': 'cabinet'})['ok'])
            ck('wrong part rejected', not s.act({'action': 'open', 'point': p, 'target': 'cabinet', 'part': 99})['ok'])
            ck('locked middle drawer rejected', not s.act({'action': 'open', 'point': p, 'target': 'cabinet', 'part': 2})['ok'])
            ck('wrong code rejected', not s.act({'action': 'unlock', 'point': p, 'target': 'cabinet', 'part': 2, 'code': '0000'})['ok'])
            ck('correct code uses old unlock', s.act({'action': 'unlock', 'point': p, 'target': 'cabinet', 'part': 2, 'code': '2314'})['ok'])
            ck('open explicit middle part', s.act({'action': 'open', 'point': p, 'target': 'cabinet', 'part': 2})['ok'])
            trace = s.last_call_trace
            ck('actual E/C dispatch frames present', all((any((x[0] == n for x in trace)) for n in ['_act_core', '_at_point', 'a_open', '_layer', 'set_joint'])))
            ck('actual old joint state open', s.esc.is_open(backend.objects['cabinet'], 'j_drawer2'))
            p = s.point_for('cabinet')
            ck('close explicit middle part', s.act({'action': 'close', 'point': p, 'target': 'cabinet', 'part': 2})['ok'])
            ck('unheld key cannot be used even with a part field', not s.act({'action': 'use', 'point': p, 'target': 'cabinet', 'item': 'key', 'part': 1})['ok'])
            s.observe([0.8, 2.25, 1.35], math.pi / 2, -15)
            far = s.point_for('cabinet')
            ck('old reach denies far cabinet', not s.act({'action': 'open', 'point': far, 'target': 'cabinet', 'part': 1})['ok'])
            s.observe([0.8, 4.0, 1.35], math.pi / 2, -15)
            moved = s.act({'action': 'walk', 'distance': 1.0})
            move_trace = s.last_call_trace
            ck('old movement stops partway at fixture obstacle', bool(moved.get('blocked')) and 0 < float(moved.get('moved', 0)) < 1)
            ck('old PhysX query branch executed against explicit CPU fixture', backend.query_count > 0 and any((x[0] == '_body_hits' for x in move_trace)))
            s.observe([2.8, 4.0, 1.35], math.pi / 2, -30)
            tb = s.point_for('toolbox')
            ck('toolbox wrong code denied', not s.act({'action': 'unlock', 'point': tb, 'target': 'cabinet', 'part': 1, 'code': '1111'})['ok'])
            ck('toolbox correct code accepted', s.act({'action': 'unlock', 'point': tb, 'target': 'cabinet', 'part': 1, 'code': '4826'})['ok'])
            ck('toolbox lid opens through old dispatcher', s.act({'action': 'open', 'point': tb, 'target': 'cabinet', 'part': 1})['ok'])
            driver_point = s.point_for('screwdriver')
            take = s.act({'action': 'take', 'point': driver_point, 'target': 'screwdriver'})
            take_trace = s.last_call_trace
            ck('old a_take stores real legacy inventory id', take['ok'] and s.esc.by_sim['screwdriver'] in s.esc.holding)
            ck('old take call stack executed', any((x[0] == 'a_take' for x in take_trace)))
            ck('taken object hidden by old _hide', 'screwdriver' in s.esc._hidden)
            return {'movement_call_trace': move_trace, 'take_call_trace': take_trace, 'passed': len(checks), 'checks': checks, 'scope': 'CPU fixture geometry and transport; actual legacy functions by reference, not native acceptance', 'call_trace': trace, 'native_visual_verified': False, 'source_files': {str(Path(s.E.__file__)): hashlib.sha256(Path(s.E.__file__).read_bytes()).hexdigest(), str(Path(s.C.__file__)): hashlib.sha256(Path(s.C.__file__).read_bytes()).hexdigest()}}
    finally:
        if original is None:
            sys.modules.pop('omnigibson', None)
        else:
            sys.modules['omnigibson'] = original
        for name, old in [('omnigibson.utils', prior_utils), ('omnigibson.utils.asset_utils', prior_assets)]:
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
if __name__ == '__main__':
    result = cpu_test()
    (ROOT / 'CPU_RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('call_trace')}, ensure_ascii=False))
