def _door_live_state337(self, so, jn):

    def actual(obj):
        joint = obj.joints[jn]
        state = joint.get_state()
        if state is None or state[0] is None:
            raise TypeError("'NoneType' object is not subscriptable (native joint state unavailable)")
        values = np.asarray(_np(state[0]), dtype=float).ravel()
        if values.size != 1 or not np.isfinite(values[0]):
            raise RuntimeError('Invalid native door joint position: ' + obj.name + '/' + jn)
        return (joint, float(values[0]))
    try:
        return actual(so)
    except TypeError as exc:
        if 'NoneType' not in str(exc) or 'subscriptable' not in str(exc):
            raise
        import omnigibson as og
        if not og.sim.is_playing():
            raise RuntimeError('Door joint unavailable while simulation is not playing') from exc
        og.sim.update_handles()
        refreshed = self.sim(so.name)
        if refreshed is None:
            raise RuntimeError('Door disappeared during native handle refresh: ' + so.name) from exc
        joint, value = actual(refreshed)
        print('  [door337] Native handles refreshed; actual joint state recovered: ' + so.name + '/' + jn + '=' + str(value), flush=True)
        return (joint, value)

def _door_swing(self, so, opened):
    md_ = (getattr(so, 'metadata', None) or {}).get('openable_joint_ids') or {}
    names_ = [v if isinstance(v, str) else v[0] for v in (md_.values() if isinstance(md_, dict) else [p_[1] for p_ in md_])]
    jns = [jn for jn in names_ if jn in (getattr(so, 'joints', {}) or {})]
    if not jns:
        jn0 = self._door_joint(so)
        jns = [jn0] if jn0 else []
    if not jns:
        return None
    closed = getattr(self, '_door_closed_pos', None)
    if closed is None:
        closed = self._door_closed_pos = {}
    first = None
    for jn in jns:
        j, cur = self._door_live_state337(so, jn)
        lo, hi = (float(j.lower_limit), float(j.upper_limit))
        key = so.name if len(jns) == 1 else f'{so.name}|{jn}'
        if opened:
            closed.setdefault(key, cur)
            tgt = hi if abs(hi - cur) >= abs(lo - cur) else lo
        else:
            tgt = closed.get(key, lo if abs(lo - cur) <= abs(hi - cur) else hi)
        j.set_pos(tgt, drive=False)
        first = first or (jn, tgt)
    self.c['step_sim'](30)
    if opened:
        want = self._inward_sign(so)
        flipped = getattr(self, '_door_flipped', None)
        if flipped is None:
            flipped = self._door_flipped = set()
        if want is not None:
            c_, n_ = self._door_plane(so)
            redo = False
            for jn in jns:
                key = f'{so.name}|{jn}'
                lk = (getattr(so, 'links', {}) or {}).get(jn[2:])
                if lk is None or key in flipped:
                    continue
                lc = (np.asarray(self.aabb(lk)[0], float) + np.asarray(self.aabb(lk)[1], float)) / 2.0
                side = 1 if float(np.dot(lc[:2] - c_, n_)) >= 0 else -1
                flipped.add(key)
                if side != want:
                    j = so.joints[jn]
                    lo, hi = (float(j.lower_limit), float(j.upper_limit))
                    if lo >= -1e-06 and hi > 0:
                        j.lower_limit, j.upper_limit = (-hi, 0.0)
                    elif hi <= 1e-06 and lo < 0:
                        j.upper_limit, j.lower_limit = (-lo, 0.0)
                    else:
                        continue
                    tgt = float(j.lower_limit) if abs(float(j.lower_limit)) > abs(float(j.upper_limit)) else float(j.upper_limit)
                    j.set_pos(tgt, drive=False)
                    redo = True
                    print(f'  [密室] 门 {so.name} {jn} 本来往外开：改成往房间里开，限位 [{lo:.2f}, {hi:.2f}] → [{float(j.lower_limit):.2f}, {float(j.upper_limit):.2f}]', flush=True)
            if redo:
                self.c['step_sim'](30)
    for jn in jns:
        j, now = self._door_live_state337(so, jn)
        print(f'  [密室] 门 {so.name} {jn}: 限位 [{float(j.lower_limit):.2f}, {float(j.upper_limit):.2f}] → 现在 {now:.2f}', flush=True)
        if opened:
            key = so.name if len(jns) == 1 else f'{so.name}|{jn}'
            rest = float(closed[key])
            travel = max(abs(float(j.lower_limit) - rest), abs(float(j.upper_limit) - rest))
            if not math.isfinite(now) or not math.isfinite(travel) or travel <= 1e-06 or (abs(now - rest) <= 0.5 * min(travel, REV_OPEN)):
                raise RuntimeError('Door did not physically open: ' + so.name + '/' + jn)
            far_ = max(abs(float(j.lower_limit)), abs(float(j.upper_limit)))
            if abs(now) < far_ - 0.2:
                print(f'  [密室] 诊断：门 {so.name} {jn} 没转开（{now:.2f} / {far_:.2f}），门板沿路碰到：{self._door_blockers(so, jn)}', flush=True)
    return first
