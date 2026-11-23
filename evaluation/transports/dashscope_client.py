from api_client import redact_json
from pathlib import Path
import os, sys, json, time, hashlib, importlib.util, copy, datetime
import httpx
from openai import OpenAI

class FatalAPI(BaseException):
    pass

def save(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(redact_json(data), encoding='utf8')
    os.replace(t, p)

def sha(data):
    return hashlib.sha256(data).hexdigest()

class Recorder:

    def __init__(self, root, model):
        self.root = Path(root)
        self.model = model
        self.calls = []
        self.sequence = 0
        self.last_parameters = {}
        self.transports = []

    def pause(self, serial, attempt, reason, digest):
        delay = [5, 15, 30, 60][min(attempt - 1, 3)]
        save(self.root / 'API_RETRY_STATUS.json', {'phase': 'retry_wait', 'sequence': serial, 'attempt': attempt, 'reason': reason, 'same_payload_sha256': digest, 'delay_seconds': delay, 'billing_unknown': True, 'action_advanced': False})
        for _ in range(delay):
            stop = os.environ.get('ESI_MODEL_STOP_FILE')
            if stop and Path(stop).exists():
                raise FatalAPI('User requested stop; Qwen original input retained')
            time.sleep(1)

    def install_create(self, client, key):
        original = client.chat.completions.create

        def create(*args, **kwargs):
            assert kwargs['model'] == self.model and kwargs.get('extra_body', {}).get('thinking_budget') == 1024 and (kwargs['extra_body'].get('enable_thinking') is True)
            assert 'reasoning_effort' not in kwargs and 'reasoning' not in kwargs.get('extra_body', {})
            assert 'response_format' not in kwargs, 'Keep the previously verified no-JSON-mode policy'
            self.sequence += 1
            serial = self.sequence
            body = json.dumps(kwargs, ensure_ascii=False, separators=(',', ':'), default=str).encode()
            digest = sha(body)
            params = {k: v for k, v in kwargs.items() if k != 'messages'}
            self.last_parameters = copy.deepcopy(params)
            save(self.root / 'api' / ('%04d_request.json' % serial), {'provider': 'dashscope', 'url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', 'parameters': params, 'payload_sha256': digest, 'messages_roles': [x['role'] for x in kwargs['messages']], 'credential_persisted': False, 'direct_no_system_proxy': True})
            attempt = 0
            while True:
                attempt += 1
                t = time.time()
                try:
                    response = original(*args, **kwargs)
                except Exception as exc:
                    status = getattr(exc, 'status_code', None)
                    message = str(exc).replace(key, '[REDACTED]')
                    low = message.lower()
                    code = None
                    raw = getattr(exc, 'response', None)
                    try:
                        error = raw.json()
                        code = (error.get('error') or {}).get('code') or error.get('code')
                    except Exception:
                        error = {'error': message[:1500]}
                    save(self.root / 'api' / ('%04d_error_%02d.json' % (serial, attempt)), {'status': status, 'error_type': type(exc).__name__, 'error': json.loads(json.dumps(error, default=str).replace(key, '[REDACTED]')), 'payload_sha256': digest, 'billing_unknown': True, 'seconds': round(time.time() - t, 3)})
                    image_timeout = 'download multimodal file timed out' in low or ('multimodal' in low and 'download' in low and ('timed out' in low))
                    transient = status in [408, 409, 500, 502, 503, 504] or isinstance(exc, (httpx.NetworkError, httpx.TimeoutException, httpx.ProtocolError)) or type(exc).__name__ in ['APIConnectionError', 'APITimeoutError'] or image_timeout
                    if status == 429:
                        transient = not any((word in low for word in ['insufficient_quota', 'arrearage', 'unpaid', 'credit balance', 'billing', 'account balance']))
                    if transient:
                        self.pause(serial, attempt, 'HTTP ' + str(status) + ' ' + type(exc).__name__, digest)
                        continue
                    if status == 400 and any((x in low for x in ['temperature', 'top_p'])) and any((x in low for x in ['not support', 'unsupported', 'invalid'])):
                        raise
                    raise FatalAPI('DashScope ' + str(status) + ' ' + str(code) + '; original input retained; no model/provider fallback')
                data = response.model_dump(mode='json') if hasattr(response, 'model_dump') else json.loads(response.model_dump_json())
                save(self.root / 'api' / ('%04d_response_%02d.json' % (serial, attempt)), {'provider': 'dashscope', 'seconds': round(time.time() - t, 3), 'response': data, 'failed_attempt_billing_unknown': attempt > 1})
                self.transports.append({'sequence': serial, 'attempts': attempt, 'payload_sha256': digest, 'parameters': params})
                save(self.root / 'API_RETRY_STATUS.json', {'phase': 'request_completed', 'sequence': serial, 'attempts': attempt, 'same_payload_sha256': digest})
                return response
        client.chat.completions.create = create

def install_qwen_transport(repo, support, root, model):
    assert model == 'qwen3.8-max' and os.environ.get('ESI_QWEN_THINKING_BUDGET') == '1024'
    sys.path[:0] = [str(Path(repo) / 'src/active_explore'), str(Path(repo) / 'src'), str(Path(repo) / 'run')]
    import models
    p = Path(support) / 'qwen_medium.py'
    assert sha(p.read_bytes()) == '86e982594c48b278afccad09ab62000b3af1d92588e15370b9c136ed4c40692d'
    spec = importlib.util.spec_from_file_location('models.qwen', p)
    q = importlib.util.module_from_spec(spec)
    sys.modules['models.qwen'] = q
    spec.loader.exec_module(q)
    models.qwen = q
    models.QwenModel = q.QwenModel
    rec = Recorder(root, model)
    legacy_generate = q.QwenModel.generate_json
    base = sys.modules['models.gpt']

    def init(self, api_key=None, model=None):
        key = os.environ.get('DASHSCOPE_API_KEY', '')
        assert key.startswith('sk-') and (not key.startswith(('sk-proj-', 'sk-or-')))
        self.openrouter = False
        self.model = rec.model
        self.client = OpenAI(api_key=key, base_url='https://dashscope.aliyuncs.com/compatible-mode/v1', max_retries=0, http_client=httpx.Client(trust_env=False, timeout=600.0))
        rec.install_create(self.client, key)

    def generate(self, contents, system_instruction, **kwargs):
        start = time.time()
        first = len(rec.transports)
        sent = []
        for v in contents:
            if isinstance(v, Path):
                from PIL import Image
                with Image.open(v) as im:
                    assert im.size == (640, 360)
                sent.append({'type': 'image', 'path': str(v), 'size': [640, 360], 'sha256': sha(v.read_bytes())})
            else:
                sent.append({'type': 'text', 'text': str(v)})
        save(Path(root) / 'api' / ('decision_%04d_input.json' % (len(rec.calls) + 1)), {'provider': 'dashscope', 'model': rec.model, 'system_instruction': system_instruction, 'contents': sent, 'thinking_budget': 1024})
        parsed, text, finish = legacy_generate(self, contents, system_instruction, **kwargs)
        entry = copy.deepcopy(q.THINKING[-1])
        strict = base.extract_json_object(text)
        record = dict(entry, provider='dashscope', model=rec.model, thinking_budget=1024, seconds=round(time.time() - start, 3), parameters=copy.deepcopy(rec.last_parameters), transport_requests=rec.transports[first:], sent=sent)
        rec.calls.append(record)
        save(Path(root) / 'API_CALLS.json', rec.calls)
        if not isinstance(strict, dict) or not isinstance(strict.get('action'), str) or (not strict['action'].strip()) or (parsed != strict):
            raise FatalAPI('Qwen response has no complete action JSON; never execute parser-invented fallback')
        return (parsed, text, finish)
    q.QwenModel.__init__ = init
    q.QwenModel.generate_json = generate
    try:
        import active_explore.models as m
        m.qwen = q
        m.QwenModel = q.QwenModel
        sys.modules['active_explore.models.qwen'] = q
    except ImportError:
        pass
    return rec
