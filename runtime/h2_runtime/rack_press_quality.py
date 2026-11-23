import math

class RackGameMixin:
    RACK_SOLVED_STAGE = 0
    RACK_TARGET = (0, 1, 2, 3)
    RACK_CHECK_ENABLED = True

    def __init__(self):
        super().__init__()
        self.states[0].update(quality_check_presses=0, quality_reset_presses=0, quality_rack_released=False)

    def _whole(self):
        super()._whole()
        if self.RACK_CHECK_ENABLED:
            released = bool(self.states[0].get('quality_rack_released', False))
            self.solved[self.RACK_SOLVED_STAGE] = released
            self.reward_open[self.RACK_SOLVED_STAGE] = released

    def act(self, a):
        if a.get('_validated364') and a.get('action') == 'press':
            key = a.get('_hit364')
            if key == 's1_check' and self.RACK_CHECK_ENABLED:
                state = self.states[0]
                state['quality_check_presses'] += 1
                if tuple((state['assignment'].get(i) for i in range(4))) == self.RACK_TARGET:
                    state['quality_rack_released'] = True
                self._whole()
                return {'ok': True, 'text': ''}
            if key == 's1_reset':
                self.states[0]['quality_reset_presses'] += 1
        return super().act(a)

class RackSceneMixin:
    RACK_CHECK_ENABLED = True

    def controls_for(self, i, s, root):
        super().controls_for(i, s, root)
        if i != 0 or not self.RACK_CHECK_ENABLED:
            return
        self.label('quality_check_legend', 'CHECK', [0, -0.04, 0], 0.11, 0.028, parent=self.target_nodes['s1_check'])
        self.label('quality_reset_legend', 'RESET', [0, -0.04, 0], 0.11, 0.028, parent=self.target_nodes['s1_reset'])
        if self.spec['id'] == 'R23':
            base = [0, -0.225, 1.205]
            lock = self.group('quality_tool_lock_bar', base, root)
            self.tube('tool_box_retaining_bar', [-0.72, 0, 0], [0.72, 0, 0], 0.012, 'steel', lock)
            for x in (-0.75, 0.75):
                self.box('grounded_bar_guide', [x, -0.16, 1.13625], [0.035, 0.075, 0.6875], 'iron', root)
                self.box('bar_slide_foot', [x, -0.16, 0.8125], [0.12, 0.16, 0.04], 'steel', root)
                self.tube('bar_sliding_shoe', [x, 0.065, -0.035], [x, 0, 0], 0.018, 'brass', lock)
            self.custom['quality_lock_axis'] = 'z'
            self.custom['quality_lock_travel'] = 0.25
            self.tube('check_to_bar_vertical', [0.67, -0.17, 0.8], [0.67, -0.17, 1.185], 0.008, 'steel', root)
            self.tube('sliding_check_link', [0.67, 0.055, -0.5], [0.67, 0.055, -0.02], 0.006, 'steel', lock)
            self.tube('check_link_bar_elbow', [0.67, 0.055, -0.02], [0.67, 0, 0], 0.006, 'steel', lock)
        else:
            base = [0.54, -0.362, 0.59]
            self.box('jug_bolt_side_support', [0.585, -0.27, 0.52], [0.055, 0.1, 0.44], 'iron', root)
            self.box('jug_bolt_fixed_housing', [0.585, -0.33, 0.59], [0.07, 0.055, 0.065], 'iron', root)
            lock = self.group('quality_jug_cabinet_bolt', base, root)
            self.cylinder('solid_jug_slide_bolt', [0, 0, 0], 0.012, 0.15, 'steel', 'x', lock)
            self.cylinder('jug_bolt_stop', [0.075, 0, 0], 0.02, 0.02, 'brass', 'x', lock)
            self.custom['quality_lock_axis'] = 'x'
            self.custom['quality_lock_travel'] = 0.13
            self.tube('check_link_horizontal', [0.67, -0.17, 0.8], [0.6, -0.17, 0.8], 0.008, 'steel', root)
            self.tube('check_link_elbow', [0.6, -0.17, 0.8], [0.6, -0.32, 0.8], 0.008, 'steel', root)
            self.tube('check_link_to_jug_bolt', [0.6, -0.32, 0.8], [0.6, -0.32, 0.62], 0.008, 'steel', root)
        self.custom['quality_rack_lock'] = lock
        self.custom['quality_lock_base'] = base

    def _quality_lock_pose(self, fraction):
        if 'quality_rack_lock' not in self.custom:
            return
        position = list(self.custom['quality_lock_base'])
        index = 2 if self.custom['quality_lock_axis'] == 'z' else 0
        position[index] += self.custom['quality_lock_travel'] * fraction
        self.transform(self.custom['quality_rack_lock'], position)

    def sync(self, g):
        super().sync(g)
        if 'handle_s1_reset' in self.custom:
            self.transform(self.custom['handle_s1_reset'], rpy=[0, -35, 0])
        if self.RACK_CHECK_ENABLED:
            released = bool(g.states[0].get('quality_rack_released'))
            if 'handle_s1_check' in self.custom:
                self.transform(self.custom['handle_s1_check'], rpy=[0, 35 if released else -35, 0])
            self._quality_lock_pose(1 if released else 0)
        for key in ('s1_check', 's1_reset'):
            if key in self.target_nodes:
                points = self.triangles(self.target_nodes[key]).reshape(-1, 3)
                if points.size:
                    self.centres[key] = ((points.min(0) + points.max(0)) / 2).tolist()

    def animate(self, d, before):
        key = (d.current_hit or {}).get('key')
        old, now = (before['states'][0], d.game.states[0])
        reset = key == 's1_reset' and now['quality_reset_presses'] != old.get('quality_reset_presses', 0)
        check = self.RACK_CHECK_ENABLED and key == 's1_check' and (now['quality_check_presses'] != old.get('quality_check_presses', 0))
        if not reset and (not check):
            return super().animate(d, before)
        release_field = 'quality_rack_released' if self.RACK_CHECK_ENABLED else 'latch_released'
        was = bool(old.get(release_field))
        released = bool(now.get(release_field))
        rows = []
        for j, fraction in enumerate((0, 0.2, 0.4, 0.6, 0.8, 1)):
            self.sync(d.game)
            if reset:
                angle = -35 + 70 * math.sin(math.pi * fraction)
                self.transform(self.custom['handle_s1_reset'], rpy=[0, angle, 0])
                for item in range(4):
                    k = 's1_item_' + str(item)
                    slot = next((z for z, value in old['assignment'].items() if value == item), None)
                    if slot is None or k not in self.props:
                        continue
                    start = self.custom['slot' + str(slot)]
                    rid = self.spec['id']
                    height = 0.91 if rid == 'R23' else 0.875 if rid == 'R24' else [0.885, 0.925, 0.895, 0.885][item]
                    finish = [(1.5 - item) * 0.37, -0.1, height]
                    self.transform(self.props[k], [a + (b - a) * fraction for a, b in zip(start, finish)])
                lock_fraction = 1 if released else 0
            else:
                angle = 35 + 15 * math.sin(math.pi * fraction) if was else -35 + 70 * fraction if released else -35 + 50 * math.sin(math.pi * fraction)
                lock_fraction = 1 if was else fraction if released else 0
                self.transform(self.custom['handle_s1_check'], rpy=[0, angle, 0])
                self._quality_lock_pose(lock_fraction)
            d.frame(warm=4)
            d.append('RESET returns rack pieces; acquired tools stay held' if reset else 'CHECK moves the actual retaining mechanism; only a complete correct rack releases it', 6)
            if j in (2, 5):
                d.capture_feedback_frame()
            rows.append({'fraction': fraction, 'handle_angle_degrees': angle, 'lock_fraction': lock_fraction})
        d.save('RACK_QUALITY_' + ('RESET' if reset else 'CHECK') + '.json', {'poses': rows, 'before_released': was, 'after_released': released, 'feedback_frames': 2, 'physical_action_only': True})
        self.sync(d.game)
        d.frame(warm=4)

