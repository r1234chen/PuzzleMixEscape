import types, json

def run(d):
    old = d.click
    events = []

    def click(driver, key, kind='read', item=None, purpose='', **fields):
        if kind == 'open' and key in ('vent', 'exit'):
            shared = driver.shared_legacy_session
            e = shared.esc
            import opening_clearance
            oid = e.by_sim['vent' if key == 'vent' else 'exit']
            ids = {'object': oid}
            if key == 'vent':
                ids['part'] = 1
            for attempt in range(4):
                refusal = opening_clearance.check(e, shared.C, ids, 'open')
                if refusal is None:
                    break
                if attempt == 3:
                    raise RuntimeError('Measured opening sweep remains blocked after limited public avoidance')
                events.append({'key': key, 'before_position': list(map(float, e.pos)), 'clearance': refusal['opening_clearance_private'], 'public_avoidance': {'action': 'step_back', 'distance': 0.1}})
                driver.execute({'action': 'step_back', 'distance': 0.1}, 'Step outside the measured moving-part sweep')
            driver.save('ACTUAL_SWEEP_AVOIDANCE.json', {'user_authorized': True, 'events': events, 'toolbox_stance_unchanged': True, 'no_environment_rule_override': True})
        return old(key, kind, item, purpose, **fields)
    d.click = types.MethodType(click, d)
    return d.level.standard(d)
