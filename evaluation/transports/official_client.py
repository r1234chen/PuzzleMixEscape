from api_client import redact_json
from pathlib import Path
import os, sys, json, time, hashlib, base64, importlib.util, math, datetime
import httpx

class FatalAPI(BaseException):
    pass

def save(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(redact_json(obj), encoding='utf8')
    os.replace(t, p)

def retry_pause(root, serial, attempt, reason, payload_sha, headers=None):
    delay = [5, 15, 30, 60][min(attempt - 1, 3)]
    try:
        delay = max(delay, float((headers or {}).get('retry-after', '0')))
    except (ValueError, TypeError):
        pass
    save(Path(root) / 'API_RETRY_STATUS.json', {'phase': 'retry_wait', 'sequence': serial, 'attempt': attempt, 'reason': reason, 'same_payload_sha256': payload_sha, 'delay_seconds': delay, 'billing_unknown': True, 'model_action_advanced': False, 'recorded_at': datetime.datetime.now().astimezone().isoformat()})
    remaining = delay
    while remaining > 0:
        stop = os.environ.get('ESI_MODEL_STOP_FILE')
        if stop and Path(stop).exists():
            raise FatalAPI('User requested stop; pending input retained')
        chunk = min(1.0, remaining)
        time.sleep(chunk)
        remaining -= chunk

def transient_http(status, error):
    code = str(error.get('code') or '')
    typ = str(error.get('type') or '')
    if status in (408, 409, 500, 502, 503, 504):
        return True
    return status == 429 and (code == 'rate_limit_exceeded' or typ == 'rate_limit_error')

class OfficialClient:

    def __init__(self, root, model, base_gpt):
        self.root = Path(root)
        self.model = model
        self.base = base_gpt
        self.calls = []
        self.sequence = 0
        self.key = os.environ['OPENAI_API_KEY']
        self.http = httpx.Client(proxy=os.environ.get('PUZZLEMIX_OPENAI_PROXY'), trust_env=False, timeout=600.0)

    def generate(self, contents, system):
        self.sequence += 1
        serial = self.sequence
        meta = []
        parts = []
        for item in contents:
            if isinstance(item, Path):
                from PIL import Image
                with Image.open(item) as im:
                    if im.size != (640, 360):
                        raise FatalAPI('Model image is not640x360')
                raw = item.read_bytes()
                parts.append({'type': 'input_image', 'image_url': 'data:image/png;base64,' + base64.b64encode(raw).decode()})
                meta.append({'type': 'image', 'path': str(item), 'sha256': hashlib.sha256(raw).hexdigest(), 'size': [640, 360]})
            else:
                parts.append({'type': 'input_text', 'text': str(item)})
                meta.append({'type': 'text', 'text': str(item)})
        body = {'model': self.model, 'reasoning': {'effort': 'medium'}, 'input': [{'role': 'system', 'content': system}, {'role': 'user', 'content': parts}]}
        rawbody = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
        save(self.root / 'api' / ('%04d_request.json' % serial), {'model': self.model, 'provider': 'openai_official', 'url': 'https://api.openai.com/v1/responses', 'reasoning': body['reasoning'], 'other_parameters': 'provider defaults; no sampling/token/format/service tier overrides', 'system_instruction': system, 'contents': meta, 'payload_sha256': hashlib.sha256(rawbody).hexdigest(), 'credential_persisted': False})
        t = time.time()
        attempt = 0
        while True:
            attempt += 1
            try:
                r = self.http.post('https://api.openai.com/v1/responses', headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'}, content=rawbody)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as exc:
                save(self.root / 'api' / ('%04d_network_%02d.json' % (serial, attempt)), {'error': type(exc).__name__, 'attempt': attempt, 'same_payload_sha256': hashlib.sha256(rawbody).hexdigest(), 'billing_unknown': True})
                retry_pause(self.root, serial, attempt, type(exc).__name__, hashlib.sha256(rawbody).hexdigest())
                continue
            try:
                data = r.json()
            except ValueError:
                data = {'error': {'type': 'non_json_response', 'message': r.text[:1000].replace(self.key, '[REDACTED]')}}
            save(self.root / 'api' / ('%04d_response_%02d.json' % (serial, attempt)), {'http_status': r.status_code, 'request_id': r.headers.get('x-request-id'), 'seconds': round(time.time() - t, 3), 'response': data})
            if r.status_code != 200:
                err = data.get('error', {})
                kind = err.get('code') or err.get('type')
                if transient_http(r.status_code, err):
                    retry_pause(self.root, serial, attempt, 'HTTP ' + str(r.status_code) + ' ' + str(kind), hashlib.sha256(rawbody).hexdigest(), r.headers)
                    continue
                raise FatalAPI('OpenAI HTTP ' + str(r.status_code) + ' ' + str(kind) + '; no provider fallback; failed-request billing unknown')
            save(self.root / 'API_RETRY_STATUS.json', {'phase': 'request_completed', 'sequence': serial, 'attempts': attempt, 'same_payload_sha256': hashlib.sha256(rawbody).hexdigest(), 'failed_attempt_billing_unknown': attempt > 1})
            break
        text = ''.join((c.get('text', '') for o in data.get('output', []) if o.get('type') == 'message' for c in o.get('content', []) if c.get('type') == 'output_text')).strip()
        usage = data.get('usage') or {}
        parsed = self.base.extract_json_object(text)
        record = {'provider': 'openai_official', 'model': data.get('model'), 'requested_model': self.model, 'returned_model': data.get('model'), 'reasoning_effort': 'medium', 'response_id': data.get('id'), 'request_id': r.headers.get('x-request-id'), 'prompt_tokens': usage.get('input_tokens'), 'completion_tokens': usage.get('output_tokens'), 'cached_tokens': (usage.get('input_tokens_details') or {}).get('cached_tokens'), 'reasoning_tokens': (usage.get('output_tokens_details') or {}).get('reasoning_tokens'), 'seconds': round(time.time() - t, 3), 'content': text, 'thinking': '', 'finish_reason': data.get('status'), 'attempts': attempt, 'api_sequence': serial, 'sent': meta, 'system_instruction': system}
        self.calls.append(record)
        save(self.root / 'API_CALLS.json', self.calls)
        if not isinstance(parsed, dict) or not parsed.get('action'):
            raise FatalAPI('Official model response did not contain a complete action JSON; no invented action fallback')
        if data.get('status') != 'completed':
            raise FatalAPI('Official model response incomplete: ' + str(data.get('incomplete_details')))
        return (parsed, text, 'stop', record)

def install_qwen_transport(repo, support, root, model):
    sys.path[:0] = [str(Path(repo) / 'src/active_explore'), str(Path(repo) / 'src'), str(Path(repo) / 'run')]
    import models
    spec = importlib.util.spec_from_file_location('models.qwen', Path(support) / 'qwen_medium.py')
    q = importlib.util.module_from_spec(spec)
    sys.modules['models.qwen'] = q
    spec.loader.exec_module(q)
    models.qwen = q
    models.QwenModel = q.QwenModel
    gpt = sys.modules['models.gpt']
    client = OfficialClient(root, model, gpt)

    def init(self, api_key=None, model=model):
        from openai import OpenAI
        self.model = model
        self.openrouter = False
        self.client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url='https://api.openai.com/v1', http_client=httpx.Client(proxy=os.environ.get('PUZZLEMIX_OPENAI_PROXY'), trust_env=False, timeout=600.0), max_retries=0)

    def generate(self, contents, system_instruction, **kwargs):
        result, raw, fin, record = client.generate(contents, system_instruction)
        q.THINKING.append(record)
        return (result, raw, fin)
    q.QwenModel.__init__ = init
    q.QwenModel.generate_json = generate
    try:
        import active_explore.models as a
        a.qwen = q
        a.QwenModel = q.QwenModel
        sys.modules['active_explore.models.qwen'] = q
    except ImportError:
        pass
    return client