def rack_feedback_standard(previous, check_enabled=True):

    def standard(d):
        if d.game.SPEC['id'] != 'R25':
            return previous(d)
        original = d.click

        def click(key, kind='read', item=None, **fields):
            if key == 's1_check' and kind == 'press':
                d.aim(d.scene.world(0, [0.3, -0.28, 0.74]), 'Observe the CHECK handle and the actual jug-cabinet bolt together')
            return original(key, kind, item=item, **fields)
        d.click = click
        try:
            return previous(d)
        finally:
            d.click = original
    return standard

class WheelFeedbackSceneMixin:

    def button(self, key, parent, pos, symbol='circle', size=0.14):
        if key != 's2_wheel_reverse':
            return super().button(key, parent, pos, symbol, size)
        from depth_four import DepthScene
        old_target = self.target_nodes.get('s2_wheel')
        old_handle = self.custom.get('handle_s2_wheel')
        node = DepthScene.button(self, 's2_wheel', parent, pos, symbol, size)
        reverse_handle = self.custom['handle_s2_wheel']
        if old_target is None:
            self.target_nodes.pop('s2_wheel', None)
        else:
            self.target_nodes['s2_wheel'] = old_target
        if old_handle is None:
            self.custom.pop('handle_s2_wheel', None)
        else:
            self.custom['handle_s2_wheel'] = old_handle
        self.custom['handle_s2_wheel_reverse'] = reverse_handle
        self.reg(key, node)
        return node

    def animate(self, d, before):
        key = (d.current_hit or {}).get('key')
        if key not in ('s2_wheel', 's2_wheel_reverse') or (d.current_action or {}).get('action') != 'press':
            return super().animate(d, before)
        state = d.game.states[1]
        base = (45 if state.get('wheel_direction') == 1 else -35) if key.endswith('reverse') else 35 if state['slack'] else -35
        direction = -1 if key.endswith('reverse') else 1
        rows = []
        for j, fraction in enumerate((0, 0.2, 0.4, 0.6, 0.8, 1)):
            self.sync(d.game)
            angle = base + direction * 360 * fraction
            self.transform(self.custom['handle_' + key], rpy=[0, angle, 0])
            d.frame(warm=4)
            d.append('The wind/unwind crank turns; the rope responds only to its real support and routing', 6)
            if j in (2, 5):
                d.capture_feedback_frame()
            rows.append({'fraction': fraction, 'angle_degrees': angle})
        d.save('WHEEL_QUALITY_' + key + '.json', {'poses': rows, 'direction': direction, 'feedback_frames': 2, 'rule_state_unchanged_by_animation': True})
        self.sync(d.game)
        d.frame(warm=4)

