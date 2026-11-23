import copy, re
from easy88_core import EasyGame, pipe_connected
from action_feedback import failure_for

class MediumGame(EasyGame):

    def __init__(self):
        super().__init__()
        self.reward_open = [False] * 3
        self.cover_keys = {}
        self.possessions = {}
        for i, s in enumerate(self.SPEC['stages']):
            self.opened[f's{i + 1}_cover'] = s.get('parent') is None
            if s['kind'] == 'bolts':
                self.states[i]['selected'] = [0] * 4
            if s['kind'] == 'pushbox':
                self.states[i].update(player=list(s['initial_player']), box=list(s['initial_box']))
            if s['kind'] == 'balance':
                self.states[i]['weights'] = []
        self.opened.pop('key_box', None)

    def snapshot(self):
        x = super().snapshot()
        x.update(reward_open=list(self.reward_open), cover_keys=dict(self.cover_keys), possessions=copy.deepcopy(self.possessions))
        return x

    def stage_accessible(self, i):
        return 0 <= i < 3 and self.opened.get(f's{i + 1}_cover', False)

    def cover_unlocked(self, i):
        p = self.SPEC['stages'][i].get('parent')
        return (p is None or self.solved[p]) and (not self.SPEC['stages'][i].get('key_gate') or self.cover_keys.get(i, self.cover_keys.get(str(i), False)))

    def _check(self, i):
        s = self.SPEC['stages'][i]
        v = self.states[i]
        if s.get('route_special'):
            return v['angles'] == s['target']
        if s['kind'] == 'bolts':
            return all(v['selected'])
        if s['kind'] == 'pushbox':
            return v['box'] == s['goal']
        if s['kind'] == 'balance':
            return sum((s['weights'][j] for j in v['weights'])) == s['target_mass']
        return super()._check(i)

    def act(self, a):
        kind = a.get('action')
        key = a.get('_hit364', '')
        if key == 'exit_lock' and kind == 'unlock':
            key = 'exit'

        def out(ok, text=''):
            return {'ok': bool(ok), 'text': text if ok and kind == 'read' else '' if ok else failure_for(kind)}
        if not a.get('_validated364'):
            return out(False)
        if key in ('clue_A', 'clue_B'):
            room = key[-1]
            i = self.SPEC['last'][room]
            portable = self.SPEC['id'] == 'R31' or (self.SPEC['id'] == 'R24' and room == 'A')
            if kind == 'take' and portable and self.reward_open[i] and (key not in self.taken):
                self.taken.add(key)
                self.holding.append(key)
                return out(True)
            if kind == 'use' and self.SPEC['id'] == 'R24' and (room == 'B') and self.reward_open[i]:
                item = self._resolve_item(a.get('item'))
                if item != 'clue_A':
                    return out(False)
                self.holding.remove(item)
                self.possessions['mask_installed'] = True
                return out(True)
            return out(False)
        if key == 'light_frame' and kind == 'use' and (self.SPEC['id'] == 'R31'):
            item = self._resolve_item(a.get('item'))
            if item not in ('clue_A', 'clue_B'):
                return out(False)
            self.holding.remove(item)
            self.possessions['installed_' + item[-1]] = True
            return out(True)
        if key == 'exit':
            if kind == 'unlock':
                self.possessions['door_input'] = str(a.get('code', ''))
                if str(a.get('code', '')) == self.SPEC['door_code']:
                    self.exit_unlocked = True
                    return out(True)
                return out(False)
            if kind in ('open', 'close'):
                if kind == 'open' and (not self.exit_unlocked):
                    return out(False)
                self.opened['exit'] = kind == 'open'
                self.exited = self.opened['exit'] and self.exit_unlocked
                return out(True)
            return out(False)
        r = re.fullmatch('reward_(\\d)', key)
        if r:
            i = int(r[1])
            if kind not in ('open', 'close') or (kind == 'open' and (not self.solved[i])):
                return out(False)
            self.reward_open[i] = kind == 'open'
            return out(True)
        r = re.fullmatch('reward_key_(\\d)', key)
        if r:
            i = int(r[1])
            if kind == 'take' and self.reward_open[i] and (key not in self.taken):
                self.taken.add(key)
                self.holding.append(key)
                return out(True)
            return out(False)
        r = re.fullmatch('s([123])_(.+)', key)
        if not r:
            return out(False)
        i = int(r[1]) - 1
        tail = r[2]
        s = self.SPEC['stages'][i]
        v = self.states[i]
        if tail == 'tool' and kind == 'take' and ((s.get('setup') or {}).get('kind') == 'weigh') and v['setup_used']:
            if key in self.holding:
                return out(False)
            v['setup_used'] = False
            v['setup_ready'] = False
            self.holding.append(key)
            return out(True)
        if s['kind'] == 'assign' and tail == 'reset' and (kind == 'press'):
            if not self.stage_accessible(i) or self.solved[i]:
                return out(False)
            v['assignment'] = {}
            for j in range(len(s['items'])):
                item = f's{i + 1}_item_{j}'
                self.taken.discard(item)
                if item in self.holding:
                    self.holding.remove(item)
            return out(True)
        if tail == 'cover' and s.get('key_gate') and (kind == 'use'):
            item = self._resolve_item(a.get('item'))
            if item != 'reward_key_' + str(s['parent']):
                return out(False)
            self.cover_keys[i] = True
            return out(True)
        if tail == 'tool' and s.get('tool_source') is not None and (not self.reward_open[s['tool_source']]):
            return out(False)
        if tail.startswith('item_') and s.get('item_source') is not None and (not self.reward_open[s['item_source']]):
            return out(False)
        if tail == 'lock' and kind == 'unlock':
            self.possessions[key] = str(a.get('code', ''))
        if s['kind'] == 'rotate_pipes' and kind == 'press' and tail.startswith('control_'):
            if not self.stage_accessible(i):
                return out(False)
            j = int(tail.rsplit('_', 1)[1])
            v['angles'][j] = (v['angles'][j] + 1) % s.get('moduli', [4] * len(v['angles']))[j]
            if self._check(i):
                self._solve(i)
            return out(True)
        if s['kind'] not in ('bolts', 'pushbox', 'balance'):
            return super().act(a)
        if tail == 'cover':
            if kind not in ('open', 'close') or (kind == 'open' and (not self.cover_unlocked(i))):
                return out(False)
            self.opened[key] = kind == 'open'
            return out(True)
        if not self.stage_accessible(i):
            return out(False)
        if tail == 'reset' and kind == 'press':
            if self.solved[i]:
                return out(False)
            if s['kind'] == 'pushbox':
                v.update(player=list(s['initial_player']), box=list(s['initial_box']))
            if s['kind'] == 'bolts':
                v['selected'] = [0] * 4
            return out(True)
        if s['kind'] == 'bolts' and tail.startswith('control_') and (kind == 'press'):
            j = int(tail.rsplit('_', 1)[1])
            order = ['ABCD'.index(x) for x in s['order']]
            n = sum(v['selected'])
            if n == 4 or j != order[n]:
                return out(False)
            v['selected'][j] = 1
            if all(v['selected']):
                self._solve(i)
            return out(True)
        if s['kind'] == 'pushbox' and tail.startswith('choice_') and (kind == 'press'):
            j = int(tail.rsplit('_', 1)[1])
            dr, dc = [(-1, 0), (0, 1), (1, 0), (0, -1)][j]
            p = [v['player'][0] + dr, v['player'][1] + dc]
            b = v['box'][:]
            if not all((1 <= z <= 4 for z in p)):
                return out(False)
            if p == b:
                b = [b[0] + dr, b[1] + dc]
                if not all((1 <= z <= 4 for z in b)):
                    return out(False)
            v['player'] = p
            v['box'] = b
            if b == s['goal']:
                self._solve(i)
            return out(True)
        if s['kind'] == 'balance':
            m = re.fullmatch('weight_(\\d)', tail)
            if m and kind == 'take':
                j = int(m[1])
                if key in self.holding:
                    return out(False)
                if j in v['weights']:
                    v['weights'].remove(j)
                self.holding.append(key)
                self.taken.add(key)
                return out(True)
            if tail == 'pan' and kind == 'use':
                item = self._resolve_item(a.get('item'))
                m = re.fullmatch('s' + str(i + 1) + '_weight_(\\d)', item or '')
                if not m:
                    return out(False)
                j = int(m[1])
                v['weights'].append(j)
                self.holding.remove(item)
                if self._check(i):
                    self._solve(i)
                return out(True)
        return out(False)

