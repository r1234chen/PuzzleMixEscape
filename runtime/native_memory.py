import copy, types

def attach(driver, session):

    def search_memory(d, query):
        e = d.shared_legacy_session.esc
        first = list(d.rows[0].get('decision_images', [])) if d.rows else list(d.current_observation_images)
        turns = [{'turn': 0, 'counted': False, 'action': {'action': 'start'}, 'result': {'ok': True, 'text': '', 'images': first}}]
        for row in d.rows:
            from native_prompt import action_turn
            turns.append(action_turn(row, session.policy.tip_event))
        for i in range(max(0, int(session.recalls) - 1)):
            turns.append({'turn': '0r' + str(i + 1), 'counted': False, 'action': {'action': 'recall'}, 'result': {'ok': True, 'text': '', 'images': []}})
        e.turns = turns
        e.memory = []
        e.t = d.step + 1
        e.recalls = session.recalls
        for turn in turns:
            if isinstance(turn['turn'], int):
                e.remember_turn(turn)
        result = e.a_recall({'action': 'recall', 'query': query})
        ids = {entry[0] for entry in result.get('recalled', [])}
        steps = {m['turn'] for m in e.memory if m['mid'] in ids}
        by_step = {r['step']: r for r in d.rows}
        ordered = []
        for mid, _score in result.get('recalled', []):
            step = next((m['turn'] for m in e.memory if m['mid'] == mid), None)
            if step in by_step:
                ordered.append(by_step[step])
        text = str(result.get('text', ''))
        feedback = text.splitlines()[0] if ordered else text
        return {'rows': ordered, 'feedback': feedback, 'raw_feedback': text, 'ok': bool(result.get('ok')), 'backend': getattr(e, 'search_backend', None), 'implementation': type(e).a_recall.__code__.co_filename}
    driver.search_memory = types.MethodType(search_memory, driver)
    return driver.search_memory