class ReadingCabinetSceneMixin:
    READING_RECORD_POS = (1.45, -0.32, 1.3)
    READING_GATE_POS = (1.45, -0.36, 1.3)

    def gate(self, key, parent, pos, w=0.6, h=0.5):
        if key == 's3_open':
            pos = list(self.READING_GATE_POS)
            w, h = (0.82, 0.56)
        return super().gate(key, parent, pos, w, h)

    def core_card(self, i, root, reward):
        super().core_card(i, root, reward)
        if i != 2:
            return
        self.transform(self.custom['clue_B'], list(self.READING_RECORD_POS))
        for node in root['meshes']:
            if node.get('prim') and node['prim'].GetName().startswith('record_mount'):
                self.visibility(node, False)
        cabinet = self.group('quality_standing_reading_cabinet', [1.45, -0.15, 1.3], root)
        self.box('reading_cabinet_back', [0, 0.12, 0], [0.82, 0.035, 0.56], 'wood', cabinet)
        for x in (-0.4, 0.4):
            self.box('reading_cabinet_side', [x, 0, 0], [0.025, 0.3, 0.56], 'paint', cabinet)
        for z in (-0.28, 0.28):
            self.box('reading_cabinet_shelf', [0, 0, z], [0.82, 0.3, 0.025], 'wood', cabinet)
        for x in (1.1, 1.8):
            self.box('grounded_reading_cabinet_leg', [x, -0.1, 0.50375], [0.055, 0.14, 1.0075], 'iron', root)
        self.label('quality_reading_cabinet_identity', 'ROOM B / READING CABINET', [1.45, -0.305, 1.6], 0.8, 0.07, parent=root)
        self.custom['quality_reading_cabinet'] = cabinet
        points = self.triangles(cabinet).reshape(-1, 3)
        lo, hi = (points.min(0), points.max(0))
        self.add_obstacle(lo[0], lo[1] - 0.08, hi[0], hi[1])

    def sync(self, g):
        super().sync(g)
        if 'clue_B' in self.custom:
            self.transform(self.custom['clue_B'], list(self.READING_RECORD_POS))
        for key in ('clue_B', 's3_open'):
            if key in self.target_nodes:
                points = self.triangles(self.target_nodes[key]).reshape(-1, 3)
                if points.size:
                    self.centres[key] = ((points.min(0) + points.max(0)) / 2).tolist()

