from copy import deepcopy
SYMS = ['circle', 'star', 'square', 'leaf']
KEYS = ['circle', 'triangle', 'square', 'star', 'leaf', 'cross']

def st(kind, room, tag, **kw):
    return dict(kind=kind, room=room, tag=tag, name=kw.pop('name', tag + ' device'), clue_text='', **kw)

def num(room, tag, code, visual, **kw):
    return st('read_code', room, tag, answer=code, digits=len(code), visual=visual, **kw)

def seq(room, tag, values, options=KEYS, flash=False, **kw):
    v = {'type': 'flash', 'sequence': values} if flash else {'type': 'symbol_strip', 'symbols': values}
    return st('sequence', room, tag, options=options, answer=[options.index(x) for x in values], length=len(values), visual=v, **kw)

def rot(room, tag, initial):
    return st('rotate_picture', room, tag, initial=initial, target=[0, 0, 0], auto=True, visual={'type': 'fabric'})

def dual(room, tag, initial, target, kind='window_align', moduli=(4, 4)):
    return st(kind, room, tag, initial=list(initial), target=[x - 1 for x in target], moduli=list(moduli), auto=False, visual={'type': 'block_faces', 'reference': ['star', 'cross']} if kind == 'block_faces' else {'type': 'window_align', 'reference': [x - 1 for x in target]})

def difference(room, tag, target):
    a = ['circle', 'star', 'leaf', 'square', 'triangle', 'cross']
    b = a[:]
    for i in target:
        b[i - 1] = KEYS[(KEYS.index(a[i - 1]) + 1) % 6]
    return st('difference', room, tag, initial=[0] * 6, target=[int(i + 1 in target) for i in range(6)], rows=2, cols=3, visual={'type': 'stamp_compare', 'left': a, 'right': b})

def pair(room, tag, targets):
    return st('assign', room, tag, items=[{'id': x, 'name': 'gauge ' + x, 'symbol': x} for x in 'ABCD'], slots=2, target=['ABCD'.index(x) for x in targets], auto=False, visual={'type': 'gauge_pairs', 'reference': list(targets)})

def wire(room, tag, ports):
    target = [None] * 4
    for i, p in enumerate(ports):
        target[p - 1] = i
    return st('assign', room, tag, items=[{'id': x, 'name': x + ' connector', 'symbol': x} for x in SYMS[:3]], slots=4, target=target, auto=False, visual={'type': 'wire_trace', 'mapping': ports})

def bolts(room, tag, order):
    return st('bolts', room, tag, initial=[0] * 4, target=[1] * 4, order=list(order), visual={'type': 'bolt_chain', 'order': list(order)})

def measure(room, tag, code, value, source=None):
    return num(room, tag, code, {'type': 'ruler', 'reading': value, 'unit': 'mm'}, setup={'kind': 'measure', 'item': 'ruler', 'item_name': 'measuring ruler', 'target_name': 'measurement strip', 'consume': False}, tool_source=source)

def lamp(room, tag, values):
    return seq(room, tag, values, flash=True)

def order(room, tag, values, indices, style='book_order'):
    return seq(room, tag, [str(x) for x in indices], options=['1', '2', '3', '4'], visual_override={'type': style, 'numbers': values})

def pipes(room, tag, initial, mirror=False):
    cells = [[0, 1], [0, 0], [1, 0]] if mirror else [[0, 0], [0, 1], [1, 1]]
    target = [0, 1, 3] if mirror else [0, 2, 0]
    return st('rotate_pipes', room, tag, grid=[2, 2], cells=cells, ports=[[1, 3], [0, 1], [0, 1]], initial=initial, target=target, inlet=cells[0] + [1 if mirror else 3], outlet=cells[-1] + [3 if mirror else 1], auto=True, moduli=[2, 4, 4], visual={'type': 'pipes'})

def binary(room, tag, target):
    return st('binary_pattern', room, tag, initial=[0] * 4, target=target, rows=2, cols=2, visual={'type': 'binary_swatch', 'cells': target})

def weighing(room, tag, code, reading, tare=0):
    return num(room, tag, code, {'type': 'scale', 'reading': reading, 'tare': tare, 'unit': 'g'}, setup={'kind': 'weigh', 'item': 'sample', 'item_name': 'sample tin', 'target_name': 'scale tray', 'consume': True})

def lines(*rows, title=''):
    return {'type': 'table', 'rows': list(rows), 'title': title}

def grid(rows, **kw):
    return {'type': 'number_grid', 'rows': rows, **kw}

