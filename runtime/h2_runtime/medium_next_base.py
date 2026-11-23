import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from depth_four import DepthScene
from medium88_scene import MediumScene
from medium88_specs import LEVELS
from action_feedback import failure_for

def make_spec(rid, title, room_names):
    spec = copy.deepcopy(LEVELS[rid])
    spec.update(title=title, room_names=list(room_names), start=[2.5, 1.25, 1.35], start_yaw=90, depth_revision='physical_next_v1', clues={'A': {}, 'B': {}}, room_views={'A': [1.5, 3.75, 1.35], 'B': [6.25, 3.75, 1.35]}, last={'A': 1, 'B': 2}, stages=[{'kind': 'float_key', 'room': r, 'name': n} for r, n in zip(['A', 'A', 'B'], ['first mechanism', 'second mechanism', 'third mechanism'])])
    return spec

def _stage_view_grid(spec):
    positions = {'A': ((1.5, 3.75), (1.25, 2.75)), 'B': ((6.25, 3.75), (8.25, 3.5))}
    counts = {'A': 0, 'B': 0}
    views = []
    for stage in spec['stages']:
        room = stage['room']
        index = counts[room]
        if index >= len(positions[room]):
            raise ValueError('Only two native workstation positions per room: ' + room)
        views.append(list(positions[room][index]))
        counts[room] += 1
    return views

class PhysicalGame:
    LABELS = {'exit': 'exit door', 'exit_lock': 'exit code keypad'}
    TEXTS = {}

    def __init__(self):
        self.states = [{}, {}, {}]
        self.solved = [False] * 3
        self.reward_open = [False] * 3
        self.opened = {'exit': False, 's1_cover': True, 's2_cover': True, 's3_cover': True}
        self.holding = []
        self.taken = set()
        self.possessions = {}
        self.exit_unlocked = False
        self.exited = False

    def snapshot(self):
        return {'states': copy.deepcopy(self.states), 'solved': list(self.solved), 'reward_open': list(self.reward_open), 'opened': dict(self.opened), 'holding': list(self.holding), 'taken': sorted(self.taken), 'possessions': copy.deepcopy(self.possessions), 'exit_unlocked': self.exit_unlocked, 'exited': self.exited}

    def _resolve_item(self, value):
        value = str(value).strip().casefold()
        return next((key for key in self.holding if value in (key.casefold(), str(self.LABELS.get(key, key)).casefold())), None)

    def stage_accessible(self, i):
        return 0 <= i < 3

    def available(self, key):
        return False

    def readable(self, key):
        return key in self.TEXTS

    def read_text(self, key):
        value = self.TEXTS.get(key, '')
        return '\n'.join(map(str, value)) if isinstance(value, (list, tuple)) else str(value)

    def give(self, key):
        if key in self.taken or key in self.holding:
            return False
        self.taken.add(key)
        self.holding.append(key)
        return True

    def consume(self, key):
        if key not in self.holding:
            return False
        self.holding.remove(key)
        self.taken.add(key)
        return True

    def return_item(self, key):
        self.taken.discard(key)
        if key in self.holding:
            self.holding.remove(key)
        return True

    def recompute(self):
        pass

    def interact(self, key, verb, item, a):
        return False

    def act(self, a):
        verb, key = (a.get('action'), a.get('_hit364', ''))
        if not a.get('_validated364'):
            return {'ok': False, 'text': failure_for(verb)}
        result = False
        if key in ('exit', 'exit_lock'):
            if verb == 'unlock':
                self.possessions['door_input'] = str(a.get('code', ''))
                self.exit_unlocked = self.possessions['door_input'] == str(self.SPEC['door_code'])
                result = self.exit_unlocked
            elif verb == 'close' or (verb == 'open' and self.exit_unlocked):
                self.opened['exit'] = verb == 'open'
                self.exited = self.opened['exit'] and self.exit_unlocked
                result = True
        elif verb == 'read' and self.readable(key):
            result = {'ok': True, 'text': self.read_text(key)}
        elif verb == 'take' and self.available(key) and (key not in self.taken):
            result = self.give(key)
        else:
            result = self.interact(key, verb, self._resolve_item(a.get('item', '')), a)
        if isinstance(result, dict):
            ok, message = (bool(result.get('ok')), str(result.get('text', '')))
        else:
            ok, message = (bool(result), '')
        if ok:
            self.recompute()
            self.reward_open = list(self.solved)
        return {'ok': ok, 'text': message if ok and verb == 'read' else '' if ok else failure_for(verb)}