def reading_cabinet_standard(previous):

    def standard(d):
        original_click, original_route, original_aim = (d.click, d.route, d.aim)

        def route(destination, *args, **kwargs):
            if list(destination) == [6.25, 3.5] and d.game.states[2].get('open'):
                destination = [7.75, 3.5]
            return original_route(destination, *args, **kwargs)

        def aim(target, *args, **kwargs):
            legacy = d.scene.world(2, [0, -0.32, 0.51])
            if len(target) == len(legacy) and all((abs(float(a) - float(b)) < 1e-05 for a, b in zip(target, legacy))):
                target = d.scene.world(2, list(d.scene.READING_RECORD_POS))
            return original_aim(target, *args, **kwargs)

        def click(key, kind='read', item=None, **fields):
            if key in ('s3_open', 'clue_B'):
                original_route([7.75, 3.5])
                original_aim(d.scene.centres[key])
            return original_click(key, kind, item=item, **fields)
        d.click, d.route, d.aim = (click, route, aim)
        try:
            return previous(d)
        finally:
            d.click, d.route, d.aim = (original_click, original_route, original_aim)
    return standard

class R34RuleLegibilitySceneMixin:
    PAWL_RULE_LINES = ('The pawl stays latched without power.', 'Support the FIXED post to unload its rope; then push the pawl.', 'A fixed support carries the load; a sliding guide follows it.', 'WIND tightens. UNWIND releases only a supported rope.')

    def textboard(self, key, parent, pos, lines, w=1.65, h=0.34):
        if key == 'rope_rule':
            return self.custom['quality_s2_rule_board']
        if key == 's2_note':
            pos, lines, w, h = ([0, 0.1, 1.72], list(self.PAWL_RULE_LINES), 1.65, 0.4)
            for x in (-0.79, 0.79):
                self.box('quality_rule_grounded_foot', [x, 0.13, 0.8125], [0.08, 0.12, 0.04], 'iron', parent)
                self.box('quality_rule_stanchion', [x, 0.13, 1.34625], [0.025, 0.04, 1.1075], 'iron', parent)
            node = super().textboard(key, parent, pos, lines, w, h)
            self.custom['quality_s2_rule_board'] = node
            return node
        return super().textboard(key, parent, pos, lines, w, h)

    def label(self, key, text, center, width, height, right=(1, 0, 0), up=(0, 0, 1), parent=None):
        center = list(center)
        if key == 'wind_label':
            center[2] = 0.835
            self.box('quality_wind_tag_mount', [center[0], -0.18, 0.835], [0.045, 0.045, 0.055], 'iron', parent)
            self.box('quality_wind_tag_back', [center[0], -0.192, 0.835], [width + 0.015, 0.016, height + 0.012], 'cream', parent)
            center[1] = -0.202
        elif key.startswith('guide_label') and key[-1:] in ('0', '1'):
            guide = self.custom['rope_guide' + key[-1]]
            self.tube('guide_tag_bracket', [0, 0.035, -0.06], [0, -0.035, -0.105], 0.008, 'iron', guide)
            self.box('guide_tag_back', [0, -0.035, -0.105], [width + 0.015, 0.025, height + 0.012], 'cream', guide)
            return super().label(key, text, [0, -0.05, -0.105], width, height, right, up, guide)
        elif key.startswith('output_label') and key[-1:] in ('0', '1'):
            center = [center[0], 0.017, 1.36]
            self.box('output_tag_support', [center[0], 0.05, 1.39], [0.035, 0.035, 0.12], 'iron', parent)
            self.box('output_tag_back', [center[0], 0.031, 1.36], [width + 0.015, 0.025, height + 0.012], 'cream', parent)
        return super().label(key, text, center, width, height, right, up, parent)

