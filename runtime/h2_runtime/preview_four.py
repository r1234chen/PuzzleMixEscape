import math, copy, json, hashlib
from pathlib import Path

def capture(d):
    from pxr import UsdGeom, Usd, UsdLux
    initial = copy.deepcopy(d.game.snapshot())
    out = d.run / 'screenshots/initial'
    out.mkdir(parents=True, exist_ok=True)
    stage = d.og.sim.stage
    hidden = []
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render], useExtentsHint=True)
    for p in stage.Traverse():
        if not (p.IsA(UsdGeom.Mesh) or p.IsA(UsdLux.RectLight)):
            continue
        if any((k in p.GetName().lower() for k in ['ceiling', 'roof', 'beam', 'lamp', 'lintel'])):
            try:
                above = bounds.ComputeWorldBound(p).ComputeAlignedBox().GetMin()[2] > 2
            except Exception:
                above = False
            if above:
                at = UsdGeom.Imageable(p).GetVisibilityAttr()
                hidden.append((at, at.HasAuthoredValueOpinion(), at.Get()))
                with d.og.sim.editing_usd():
                    UsdGeom.Imageable(p).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    try:
        with d.og.sim.editing_usd():
            UsdLux.DomeLight.Define(stage, '/World/medium_overview_fill').CreateIntensityAttr(1000.0)
        d.camera.set_attribute('projection', 'orthographic')
        d.camera.horizontal_aperture = 108.0
        d.camera.set_attribute('verticalAperture', 54.0)
        d.raw([4.8, 2.5, 6.8], [4.8, 2.5, 0], warm=24).save(out / 'top.png')
    finally:
        with d.og.sim.editing_usd():
            stage.RemovePrim('/World/medium_overview_fill')
            for at, authored, val in hidden:
                if authored:
                    at.Set(val)
                else:
                    at.Clear()
        d.camera.set_attribute('projection', 'perspective')
        d.camera.horizontal_aperture = 28.0
        d.camera.set_attribute('verticalAperture', 14.0)
    for room, pos in [('A', [2.4, 2.0, 1.35]), ('B', [7.2, 2.0, 1.35])]:
        for name, a in [('front', 90), ('back', 270), ('left', 180), ('right', 0)]:
            f = [math.cos(math.radians(a)), math.sin(math.radians(a)), 0]
            look = [x + y for x, y in zip(pos, f)]
            d.raw(pos, look, warm=16).save(out / f'room_{room}_{name}.png')
    assert d.game.snapshot() == initial
    d.frame(warm=24)
    records = {p.name: {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.glob('*.png')}
    assert len(records) == 9
    (out / 'CAPTURE.json').write_text(json.dumps({'images': records, 'presentation_only': True, 'initial_state_unchanged': True, 'room_stands': {'A': [2.4, 2.0, 1.35], 'B': [7.2, 2.0, 1.35]}, 'native_images': 9, 'model_calls': 0}, ensure_ascii=False, indent=2), encoding='utf-8')
