import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.chdir(HERE.parent)
import _escape

cfg_path = Path(os.environ.get("ESI_ESCAPE_CONFIG") or "run/escape_configs/office_min.json").resolve()
cfg = _escape.load_config(cfg_path)
extra = Path("outputs") / "escape" / f"_extra_objects_{cfg.get('name', 'escape')}.json"
extra.parent.mkdir(parents=True, exist_ok=True)
extra.write_text(json.dumps(_escape.extra_objects(cfg), ensure_ascii=False, indent=1), encoding="utf-8")
os.environ["ESI_EXPLORE"] = "1"
os.environ["ESI_ESCAPE"] = str(cfg_path)
os.environ["ESI_EXTRA_OBJECTS"] = str(extra.resolve())
if os.environ.get("ESI_ESCAPE_EXPLORE", "1") == "1":
    os.environ["ESI_START_POSE"] = "%s,%s,%s" % (cfg["start"]["xy"][0], cfg["start"]["xy"][1], cfg["start"].get("yaw_deg", 0))
    os.environ["ESI_DOORS_LOCKED"] = "1"
    os.environ.setdefault("ESI_PARTITION", "1" if os.environ.get("ESI_ESCAPE_POLICY", "oracle") == "model" else "0")

os.environ.setdefault("ESI_REPLY_REQUIRE_ACTION", "1")

if os.environ.get("ESI_ESCAPE_RESUME", "").strip():
    os.environ["ESI_ESCAPE_RESUME"] = str(Path(os.environ["ESI_ESCAPE_RESUME"]).resolve())
    if os.environ.get("ESI_ESCAPE_EXPLORE", "1") == "1":
        os.environ["ESI_RESUME"] = os.environ["ESI_ESCAPE_RESUME"]

from _runner import launch, DEFAULT_MODEL

start = cfg["start"]
scene = {
    "task": "puzzlemix_escape",
    "level": cfg["public_id"],
    "scene": cfg["scene"],
    "start": {"room": start["room"], "xy": start["xy"], "yaw_deg": start["yaw_deg"]},
}
metadata = extra.with_name("puzzlemix_scene.json")
metadata.write_text(json.dumps(scene, ensure_ascii=False), encoding="utf-8")
raise SystemExit(launch(
    task="puzzlemix_escape",
    metadata=str(metadata.resolve()),
    watch="PuzzleMixEscape: " + scene["level"],
    model=os.environ.get("ESI_MODEL") or DEFAULT_MODEL,
))
