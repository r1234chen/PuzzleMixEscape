from __future__ import annotations
import os
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY','')
DEFAULT_MODEL = 'qwen3.7-plus'
_INTERESTING_RESULT_KEYS = ('operation', 'success', 'error', 'reason', 'lift_m', 'small_object_inside_before_pickup', 'small_object_lifted', 'grasp_success', 'object', 'target', 'container', 'poured_completely', 'poured_overflow', 'physical_state', 'attempts', 'placement', 'placed_on_slope', 'open_state')

def launch(*, task: str, metadata: str, watch: str='', model: str=DEFAULT_MODEL, max_steps: int=30, max_new_tokens: int=8192, headless: bool=True, verbose: bool=True, disable_segmentation: bool=True, warning: str='') -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    os.chdir(ROOT)
    if os.environ.get('ESI_MAX_STEPS_OVERRIDE', '').isdigit():
        max_steps = int(os.environ['ESI_MAX_STEPS_OVERRIDE'])
    if os.environ.get('ESI_EXPLORE') == '1':
        max_steps = 100000
    os.environ['OMNI_KIT_ACCEPT_EULA'] = 'YES'
    os.environ['DASHSCOPE_API_KEY'] = DASHSCOPE_API_KEY
    os.environ['ESI_MAX_STEPS'] = str(max_steps)
    if headless:
        os.environ['OMNIGIBSON_HEADLESS'] = '1'
    else:
        os.environ.pop('OMNIGIBSON_HEADLESS', None)
    for var in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy'):
        os.environ.pop(var, None)
    sys.path.insert(0, str(ROOT / 'src' / 'active_explore'))
    import pipeline
    from models import qwen as _qwen
    _qwen.reset_thinking()
    if disable_segmentation:
        pipeline.load_task_module(task).DISABLE_VIEWER_CAMERA_MODALITIES = True
    usage = _install_hooks(pipeline) if verbose else None
    _arm_camera_guard(pipeline, verbose=verbose)
    _arm_collision_guard(pipeline, verbose=verbose)
    _arm_render_guard(pipeline, verbose=verbose)
    _arm_grasp_guard(pipeline, verbose=verbose)
    from _tools import arm_tools, arm_put_fix, arm_joint_guard
    arm_joint_guard(pipeline, verbose=verbose)
    arm_tools(pipeline, verbose=verbose)
    arm_put_fix(pipeline, verbose=verbose)
    from _tools import arm_preconditions
    arm_preconditions(pipeline, verbose=verbose)
    meta = _read_question(metadata)
    编号, 脚本名 = _script_id()
    print('=' * 70)
    print(f"编号   : {(编号 if 编号 is not None else '-')}   ({脚本名 or '?'})")
    print(f"任务   : {task}  /  {meta.get('small_task') or ''}")
    print(f"场景   : {meta.get('scene')} / {meta.get('room')}")
    if task == 'puzzlemix_escape':
        print(f"关卡   : {meta['level']}")
    else:
        print(f"问题   : {meta.get('question')}")
        print(f"答案   : {meta.get('answer')}")
        if meta.get('options'):
            print(f"选项   : {meta['options']}")
    if watch:
        print(f'看点   : {watch}')
    print(f"配置   : 模型={model}  界面={('关' if headless else '开')}  最多{max_steps}步  分割渲染={('关' if disable_segmentation else '开')}")
    if warning:
        print(f'⚠ 注意 : {warning}')
    print(f"截图   : {ROOT / 'outputs' / 'steps'}")
    print(f"结果   : {ROOT / 'outputs' / 'results'}")
    print('=' * 70)
    print('首次启动要编译着色器，卡住一两分钟是正常的\n', flush=True)
    _arm_record_writer(task, metadata, meta, model)
    code = pipeline.main(['--task', task, '--metadata', metadata, '--provider', 'qwen', '--model', model, '--max-steps', str(max_steps), '--max-new-tokens', str(max_new_tokens), '--results-root', 'outputs/results', '--step-image-root', 'outputs/steps', '--overwrite'])
    _write_experiment_record(task, metadata, meta, model)
    if usage is not None:
        total = usage['tok_in'] + usage['tok_out']
        print(f"\n本次消耗: {usage['step']} 步 / 输入 {usage['tok_in']:,} + 输出 {usage['tok_out']:,} = {total:,} tokens", flush=True)
    return code

def _script_id():
    import re
    try:
        name = Path(sys.argv[0]).stem
    except Exception:
        return (None, None)
    m = re.match('(\\d+)_(.+)', name)
    if m:
        return (int(m.group(1)), name)
    return (None, name or None)