def make_game(spec):
    from easy88_core import build_labels

    class Game(MediumGame):
        pass
    Game.SPEC = copy.deepcopy(spec)
    for i, s in enumerate(Game.SPEC['stages']):
        if spec['id'] == 'R29' and i == 2 or (spec['id'] == 'R36' and i == 1):
            s['key_gate'] = True
    Game.LABELS = build_labels(Game.SPEC)
    for i, s in enumerate(Game.SPEC['stages']):
        Game.LABELS['reward_' + str(i)] = s['name'] + ' drawer'
        Game.LABELS['reward_key_' + str(i)] = 'small brass control key'
        for j in range(4):
            Game.LABELS[f's{i + 1}_weight_{j}'] = str([1, 2, 4, 8][j]) + '-point weight'
        Game.LABELS[f's{i + 1}_pan'] = 'balance pan'
    Game.LABELS.update(exit='exit door')
    Game.LABELS.update(exit_lock='exit code keypad', clue_A=spec['room_names'][0] + ' record', clue_B=spec['room_names'][1] + ' record')
    if spec['id'] == 'R24':
        Game.LABELS['clue_A'] = 'transparent locator sheet'
    if spec['id'] == 'R31':
        Game.LABELS.update(clue_A='first numeral film', clue_B='second numeral film', light_frame='locating light frame')
    for i, s in enumerate(Game.SPEC['stages']):
        if s['kind'] == 'float_key':
            Game.LABELS[f's{i + 1}_float_key'] = 'small brass cylinder key'
    return Game