def vector(values, **kw):
    return {'type': 'symbol_values', 'symbols': SYMS, 'values': values, **kw}
LEVELS = {}

def add(i, title, rooms, stages, A, B, code):
    for j, s in enumerate(stages):
        if 'visual_override' in s:
            s['visual'] = s.pop('visual_override')
        s['index'] = j
        s['parent'] = None
        for k in range(j - 1, -1, -1):
            if stages[k]['room'] == s['room']:
                s['parent'] = k
                break
        if s['kind'] in ('adjust', 'window_align', 'support_align', 'block_faces'):
            s['initial'] = [x - 1 for x in s['initial']]
        s['name'] = {'bolts': 'inspection bolts', 'rotate_pipes': 'pipe manifold', 'rotate_picture': 'pattern restoration frame', 'assign': 'component fixture', 'sequence': 'signal unit', 'binary_pattern': 'sample pattern keys', 'difference': 'comparison tray', 'support_align': 'frame support', 'window_align': 'inspection windows', 'block_faces': 'reference columns', 'float_key': 'water cylinder', 'balance': 'sample balance', 'pushbox': 'parcel puzzle', 'sliding_puzzle': 'archive sliding tray', 'read_code': 'record cabinet', 'adjust': 'pattern dial'}[s['kind']]
    last = {r: max((j for j, s in enumerate(stages) if s['room'] == r)) for r in ['A', 'B']}
    LEVELS[f'R{i}'] = {'id': f'R{i}', 'title': title, 'room_names': rooms, 'size': [9.6, 5.0], 'room_size': [4.8, 5.0], 'start': [2.4, 2.15, 1.35], 'start_yaw': 90, 'room_views': {'A': [2.4, 2.15, 1.35], 'B': [7.2, 2.15, 1.35]}, 'stages': stages, 'last': last, 'clues': {'A': A, 'B': B}, 'door_code': code, 'door': {'side': 'east', 'start': 0.65, 'width': 1.04}, 'theme': title.lower().split()[0]}