def _arm_record_writer(task: str, metadata: str, meta: dict, model: str) -> None:
    import atexit
    import omnigibson as og
    done = {'written': False}

    def write_once():
        if done['written']:
            return
        done['written'] = True
        try:
            _write_experiment_record(task, metadata, meta, model)
        except Exception as exc:
            print(f'[警告] 实验记录写入失败: {type(exc).__name__}: {exc}', flush=True)
    original_shutdown = og.shutdown

    def shutdown_with_record(*args, **kwargs):
        write_once()
        return original_shutdown(*args, **kwargs)
    og.shutdown = shutdown_with_record
    atexit.register(write_once)
    globals()['_record_written_flag'] = done

def _arm_grasp_guard(pipeline, verbose: bool=True) -> None:
    try:
        ss = pipeline.load_task_module('stacking_stability')
    except Exception as exc:
        print(f'[抓取防崩] 挂载失败，本次运行无防护：{exc}')
        return
    if getattr(ss, '_grasp_guard_armed', False):
        return
    original_detach = ss.detach_grasp

    def guarded_detach():
        import omnigibson as og
        if getattr(ss, 'AG_JOINT_PRIM', None) is None:
            return original_detach()
        try:
            state = og.sim.dump_state(serialized=False)
            og.sim.stop()
            original_detach()
            og.sim.play()
            og.sim.load_state(state, serialized=False)
            for _ in range(3):
                og.sim.step()
            if verbose:
                print('[抓取防崩] 关节删除已在 stop/play 保护段内完成，场景状态已恢复')
        except Exception as exc:
            print(f'[抓取防崩] 保护流程异常（{exc}），回退原始删除')
            original_detach()
    ss.detach_grasp = guarded_detach
    ss._grasp_guard_armed = True
    if verbose:
        print('[抓取防崩] 已挂载：关节删除将走 stop/play 保护段')

def _arm_render_guard(pipeline, verbose: bool=True) -> None:
    import numpy as np
    original = pipeline.capture_image

    def guarded(path):
        result = original(path)
        try:
            from PIL import Image
            for attempt in range(3):
                a = np.asarray(Image.open(result).convert('L'), dtype=np.float32)
                if float(a.mean()) > 1.0:
                    break
                import omnigibson as og
                for _ in range(10):
                    og.sim.render()
                original(path)
                if verbose:
                    print(f'[取帧重试] 黑帧重拍（第 {attempt + 1} 次）: {path.name}', flush=True)
        except Exception:
            pass
        return result
    pipeline.capture_image = guarded
    if verbose:
        print('[取帧重试] 已启用（纯黑帧自动重拍）', flush=True)

def _arm_collision_guard(pipeline, verbose: bool=True) -> None:
    import numpy as np
    try:
        from omnigibson.utils.sampling_utils import raytest
    except Exception as exc:
        print(f'[碰撞守卫] raytest 不可用（{type(exc).__name__}），未启用', flush=True)
        return
    original = pipeline.apply_camera_action

    def guarded(pos, quat, action):
        new_pos, new_quat = original(pos, quat, action)
        moved = np.asarray(new_pos, float) - np.asarray(pos, float)
        dist = float(np.linalg.norm(moved))
        if dist < 1e-06:
            return (new_pos, new_quat)
        try:
            direction = moved / dist
            end = np.asarray(pos, float) + direction * (dist + 0.05)
            hit = raytest(np.asarray(pos, float), end, only_closest=True)
            if isinstance(hit, dict) and hit.get('hit'):
                if verbose:
                    print(f"[碰撞守卫] {action} 被挡（{hit.get('distance', 0):.2f}m 处命中），保持原位", flush=True)
                try:
                    from _tools import STATE as _TS
                    _TS['last_block'] = {'action': str(action), 'dist': float(hit.get('distance', 0.0))}
                except Exception:
                    pass
                return (np.asarray(pos, float).copy(), new_quat)
        except Exception as exc:
            if verbose:
                print(f'[碰撞守卫] 检测异常放行: {type(exc).__name__}', flush=True)
        return (new_pos, new_quat)
    pipeline.apply_camera_action = guarded
    if verbose:
        print('[碰撞守卫] 已启用（相机平移带射线检测）', flush=True)