def r34_rule_legibility_standard(previous):

    def standard(d):
        original = d.click

        def click(key, kind='read', item=None, **fields):
            if key == 's2_note' and kind == 'read':
                d.route([1.5, 2.75])
                d.aim(d.scene.centres[key], 'Read the single complete pawl/rope rule board')
            return original(key, kind, item=item, **fields)
        d.click = click
        try:
            return previous(d)
        finally:
            d.click = original
    return standard

class ReadingReleaseSceneMixin:
    RELEASE_PIN_BASE = (1.45, -0.383, 1.02)
    RELEASE_PIN_TRAVEL = 0.1

    def core_card(self, i, root, reward):
        super().core_card(i, root, reward)
        if i != 2 or 'quality_record_release_pin' in self.custom:
            return
        rid = self.spec['id']
        socket = {'R24': [0.79, -0.025, 1.23], 'R25': [0.79, 0.02, 1.02], 'R34': [0.755, -0.155, 1.25]}[rid]
        self.cylinder('output_release_socket', socket, 0.018, 0.04, 'brass', 'x', root)
        start = [socket[0] + 0.02, socket[1], socket[2]]
        path = [start, [1.025, socket[1], socket[2]], [1.025, -0.27, socket[2]], [1.025, -0.27, 1.0], [1.025, -0.335, 1.0], [1.45, -0.335, 1.0]]
        cable = self.group('quality_reading_release_bowden', parent=root)
        for a, b in zip(path, path[1:]):
            if sum(((x - y) ** 2 for x, y in zip(a, b))) > 1e-12:
                self.tube('fixed_edge_bowden_sheath', a, b, 0.008, 'rubber', cable)
        self.box('release_source_cable_clip', [socket[0] - 0.012, socket[1], socket[2]], [0.025, 0.04, 0.04], 'steel', root)
        self.box('release_left_stile_clip', [1.04, -0.27, socket[2]], [0.04, 0.045, 0.035], 'steel', root)
        self.box('release_lower_corner_clip', [1.04, -0.315, 1.0], [0.045, 0.04, 0.03], 'steel', root)
        self.box('release_bottom_rail_clip', [1.25, -0.315, 1.0], [0.035, 0.04, 0.03], 'steel', root)
        housing = self.box('fixed_reading_latch_housing', [1.45, -0.345, 0.98], [0.1, 0.1, 0.07], 'iron', root)
        points = self.triangles(housing).reshape(-1, 3)
        lo, hi = (points.min(0), points.max(0))
        self.add_obstacle(lo[0], lo[1], hi[0], hi[1])
        self.cylinder('bowden_frame_socket', [1.415, -0.335, 0.995], 0.014, 0.045, 'brass', 'x', root)
        pin = self.group('quality_record_release_pin', list(self.RELEASE_PIN_BASE), root)
        self.cylinder('reading_frame_vertical_pin', [0, 0, 0], 0.009, 0.16, 'steel', 'z', pin)
        self.cylinder('reading_pin_stop', [0, 0, -0.075], 0.014, 0.018, 'brass', 'z', pin)
        self.custom['quality_record_release_pin'] = pin
        self.custom['quality_record_release_path'] = path
        self.custom['quality_record_release_cable'] = cable
        self.custom['quality_record_release_source_socket'] = socket

    def sync(self, g):
        super().sync(g)
        pin = self.custom.get('quality_record_release_pin')
        if pin is not None:
            withdrawn = bool(g.solved[2] or g.states[2].get('open', False))
            pos = list(self.RELEASE_PIN_BASE)
            if withdrawn:
                pos[2] -= self.RELEASE_PIN_TRAVEL
            self.transform(pin, pos)