route = st('rotate_pipes', 'A', 'A2', grid=[4, 3], cells=[[2, 0], [2, 2], [1, 2]], ports=[[0, 1]] * 3, initial=[0, 0, 0], target=[1, 3, 2], auto=True, route_special=True, visual={'type': 'pipes'})
add(23, 'Service passage', ['Registration room', 'Number room'], [bolts('A', 'A1', 'BDAC'), route, wire('B', 'B1', [3, 1, 4])], {'type': 'route', 'rows': 4, 'cols': 3, 'path': [[3, 0], [2, 0], [2, 1], [2, 2], [1, 2], [1, 1], [0, 1]], 'title': 'S > T / CORNERS'}, grid([[7, 4, 0], [9, 6, 2], [5, 1, 8], [3, 0, 4]]), '5826')
LEVELS['R23']['stages'][2]['item_source'] = 1
add(24, 'Gauge workshop', ['Gauge room', 'Spare-parts room'], [pair('A', 'A1', 'BD'), rot('A', 'A2', [1, 2, 3]), num('B', 'B1', '352', {'type': 'count', 'groups': [3, 5, 2], 'object': 'tooth'})], {'type': 'hole_mask', 'rows': 3, 'cols': 4, 'points': [[0, 2], [2, 0], [1, 3], [2, 3]]}, grid([[4, 8, 1, 6], [7, 2, 9, 3], [5, 0, 6, 4]]), '1534')
add(25, 'Tea samples', ['Tea-sample room', 'Cup store'], [dual('A', 'A1', [4, 4], [3, 2], kind='support_align'), weighing('B', 'B1', '0250', 270, 20), num('B', 'B2', '425', {'type': 'bottle_heights', 'heights': [4, 2, 5], 'levels': 6})], {'type': 'symbol_strip', 'symbols': ['round_lid', 'tall_cup', 'square_can', 'handled_cup'], 'title': 'ROOT > TIP'}, lines(['round_lid', 7], ['tall_cup', 2], ['square_can', 9], ['handled_cup', 4]), '7294')
add(26, 'Archive index', ['Archive room', 'Reading room'], [st('sliding_puzzle', 'A', 'A1', grid=[2, 3], initial=['D', 'A', 'C', 'B', '', 'E'], target=['A', 'B', 'C', 'D', 'E', ''], auto=True, visual={'type': 'cargo_puzzle'}), dual('A', 'A2', [4, 2], [2, 3]), difference('B', 'B1', [1, 4, 6])], lines(['deer', 'sun'], ['fish', 'moon'], ['bird', 'sun'], ['deer', 'moon']), grid([[4, 7, 2], [8, 1, 6], [5, 0, 3]], row_labels=['deer', 'fish', 'bird'], col_labels=['sun', 'moon', 'star']), '4157')
add(27, 'Mirror repair', ['Mirror-frame room', 'Display room'], [num('A', 'A1', '425', {'type': 'trace', 'mapping': [4, 2, 5]}), st('float_key', 'B', 'B1', visual={'type': 'float_key'}), dual('B', 'B2', [3, 4], [1, 3], kind='support_align')], {'type': 'hole_mask', 'rows': 2, 'cols': 4, 'points': [[0, 0], [1, 2], [0, 3], [1, 0]]}, grid([[3, 8, 1, 6], [7, 4, 9, 2]], mirror=True), '3967')
chain = lambda room, tag: st('assign', room, tag, items=[{'id': str(j), 'name': 'binding strip ' + str(j + 1), 'symbol': x + '>' + y} for j, (x, y) in enumerate([('circle', 'leaf'), ('square', 'star'), ('leaf', 'square'), ('star', 'flag')])], slots=4, target=[0, 2, 1, 3], auto=False, visual={'type': 'chain', 'ends': [['circle', 'leaf'], ['square', 'star'], ['leaf', 'square'], ['star', 'flag']]})
add(28, 'Bookbinding', ['Binding room', 'Card store'], [wire('A', 'A1', [2, 4, 1]), lamp('A', 'A2', ['circle', 'leaf', 'square']), chain('B', 'B1')], lines(['START', 'triangle'], ['NEXT', 1], ['NEXT', 2], ['PREVIOUS', 1], ['NEXT', 3], title='PAGE TURNS / READ EACH STOP'), lines(['triangle', 7], [2, 6], [3, 8], [4, 4], [5, 9], [6, 1], title='PAGES 1 > 6'), '6481')
add(29, 'Instrument calibration', ['Calibration room', 'Instrument room'], [measure('A', 'A1', '0140', 140), num('B', 'B1', '253', {'type': 'dials', 'values': [2, 5, 3]}), dual('B', 'B2', [1, 3], [4, 5], kind='block_faces', moduli=(6, 6))], vector([2, 1, 3, 2], title='READING - PAD'), vector([7, 5, 9, 3]), '5461')
add(30, 'Dated records', ['Maintenance registry', 'Record store'], [bolts('A', 'A1', 'ACDB'), binary('A', 'A2', [0, 1, 1, 0]), st('assign', 'B', 'B1', items=[{'id': n, 'name': n + ' cover card', 'symbol': n} for n in ['building', 'tree', 'car']], slots=4, target=[0, 1, None, 2], visual={'type': 'classes', 'classes': ['building', 'plant', 'animal', 'transport']})], vector(['WED', 'MON', 'TUE', 'THU']), grid([[4, 9, 2, 5], [7, 1, 6, 3], [8, 4, 9, 0], [6, 5, 1, 8]], row_labels=SYMS, col_labels=['MON', 'TUE', 'WED', 'THU']), '2748')
add(31, 'Split numerals', ['Textile sample room', 'Light room'], [order('A', 'A1', [3, 1, 4, 2], [2, 4, 1, 3], style='heights'), pipes('B', 'B1', [1, 0, 1]), measure('B', 'B2', '0230', 230, source=1)], {'type': 'segments', 'values': ['abfg', 'afg', 'abg', 'abg']}, {'type': 'segments', 'values': ['cde', 'cde', 'cd', 'de']}, '8632')
add(32, 'Postal wheel', ['Mail-sorting room', 'Wheel store'], [st('balance', 'A', 'A1', weights=[1, 2, 4, 8], target_mass=6, visual={'type': 'balance'}), lamp('A', 'A2', ['cross', 'leaf', 'cross', 'circle']), st('pushbox', 'B', 'B1', initial_player=[2, 1], initial_box=[2, 2], goal=[3, 3], grid=[4, 4], visual={'type': 'pushbox'})], {'type': 'ring', 'marks': [0, 2, 5, 9]}, {'type': 'ring', 'numbers': [1, 4, 9, 2, 7, 6, 0, 3, 8, 5, 2, 4], 'triangle': 2}, '9734')
add(33, 'Filling samples', ['Sample room', 'Measurement room'], [rot('A', 'A1', [2, 1, 3]), seq('B', 'B1', ['left', 'up', 'right'], options=['up', 'right', 'down', 'left']), dual('B', 'B2', [2, 1], [3, 4])], vector([1, 3, 2, 4], title='BEFORE / INCREASE'), vector([8, 5, 9, 6], title='AFTER'), '7272')
add(34, 'State selectors', ['Power room', 'Indicator room'], [difference('A', 'A1', [2, 3, 5]), seq('A', 'A2', ['2', '3'], options=['1', '2', '3', '4'], distinct=True, visual_override={'type': 'locations', 'points': ['red left ring', 'red right ring', 'blue upper clip', 'blue lower clip'], 'selected': [2, 3]}), order('B', 'B1', [40, 10, 30, 20], [2, 4, 3, 1])], vector(['ON', 'OFF', 'OFF', 'ON']), grid([[6, 1, 8, 4], [3, 7, 2, 9]], row_labels=['ON', 'OFF'], col_labels=SYMS), '6724')
add(35, 'Shared solid cells', ['Screening room', 'Review room'], [bolts('A', 'A1', 'DBAC'), wire('B', 'B1', [1, 4, 2]), measure('B', 'B2', '0220', 220, source=1)], {'type': 'solid', 'solid': [1, 3, 4, 6, 7, 8], 'title': 'BOTH SOLID / LEFT > RIGHT'}, {'type': 'solid', 'solid': [1, 2, 4, 5, 7, 8], 'numbers': [4, 1, 7, 5, 8, 2, 9, 6]}, '4596')
add(36, 'Before storage', ['Item registry', 'Storage room'], [seq('A', 'A1', ['circle', 'square', 'leaf', 'star'], options=SYMS, visual_override={'type': 'occlusion', 'symbols': ['circle', 'square', 'leaf', 'star']}), num('A', 'A2', '3068', {'type': 'mirror', 'code': '3068'}), num('B', 'B1', '0825', {'type': 'clock', 'hour': 8, 'minute': 25, 'period': 'AM', 'format': 'HHMM'})], lines(['book:4', 'cup:7', 'ball:2'], ['brush:9', 'hook:3', 'box:5'], ['hat:8', 'bottle:6', 'shoe:1'], ['leaf_clip:5', 'scroll:0', 'clip:7'], title='ORIGINAL'), lines(['book', 'cup'], ['hook', 'box'], ['hat', 'shoe'], ['leaf_clip', 'scroll'], title='CURRENT / MISSING ITEM'), '2967')
add(37, 'Ordering relations', ['Display room', 'Number room'], [rot('A', 'A1', [3, 2, 1]), lamp('B', 'B1', ['leaf', 'circle', 'leaf']), measure('B', 'B2', '0160', 160, source=1)], lines(['circle', '>', 'star'], ['leaf', '>', 'square']), lines(['star', '>', 'leaf'], ['circle', 8], ['star', 0], ['leaf', 4], ['square', 6]), '8046')
add(38, 'Toy queue', ['Toy repair room', 'Label room'], [weighing('A', 'A1', '0476', 476), binary('A', 'A2', [1, 0, 0, 1]), num('B', 'B1', '364', {'type': 'count', 'groups': [3, 6, 4], 'object': 'spoke'})], {'type': 'symbol_strip', 'symbols': SYMS}, lines(['1', '< >', '3'], ['2', '< >', '4'], ['circle', 5], ['star', 7], ['square', 9], ['leaf', 2]), '9257')
add(39, 'Pattern inventory', ['Pattern room', 'Pattern store'], [difference('A', 'A1', [1, 3, 4]), seq('B', 'B1', ['down', 'left', 'up'], options=['up', 'right', 'down', 'left'], visual_override={'type': 'symbol_strip', 'symbols': ['down', 'left', 'up'], 'title': 'S > T'}), num('B', 'B2', '368', {'type': 'successor', 'before': [2, 5, 7]})], {'type': 'symbol_strip', 'symbols': ['circle', 'cross', 'leaf', 'star']}, {'type': 'symbol_grid', 'rows': [['circle', 'cross', 'leaf', 'star', 'square'], ['circle', 'cross', 'leaf', 'star', 'triangle'], ['circle', 'leaf', 'star', 'star', 'triangle'], ['circle', 'star', None, None, None]]}, '4235')
add(40, 'Assembly supply', ['Assembly room', 'Supply room'], [pair('A', 'A1', 'DC'), pipes('A', 'A2', [1, 3, 0], mirror=True), st('assign', 'B', 'B1', items=[{'id': str(i), 'name': 'assembly strip ' + str(i + 1), 'symbol': x + '>' + y} for i, (x, y) in enumerate(zip(['circle', 'star', 'leaf', 'square'], ['star', 'leaf', 'square', 'flag']))], slots=4, target=[0, 1, 2, 3], visual={'type': 'chain', 'ends': [['circle', 'star'], ['star', 'leaf'], ['leaf', 'square'], ['square', 'flag']]})], vector([1, 3, 2, 4]), vector([6, 2, 5, 1], title='COMBINE THE TWO PILES'), '7575')
add(41, 'Common samples', ['Sample archive', 'Sample display'], [wire('A', 'A1', [3, 2, 4]), num('B', 'B1', '264', {'type': 'holes', 'positions': [2, 6, 4]}), num('B', 'B2', '580', {'type': 'pattern_map', 'references': ['crosshatch', 'waves', 'dots'], 'samples': [['dots', 0], ['crosshatch', 5], ['grid', 2], ['waves', 8]]})], lines(['round_pot', 'square_box'], ['leaf_clip', 'star_plate'], ['brush', 'comb'], ['ball', 'cup']), lines(['square_box:8', 'round_cup:1'], ['star_plate:4', 'triangle_plate:7'], ['comb:6', 'ruler:2'], ['ball:3', 'hat:9'], title='COMMON ITEM / 1 > 4'), '8463')
add(42, 'Appointment issue', ['Appointment registry', 'Issue room'], [difference('A', 'A1', [2, 4]), num('A', 'A2', '524', {'type': 'hole_count', 'holes': [[1, 2, 3, 5, 6], [2, 5], [1, 3, 4, 6]]}), order('B', 'B1', ['9/12', '9/03', '9/19', '9/07'], [2, 4, 1, 3])], lines(['X', 'clock:9:15 AM'], ['Y', 'clock:2:30 PM']), lines(['08:00 - 10:00', 26, 13], ['10:00 - 12:00', 71, 68], ['12:00 - 15:00', 49, 52], ['15:00 - 18:00', 80, 97], title='TIME / X / Y'), '2652')
add(43, 'One step each', ['Sign room', 'Map room'], [seq('A', 'A1', ['leaf', 'square', 'circle', 'star'], options=SYMS, visual_override={'type': 'occlusion', 'symbols': ['leaf', 'square', 'circle', 'star']}), num('B', 'B1', '246', {'type': 'missing_middle', 'rows': [[1, None, 3], [3, None, 5], [5, None, 7]]}), weighing('B', 'B2', '0230', 260, 30)], vector(['right', 'up', 'left', 'down'], title='ONE CELL EACH'), grid([[6, 2, 9], [7, 4, 1], [3, 8, 5]], starts=[['circle', 0, 0], ['star', 2, 2], ['square', 2, 1], ['leaf', 0, 2]]), '2131')
add(44, 'Samples and standards', ['Sample comparison', 'Standard store'], [num('A', 'A1', '241', {'type': 'odd_one', 'rows': [['circle', 'square', 'circle', 'circle'], ['leaf', 'leaf', 'leaf', 'star'], ['triangle', 'square', 'square', 'square']]}), lamp('A', 'A2', ['square', 'leaf', 'square']), rot('B', 'B1', [1, 3, 2])], vector([3, 7, 2, 6]), lines(['STANDARD', 5, 4, 2, 8], ['HEAVIER', 6, 9, 5, 1], ['EQUAL', 4, 3, 7, 8], ['LIGHTER', 8, 2, 0, 6]), '8976')
for spec in LEVELS.values():
    spec['interroom'] = {'type': 'open_passage', 'boundary_x': 4.8, 'y_range': [1.8, 2.95], 'door_leaf': False, 'lock': False, 'requires_action': False}
    for s in spec['stages']:
        if s.get('tool_source') is not None:
            s['parent'] = None
    assert len(spec['stages']) == 3 and set((x['room'] for x in spec['stages'])) == {'A', 'B'}
LEVELS['R25']['stages'][0].update(kind='adjust', name='tea-pattern rings', visual={'type': 'pattern_rings'})
LEVELS['R33']['stages'][2].update(kind='adjust', name='bottle-shape levers', visual={'type': 'lever_shapes'})
LEVELS['R28']['stages'][2]['rack_order'] = [1, 3, 0, 2]
LEVELS['R40']['stages'][2]['rack_order'] = [2, 0, 3, 1]
LEVELS['R33']['stages'][1]['visual'] = {'type': 'cap_notches', 'directions': ['left', 'up', 'right']}