def _arm_camera_guard(pipeline, verbose: bool=True) -> None:
    import numpy as np
    original = pipeline.task_postprocess_env

    def variance_at(pos, quat, tag) -> float:
        from PIL import Image
        tmp = ROOT / 'outputs' / '_camguard' / f'{tag}.png'
        pipeline.set_camera(np.asarray(pos, dtype=float), np.asarray(quat, dtype=float))
        pipeline.capture_image(tmp)
        return float(np.asarray(Image.open(tmp).convert('L'), dtype=np.float32).std())

    def lookat_quat(cam, target):
        from scipy.spatial.transform import Rotation
        d = np.asarray(target, float) - np.asarray(cam, float)
        d = d / max(np.linalg.norm(d), 1e-09)
        z = -d
        x = np.cross([0.0, 0.0, 1.0], z)
        n = np.linalg.norm(x)
        x = np.array([1.0, 0.0, 0.0]) if n < 1e-06 else x / n
        y = np.cross(z, x)
        return Rotation.from_matrix(np.stack([x, y, z], axis=1)).as_quat()

    def guarded(task_module, env, payload, camera_info, task_state):
        result = original(task_module, env, payload, camera_info, task_state) or {}
        ov = result.get('camera_override') if isinstance(result, dict) else None
        try:
            if ov and ov.get('position') and ov.get('quaternion_xyzw'):
                pos = np.asarray(ov['position'], dtype=float)
                quat = np.asarray(ov['quaternion_xyzw'], dtype=float)
            else:
                pos, quat, _ = task_module.initial_camera(payload)
        except Exception:
            return result
        try:
            v = variance_at(pos, quat, 'check1')
            if v >= 12:
                if getattr(task_module, 'FULL_SCENE', False):
                    return result
                try:
                    objs = task_module.build_env_objects(payload) or []
                except Exception:
                    objs = []
                centers = []
                for o in objs:
                    name = o.get('name') if isinstance(o, dict) else None
                    actual = None
                    if name:
                        try:
                            ob = env.scene.object_registry('name', name)
                            if ob is not None:
                                actual = [float(x) for x in ob.get_position_orientation()[0]]
                        except Exception:
                            actual = None
                    if actual is None and isinstance(o, dict):
                        actual = o.get('position')
                    if actual:
                        centers.append(actual)
                if centers:
                    med = np.median(np.asarray(centers, dtype=float), axis=0)
                    centers = [c for c in centers if float(np.linalg.norm(np.asarray(c, float) - med)) < 10.0]
                if not centers:
                    return result
                center = np.mean(np.asarray(centers, dtype=float), axis=0)
                dist = float(np.linalg.norm(np.asarray(pos, float)[:2] - center[:2]))
                blocked = False
                try:
                    from omnigibson.utils.sampling_utils import raytest
                    hit = raytest(np.asarray(pos, float), center, only_closest=True)
                    blocked = bool(hit.get('hit')) and float(hit.get('distance', 1000000000.0)) < 0.85 * dist
                except Exception:
                    pass
                if dist <= 3.5 and (not blocked):
                    return result
                for cand in (center + np.array([0.0, -1.2, 0.8]), center + np.array([1.2, 0.0, 0.8]), center + np.array([0.01, 0.01, 2.2])):
                    q_c = lookat_quat(cand, center)
                    if variance_at(cand, q_c, 'target_fix') >= 12:
                        print(f"[机位自检] 目标距离 {dist:.1f}m{('、视线被挡' if blocked else '')} → 已移至目标附近 look-at 机位", flush=True)
                        result = dict(result)
                        result['camera_override'] = {'position': [float(x) for x in cand], 'quaternion_xyzw': [float(x) for x in q_c]}
                        return result
                print(f'[机位自检] 目标距离 {dist:.1f}m 但补救机位均无效，保留原机位', flush=True)
                return result
            import omnigibson as og
            for _ in range(20):
                og.sim.render()
            v2 = variance_at(pos, quat, 'check2')
            if v2 >= 12:
                if verbose:
                    print(f'[机位自检] 首帧方差 {v:.1f}，补渲染后恢复（{v2:.1f}），保留原机位', flush=True)
                return result
            objs = []
            try:
                objs = task_module.build_env_objects(payload) or []
            except Exception:
                pass
            centers = [o.get('position') for o in objs if isinstance(o, dict) and o.get('position')]
            if not centers:
                print(f'[机位自检] 首帧空白（方差 {v2:.1f}）但无物体坐标可参照，保留原机位', flush=True)
                return result
            center = np.mean(np.asarray(centers, dtype=float), axis=0)
            new_pos = center + np.array([0.0, -1.2, 0.8])
            new_quat = lookat_quat(new_pos, center)
            v3 = variance_at(new_pos, new_quat, 'check3')
            if v3 < 12:
                new_pos = center + np.array([1.2, 0.0, 0.8])
                new_quat = lookat_quat(new_pos, center)
                v3 = variance_at(new_pos, new_quat, 'check3b')
            if v3 < 12:
                new_pos = center + np.array([0.01, 0.01, 2.2])
                new_quat = lookat_quat(new_pos, center)
                v3 = variance_at(new_pos, new_quat, 'check3c')
            if v3 >= 12:
                print(f'[机位自检] 原机位空白（方差 {v2:.1f}）→ 已补救为 look-at 机位（方差 {v3:.1f}）', flush=True)
                result = dict(result)
                result['camera_override'] = {'position': [float(x) for x in new_pos], 'quaternion_xyzw': [float(x) for x in new_quat]}
            else:
                print(f'[机位自检] 原机位空白且补救失败（方差 {v3:.1f}），保留原机位', flush=True)
        except Exception as exc:
            print(f'[机位自检] 检查出错，跳过: {type(exc).__name__}: {exc}', flush=True)
        return result
    pipeline.task_postprocess_env = guarded