class PhysicalScene(DepthScene):
    LABELS = {}

    def __init__(self, og, run, spec):
        super().__init__(og, run, spec)
        self.labels = {'exit': 'exit door', 'exit_lock': 'exit code keypad'}
        self.labels.update(self.LABELS)
        self._physical_hidden = set()

    def _physical_asset_key(self, im, size=None):
        pixels = im.convert('RGBA')
        header = repr((pixels.mode, pixels.size, size)).encode('utf-8')
        return hashlib.sha256(header + b'\x00' + pixels.tobytes()).hexdigest()

    def _physical_asset(self, im, size=None):
        path = self.tex / ('a_' + self._physical_asset_key(im, size)[:32] + '.png')
        if not path.exists():
            im.save(path)
        return path

    def face(self, key, parent, pos, w, h, im):
        p = self._physical_asset(im, (w, h))
        mat = self.image_mat('physical_face_' + p.stem, p)
        self.plane(key, pos, w, h, (1, 0, 0), (0, 0, 1), None, parent, material=mat)
        return mat

    def show_image(self, key, parent, pos, w, h, im):
        if len(key) > 2 and key[0] == 's' and key[1].isdigit() and key.endswith(('_reference', '_evidence')):
            i = int(key[1]) - 1
            stage = self.spec['stages'][i]
            if key == f's{i + 1}_reference' and stage.get('visual', {}).get('type') == 'wire_trace':
                pos, w, h = ([0.12, -0.035, 1.425], 0.92, 0.34)
            elif key == f's{i + 1}_reference':
                pos, w, h = ([0, 0.27, 1.47], 1.1, 0.34)
            elif key == f's{i + 1}_evidence':
                pos, w, h = ([0, 0.27, 1.43], 1.1, 0.38)
        if key.endswith(('_reference', '_evidence', '_complete_reference', '_goal')) and any((parent is root for root in self.roots)):
            self.box(key + '_physical_backing', [pos[0], pos[1] + 0.012, pos[2]], [w + 0.025, 0.022, h + 0.025], 'ivory', parent)
        p = self._physical_asset(im, (w, h))
        mat = self.image_mat('physical_image_' + p.stem, p)
        return self.plane(key, pos, w, h, (1, 0, 0), (0, 0, 1), None, parent, material=mat)

    def screen(self, key, parent, pos, w, h, im, sig):
        identity = (self._physical_asset_key(im, (w, h)), tuple(pos), w, h, id(parent))
        cache = self.__dict__.setdefault('_physical_screen_assets', {})
        if key in self.images and self.image_sig.get(key) == sig and (cache.get(key) == identity):
            return
        self.image_sig[key] = object()
        super().screen(key, parent, pos, w, h, im, sig)
        cache[key] = identity

    def button(self, key, parent, pos, symbol='circle', size=0.14):
        node = super().button(key, parent, pos, symbol, size)
        handle = self.custom.get('handle_' + key)
        if handle is not None:
            self.__dict__.setdefault('_generic_button_pairs', {})[key] = (node, handle)
        return node

    @staticmethod
    def _button_pose(handle):
        return tuple((tuple((float(v) for v in handle[name].Get())) for name in ('translate', 'rotate')))

    def _button_response_candidate(self, d):
        if (getattr(d, 'current_action', None) or {}).get('action') != 'press' or not (getattr(d, 'current_result', None) or {}).get('ok'):
            return None
        key = (getattr(d, 'current_hit', None) or {}).get('key', '')
        if any((word in key.casefold() for word in ('pump', 'wheel', 'crank'))):
            return None
        pair = self.__dict__.get('_generic_button_pairs', {}).get(key)
        if pair is None or self.target_nodes.get(key) is not pair[0] or self.custom.get('handle_' + key) is not pair[1]:
            return None
        if getattr(d, 'current_visual_feedback', ()):
            return None
        step = getattr(d, 'step', None)
        if step is not None and any((row.get('step') == step for name in ('timeline', 'capture_rows') for row in getattr(d, name, ()))):
            return None
        if not callable(getattr(d, 'capture_feedback_frame', None)):
            return None
        return (key, pair, self._button_pose(pair[1]))

    def _button_response(self, d, candidate):
        if candidate is None:
            return
        key, (node, handle), old_pose = candidate
        if self.target_nodes.get(key) is not node or self.custom.get('handle_' + key) is not handle:
            return
        pose = self._button_pose(handle)
        if not all((abs(a - b) < 1e-07 for aa, bb in zip(old_pose, pose) for a, b in zip(aa, bb))):
            return
        position, rest = pose
        pressed = list(rest)
        pressed[1] += -12 if rest[1] > 0 else 12
        try:
            for phase, rotation in enumerate((rest, pressed, rest)):
                self.transform(handle, pos=position, rpy=rotation)
                if phase:
                    d.frame(warm=4)
                    d.capture_feedback_frame()
                    d.append('Control handle depresses and springs back', 4)
        finally:
            self.transform(handle, pos=position, rpy=rest)

    def controls_for(self, i, s, root):
        pass

    def core_card(self, i, root, reward):
        self.core_cards.append(None)

    def apply_visuals(self, g):
        pass

    def build(self, g):
        MediumScene.build(self, g)
        self.stage_views = _stage_view_grid(self.spec)
        for key in self.target_nodes:
            if key.startswith('s') and key[1:2].isdigit():
                index = int(key[1]) - 1
                if index < len(self.stage_views):
                    self.views[key] = self.stage_views[index]
        self.door_view = [8.25, 1.25]
        self.views['exit'] = list(self.door_view)
        self.views['exit_lock'] = list(self.door_view)
        self.labels.update(g.LABELS)
        if 'light_frame' in self.extra:
            self.visibility(self.extra['light_frame'], False)
            self.target_nodes.pop('light_frame', None)
            self._physical_hidden.add('light_frame')
        assert self.door_lock['prim'].GetParent().GetPath() == self.exit_node['prim'].GetPath()
        self.label('attached_exit_code_label', 'EXIT CODE', [0, -0.034, 0.094], 0.18, 0.023, parent=self.door_lock)
        for j, value in enumerate('123456789*0#'):
            r, c = divmod(j, 3)
            self.box('keypad_key', [(c - 1) * 0.06, -0.036, -0.005 - r * 0.025], [0.035, 0.01, 0.018], 'cream', self.door_lock)
            self.label('keypad_digit_' + str(j), value, [(c - 1) * 0.06, -0.042, -0.005 - r * 0.025], 0.027, 0.016, parent=self.door_lock)
        self.reg('exit', {'meshes': [n for n in self.exit_node['meshes'] if n is not self.door_lock]})
        self.sync(g)

    def read_board(self, key, parent, pos, lines, w=1.65, h=0.34):
        return self.textboard(key, parent, pos, lines.splitlines() if isinstance(lines, str) else lines, w, h)

    def tool(self, key, parent, pos, kind=None):
        kind = kind or key
        known = {'wrench', 'rod', 'hook', 'pawl_tool', 'meter', 'wire', 'rubber', 'clamp', 'blockP', 'blockQ', 'band', 'cutters'}
        if kind in known:
            old_prop = self.props.get(kind)
            old_target = self.target_nodes.get(kind)
            node = DepthScene.physical_tool(self, kind, parent, pos, kind)
            if key != kind:
                if old_prop is None:
                    self.props.pop(kind, None)
                else:
                    self.props[kind] = old_prop
                if old_target is None:
                    self.target_nodes.pop(kind, None)
                else:
                    self.target_nodes[kind] = old_target
                self.props[key] = node
                self.reg(key, node)
            return node
        node = self.group(key, pos, parent)
        if kind in ('hammer', 'mallet'):
            self.box('wooden_handle', [0, 0, 0], [0.028, 0.035, 0.25], 'wood', node)
            self.box('hammer_head', [0, 0, 0.13], [0.17, 0.065, 0.065], 'steel', node)
        elif kind in ('screwdriver', 'awl'):
            self.cylinder('grip', [0, 0, -0.06], 0.03, 0.14, 'wood', 'z', node)
            self.cylinder('shaft', [0, 0, 0.075], 0.009, 0.15, 'steel', 'z', node)
            self.box('flat_tip', [0, 0, 0.15], [0.025, 0.007, 0.02], 'steel', node)
        elif kind in ('paper', 'card', 'sheet', 'label', 'film'):
            self.box('flat_sheet', [0, 0, 0], [0.2, 0.008, 0.15], 'cream', node)
        elif kind in ('rope', 'cord', 'belt', 'strap'):
            for x in (-0.065, 0.065):
                self.tube('loose_loop', [x, 0, -0.09], [x, 0, 0.09], 0.01, 'rubber', node)
            for z in (-0.09, 0.09):
                self.tube('loop_end', [-0.065, 0, z], [0.065, 0, z], 0.01, 'rubber', node)
        else:
            self.box('handled_component', [0, 0, 0], [0.12, 0.055, 0.12], 'brass', node)
            self.box('component_grip', [0, 0, -0.1], [0.035, 0.04, 0.12], 'wood', node)
        self.props[key] = node
        self.reg(key, node)
        return node

    def case(self, i, root, key='s2_open', width=0.7):
        return self.smallcase(i, root, key, width)

    def status(self, key, parent, pos, value, w=0.3, h=0.09):
        self.screen(key, parent, pos, w, h, self.small_text(value), repr(value))
        return self.images[key]

    def sync(self, g):
        self._dynamic_collision_cache = None
        for i, (off, on) in enumerate(self.status_nodes):
            self.visibility(off, not g.solved[i])
            self.visibility(on, g.solved[i])
        for key, node in self.props.items():
            self.visibility(node, key not in g.holding)
        self.apply_visuals(g)
        if hasattr(self, 'exit_node'):
            self.transform(self.exit_node, rpy=[0, 0, 90 + (100 if g.opened['exit'] else 0)])
        if hasattr(self, 'door_lock'):
            value = g.possessions.get('door_input', '____')
            self.screen('exit_lcd', self.door_lock, [0, -0.034, 0.045], 0.205, 0.04, self.small_text(value), value)
        self.centres = {}
        for key, node in self.target_nodes.items():
            points = self.triangles(node).reshape(-1, 3)
            if points.size:
                self.centres[key] = ((points.min(0) + points.max(0)) / 2).tolist()

    def _node_visible(self, node):
        prim = node.get('prim')
        if prim is not None and self.G.Imageable(prim).ComputeVisibility() == 'invisible':
            return False
        if 'points' in node:
            return True
        return any((self._node_visible(child) for child in node.get('meshes', [])))

    def target_enabled(self, key, g):
        return key not in self._physical_hidden and key not in g.holding and (key in self.target_nodes) and self._node_visible(self.target_nodes[key])

    def visible(self, key, g):
        return self.target_enabled(key, g)

    def candidates(self, g):
        return self.base_candidates([key for key in self.target_nodes if self.visible(key, g)])

    def animate(self, d, before):
        response = self._button_response_candidate(d)
        after = d.game.snapshot()
        if before == after:
            if response is not None:
                self.sync(d.game)
                self._button_response(d, response)
            return
        if before['opened']['exit'] != after['opened']['exit']:
            start = 100 if before['opened']['exit'] else 0
            end = 100 if after['opened']['exit'] else 0
            poses = []
            for fraction in (0, 0.2, 0.4, 0.6, 0.8, 1):
                self.sync(d.game)
                self.transform(self.exit_node, rpy=[0, 0, 90 + start + (end - start) * fraction])
                cache = self.G.XformCache()
                door = cache.GetLocalToWorldTransform(self.exit_node['prim'])
                lock = cache.GetLocalToWorldTransform(self.door_lock['prim'])
                local = list(door.GetInverse().Transform(lock.ExtractTranslation()))
                assert max((abs(float(x) - y) for x, y in zip(local, [0.84, 0.075, 1.5]))) < 1e-06
                poses.append({'fraction': fraction, 'door_local_position': local, 'world_position': list(lock.ExtractTranslation())})
                d.frame(warm=4)
                d.append('Door and attached keypad move together', 4)
            if hasattr(d, 'save'):
                d.save('DOOR_ATTACHMENT_' + ('open' if after['opened']['exit'] else 'close') + '.json', {'fixed_local_pose_verified': True, 'poses': poses})
        self.sync(d.game)
        self._button_response(d, response)
        d.frame(warm=8)
        d.append('Observe the physical result', 8)

def standard_go(d, i, point=(0, -0.08, 1.18)):
    d.route(d.scene.stage_views[i])
    d.aim(d.scene.world(i, list(point)), 'Observe the mechanism and its real parts')

def standard_click(d, key, verb='press', item=None, **kw):
    return d.click(key, verb, item=item, **kw)

def observe_clue(d, name):
    if not hasattr(d, 'run'):
        return
    path = Path(d.run) / 'screenshots' / ('clue_' + str(name) + '_native.png')
    path.parent.mkdir(parents=True, exist_ok=True)
    d.clean.save(path)
    observations = getattr(d, 'cross_room_observations', [])
    observations.append({'name': 'clue_' + str(name), 'path': str(path), 'step': d.step, 'native': True})
    d.cross_room_observations = observations
    d.save('CROSS_ROOM_OBSERVATIONS.json', observations)

def finish_exit(d, code=None):
    d.route(d.scene.door_view)
    d.aim(d.scene.centres['exit_lock'])
    standard_click(d, 'exit_lock', 'unlock', code=d.game.SPEC['door_code'] if code is None else code)
    standard_click(d, 'exit', 'open')

def exit_test(pos, g):
    return bool(g.exited and g.opened['exit'] and g.exit_unlocked)
