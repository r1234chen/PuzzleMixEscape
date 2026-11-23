from api_client import redact_json
from pathlib import Path
import sys, os, json, time, copy, hashlib, importlib.util
import httpx

class FatalAPI(BaseException):
    pass

def save(p, v):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    q = p.with_suffix(p.suffix + '.tmp')
    q.write_text(redact_json(v), 'utf8')
    os.replace(q, p)

class Recorder:

    def __init__(self, root, model):
        self.root = Path(root)
        self.model = model
        self.calls = []
        self.sequence = 0
        self.transports = []
        self.last_parameters = {}

def install_qwen_transport(repo, support, root, model):
    if '/' not in model:
        raise ValueError('Provider/model OpenRouter identifier required')
    proxy = os.environ.get('ESI_OPENROUTER_PROXY')
    if not proxy:
        raise FatalAPI('OpenRouter must use the confirmed Clash proxy; direct connection disabled')
    sys.path[:0] = [str(Path(repo) / 'src/active_explore'), str(Path(repo) / 'src'), str(Path(repo) / 'run')]
    import models
    p = Path(support) / 'qwen_medium.py'
    if hashlib.sha256(p.read_bytes()).hexdigest() != '86e982594c48b278afccad09ab62000b3af1d92588e15370b9c136ed4c40692d':
        raise FatalAPI('Verified model client source changed')
    spec = importlib.util.spec_from_file_location('models.qwen', p)
    q = importlib.util.module_from_spec(spec)
    sys.modules['models.qwen'] = q
    spec.loader.exec_module(q)
    models.qwen = q
    models.QwenModel = q.QwenModel
    rec = Recorder(root, model)
    legacy = q.QwenModel.generate_json
    base = sys.modules['models.gpt']

    def init(self, api_key=None, model=model):
        from openai import OpenAI
        key = os.environ.get('OPENROUTER_API_KEY', '')
        if not key:
            raise FatalAPI('OPENROUTER_API_KEY is not set')
        self.openrouter = True
        self.model = rec.model
        self.client = OpenAI(api_key=key, base_url=q.OPENROUTER_URL, max_retries=0, http_client=httpx.Client(proxy=proxy, trust_env=False, timeout=600.0))
        original = self.client.chat.completions.create

        def create(*args, **kwargs):
            if kwargs.get('extra_body') != {'reasoning': {'effort': 'medium'}} or any((k in kwargs for k in ['temperature', 'top_p', 'response_format', 'max_completion_tokens', 'service_tier'])):
                raise FatalAPI('OpenRouter provider-default/medium contract changed')
            rec.sequence += 1
            serial = rec.sequence
            raw = json.dumps(kwargs, ensure_ascii=False, separators=(',', ':')).encode()
            digest = hashlib.sha256(raw).hexdigest()
            parameters = {k: v for k, v in kwargs.items() if k != 'messages'}
            rec.last_parameters = copy.deepcopy(parameters)
            save(Path(root) / 'api' / ('%04d_request.json' % serial), {'provider': 'openrouter', 'parameters': parameters, 'payload_sha256': digest, 'credential_persisted': False, 'proxy_required': True})
            attempt = 0
            while True:
                attempt += 1
                stop = os.environ.get('ESI_MODEL_STOP_FILE')
                if stop and Path(stop).exists():
                    raise FatalAPI('User stopped original OpenRouter request')
                try:
                    response = original(*args, **kwargs)
                except Exception as exc:
                    status = getattr(exc, 'status_code', None)
                    transient = isinstance(exc, (httpx.NetworkError, httpx.TimeoutException, httpx.ProtocolError)) or type(exc).__name__ in ['APIConnectionError', 'APITimeoutError'] or (status is not None and (status >= 500 or status in (408, 409, 429)))
                    text = str(exc).replace(key, '[REDACTED]')
                    save(Path(root) / 'api' / ('%04d_error_%02d.json' % (serial, attempt)), {'status': status, 'type': type(exc).__name__, 'message': text[:1200], 'payload_sha256': digest, 'billing_unknown': True})
                    if status == 429 and any((x in text.lower() for x in ['insufficient_quota', 'credit balance', 'unpaid', 'billing'])):
                        transient = False
                    if not transient:
                        raise FatalAPI('OpenRouter request rejected; ' + str(status) + '; no provider/parameter fallback')
                    delay = (5, 15, 30, 60)[min(attempt - 1, 3)]
                    save(Path(root) / 'API_RETRY_STATUS.json', {'phase': 'retry_wait', 'sequence': serial, 'attempt': attempt, 'delay_seconds': delay, 'same_payload_sha256': digest, 'model_action_advanced': False})
                    for _ in range(delay):
                        if stop and Path(stop).exists():
                            raise FatalAPI('User stopped original request')
                        time.sleep(1)
                    continue
                data = response.model_dump(mode='json')
                save(Path(root) / 'api' / ('%04d_response_%02d.json' % (serial, attempt)), {'provider': 'openrouter', 'response': data, 'failed_request_billing_unknown': attempt > 1})
                rec.transports.append({'sequence': serial, 'attempts': attempt, 'parameters': parameters, 'payload_sha256': digest})
                return response
        self.client.chat.completions.create = create

    def generate(self, contents, system_instruction, **kwargs):
        started = time.time()
        first = len(rec.transports)
        sent = []
        for value in contents:
            if isinstance(value, Path):
                from PIL import Image
                with Image.open(value) as im:
                    if im.size != (640, 360):
                        raise FatalAPI('Model input is not actual640x360')
                sent.append({'type': 'image', 'path': str(value), 'sha256': hashlib.sha256(value.read_bytes()).hexdigest(), 'size': [640, 360]})
            else:
                sent.append({'type': 'text', 'text': str(value)})
        parsed, text, finish = legacy(self, contents, system_instruction, **kwargs)
        strict = base.extract_json_object(text)
        entry = copy.deepcopy(q.THINKING[-1])
        record = dict(entry, provider='openrouter', model=rec.model, reasoning_effort='medium', seconds=round(time.time() - started, 3), parameters=copy.deepcopy(rec.last_parameters), transport_requests=rec.transports[first:], sent=sent)
        rec.calls.append(record)
        save(Path(root) / 'API_CALLS.json', rec.calls)
        if not isinstance(strict, dict) or not strict.get('action') or strict != parsed:
            raise FatalAPI('No complete action JSON; parser fallback is not executable')
        return (parsed, text, finish)
    q.QwenModel.__init__ = init
    q.QwenModel.generate_json = generate
    return rec