def _read_question(metadata: str) -> dict:
    import json
    try:
        data = json.loads((ROOT / metadata).read_text(encoding='utf-8'))
    except Exception as exc:
        return {'question': f'(读取失败: {type(exc).__name__})', 'answer': '?'}
    if data.get('task') == 'puzzlemix_escape':
        return {'level': data['level'], 'scene': data['scene'], 'room': data['start']['room'], 'small_task': 'PuzzleMixEscape'}
    options = data.get('options_json')
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except Exception:
            pass
    if isinstance(options, list):
        options = ' / '.join((str(o)[:28] for o in options[:6]))
    return {'question': data.get('question'), 'answer': data.get('answer'), 'options': options, 'scene': data.get('scene'), 'room': data.get('room'), 'small_task': data.get('small_task')}

def _rules_text(sent) -> str | None:
    try:
        from _tools import STATE as _TS
        rules = _TS.get('rules')
        if rules:
            return rules
    except Exception:
        pass
    return next((x['text'] for x in reversed(sent or []) if x.get('type') == 'text'), None)

def _plan_text() -> str | None:
    try:
        from _tools import STATE as _TS
        return _TS.get('plan') or None
    except Exception:
        return None

def _write_experiment_record(task: str, metadata: str, meta: dict, model: str) -> None:
    import json
    from models import qwen as _qwen
    results = sorted((ROOT / 'outputs' / 'results' / task).rglob('*_answer.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not results:
        print('[警告] 没找到 answer.json，实验记录未生成', flush=True)
        return
    try:
        answer = json.loads(results[0].read_text(encoding='utf-8'))
    except Exception as exc:
        print(f'[警告] 读取 answer.json 失败: {type(exc).__name__}: {exc}', flush=True)
        return
    records = [r for r in _qwen.THINKING if not r.get('inner')]
    history = answer.get('history', [])
    prompt = {}
    if records:
        sent = records[0].get('sent') or []
        prompt = {'system': records[0].get('system_instruction'), '任务提示词': _rules_text(sent)}
    轮次 = []
    for idx, step in enumerate(history):
        rec = records[idx] if idx < len(records) else {}
        看到 = [x['name'] for x in rec.get('sent') or [] if x.get('type') == 'image']
        rd = {'步': step.get('step'), '看到的图': 看到, '思考': rec.get('thinking') or '', '动作': step.get('action'), '当前答案': step.get('answer'), '置信度': step.get('confidence'), '理由': step.get('reasoning')}
        try:
            from _tools import STATE as _TS
            内 = (_TS.get('inner') or {}).get(step.get('step'))
            if 内:
                rd['内循环'] = [{'输出': o, '检索': r} for o, r in 内]
            slog = (_TS.get('steplog') or {}).get(step.get('step')) or {}
            if slog.get('det'):
                rd['检测'] = slog['det']
            if slog.get('look_dets') is not None:
                rd['环视检测'] = slog['look_dets']
            if slog.get('memory'):
                rd['记忆'] = slog['memory']
            pose = slog.get('pose')
            if pose:
                x_, y_, deg_ = (pose[0], pose[1], pose[2])
                pitch_ = pose[3] if len(pose) > 3 else 0
                gaze_ = 'level' if abs(pitch_) < 3 else f'{abs(pitch_)}° down' if pitch_ < 0 else f'{abs(pitch_)}° up'
                head_ = 'facing initial heading' if abs(deg_) < 1 else f"facing {abs(deg_)}° {('right' if deg_ > 0 else 'left')}"
                rd['位姿'] = f'({x_}, {y_}) {head_}, gaze {gaze_}'
        except Exception:
            pass
        轮次.append(rd)
    final = answer.get('final_answer', {})
    编号, 脚本名 = _script_id()
    record = {'编号': 编号, '脚本': 脚本名, '题目': {'任务': task, '子类': meta.get('small_task'), '场景': f"{meta.get('scene')} / {meta.get('room')}", '问题': meta.get('question'), '选项': meta.get('options'), '标准答案': meta.get('answer'), '题目文件': metadata}, '提示词': prompt, '模型': model, '轮次': 轮次, **({'计划': _plan_text()} if _plan_text() else {}), '结果': {'最终答案': final.get('answer'), '正确': answer.get('correct'), '步数': final.get('steps'), '停止原因': final.get('stopped_by')}}
    out_dir = ROOT / 'outputs' / 'experiments'
    out_dir.mkdir(parents=True, exist_ok=True)
    前缀 = f'{编号:02d}_' if 编号 is not None else ''
    out_path = out_dir / f'{前缀}{task}__{Path(metadata).stem}.json'
    flag = globals().get('_record_written_flag')
    if flag is not None:
        flag['written'] = True
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    mark = '答对' if answer.get('correct') else '答错' if answer.get('correct') is False else '未判分'
    print(f'\n实验记录 -> {out_path}', flush=True)
    print(f"  {mark} | {final.get('steps')} 步 | 停止: {final.get('stopped_by')}", flush=True)

def _install_hooks(pipeline) -> dict:
    from models.qwen import QwenModel
    state = {'step': 0, 't0': time.time(), 'tok_in': 0, 'tok_out': 0}

    def _patch_usage(client):
        if getattr(client, '_usage_patched', False):
            return
        orig_create = client.chat.completions.create

        def counting_create(*a, **kw):
            resp = orig_create(*a, **kw)
            u = getattr(resp, 'usage', None)
            if u is not None:
                state['tok_in'] += getattr(u, 'prompt_tokens', 0) or 0
                state['tok_out'] += getattr(u, 'completion_tokens', 0) or 0
            return resp
        client.chat.completions.create = counting_create
        client._usage_patched = True
    orig_generate = QwenModel.generate_json

    def verbose_generate(self, *args, **kwargs):
        state['step'] += 1
        _patch_usage(self.client)
        started = time.time()
        result = orig_generate(self, *args, **kwargs)
        parsed = result[0] if isinstance(result, tuple) else result

        def field(name, default=''):
            return parsed.get(name, default) if isinstance(parsed, dict) else default
        reasoning = str(field('reasoning')).replace('\n', ' ').strip()
        if len(reasoning) > 300:
            reasoning = reasoning[:300] + '…'
        if reasoning == 'parse fallback':
            finish = result[2] if isinstance(result, tuple) and len(result) > 2 else '?'
            raw_len = len(result[1]) if isinstance(result, tuple) and len(result) > 1 else 0
            print(f"\n⚠ 第 {state['step']} 步 解析失败，本步决策丢失（已兜底成 move_forward）", flush=True)
            print(f'   finish_reason={finish}  模型正文长度={raw_len}', flush=True)
            if finish == 'length':
                print('   原因：思考过程耗尽 token 预算，正文没写出来。调大 max_new_tokens。', flush=True)
            return result
        try:
            confidence = f"{float(field('confidence', 0)):.2f}"
        except (TypeError, ValueError):
            confidence = str(field('confidence'))
        print(f"\n─── 第 {state['step']} 步 （本步 {time.time() - started:.1f}s / 累计 {time.time() - state['t0']:.0f}s）", flush=True)
        print(f"  动作   : {field('action')}", flush=True)
        print(f"  当前答案: {field('answer')}   置信度: {confidence}", flush=True)
        print(f'  理由   : {reasoning}', flush=True)
        from models import qwen as _qwen
        if _qwen.THINKING:
            rec = _qwen.THINKING[-1]
            think = str(rec.get('thinking') or '').strip()
            if think:
                shown = think if len(think) <= 700 else think[:700] + f'…（共 {len(think)} 字符，完整内容见 answer.json）'
                print(f"  ── 思考（{rec.get('reasoning_tokens')} tokens）:", flush=True)
                for line in shown.splitlines():
                    if line.strip():
                        print(f'       {line}', flush=True)
        return result
    QwenModel.generate_json = verbose_generate
    orig_execute = pipeline.execute_action

    def verbose_execute(*args, **kwargs):
        pos, quat, action_result = orig_execute(*args, **kwargs)
        if isinstance(action_result, dict):
            shown = {k: action_result[k] for k in _INTERESTING_RESULT_KEYS if k in action_result}
            if shown:
                print('  ── 物理执行结果:', flush=True)
                for k, v in shown.items():
                    print(f'       {k} = {v}', flush=True)
        return (pos, quat, action_result)
    pipeline.execute_action = verbose_execute
    return state
