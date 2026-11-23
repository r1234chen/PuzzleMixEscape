import importlib.util
from functools import lru_cache
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROVIDERS = {
    "openai_official": ("OPENAI_API_KEY", "official_client.py"),
    "openrouter": ("OPENROUTER_API_KEY", "openrouter_client.py"),
    "dashscope": ("DASHSCOPE_API_KEY", "dashscope_client.py"),
}


def validate(provider, model, medium, proxy=None):
    if provider not in PROVIDERS or not model.strip():
        raise ValueError("Select an API-key provider and an explicit model ID")
    if provider == "dashscope":
        if model != "qwen3.8-max":
            raise ValueError("Only qwen3.8-max / thinking_budget=1024 is frozen here")
    elif not medium:
        raise ValueError("Confirm that this exact model supports medium reasoning first")
    if provider == "openrouter" and ("/" not in model or not proxy):
        raise ValueError("OpenRouter requires provider/model and PUZZLEMIX_OPENROUTER_PROXY")
    if proxy:
        from urllib.parse import urlsplit
        u = urlsplit(proxy)
        if u.scheme not in ("https", "http") or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError("Use an HTTP(S) proxy without embedded credentials")


@lru_cache(maxsize=None)
def module(provider):
    path = HERE / "transports" / PROVIDERS[provider][1]
    spec = importlib.util.spec_from_file_location("puzzlemix_" + provider, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def redact_json(value):
    import json
    text=json.dumps(value,ensure_ascii=False,indent=2,default=str)
    for name,_ in PROVIDERS.values():
        secret=os.environ.get(name)
        if secret:text=text.replace(secret,'[REDACTED]')
    return text


def install(provider, model, out, *, medium=False, proxy=None, stop=None):
    validate(provider, model, medium, proxy)
    if not os.environ.get(PROVIDERS[provider][0]):
        raise ValueError("Missing process environment variable: " + PROVIDERS[provider][0])
    os.environ["ESI_MODEL_PARAMETERS"] = "default"
    os.environ["ESI_REPLY_REQUIRE_ACTION"] = "1"
    os.environ["ESI_MODEL_STOP_FILE"] = str(stop or Path(out) / "STOP")
    if provider == "openrouter":
        os.environ["ESI_OPENROUTER_PROXY"] = proxy
    if provider == "dashscope":
        os.environ["ESI_QWEN_THINKING_BUDGET"] = "1024"
    return module(provider).install_qwen_transport(HERE / "client_base", HERE / "client_base", Path(out), model)
