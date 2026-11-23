from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from openai import OpenAI
from .gpt import GPTModel, parse_json_response
BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
OPENROUTER_URL = 'https://openrouter.ai/api/v1'
DEFAULT_MODEL = 'qwen3-vl-plus'
THINKING: list[dict[str, Any]] = []
_PARSE_FAILED = '__parse_failed__'
_DIAG_DONE = [False]

def _openrouter_diag() -> None:
    pass

def reset_thinking() -> None:
    THINKING.clear()

class QwenModel(GPTModel):

    def __init__(self, api_key: str | None=None, model: str=DEFAULT_MODEL):
        self.openrouter = '/' in str(model)
        if self.openrouter:
            key = os.environ.get('OPENROUTER_API_KEY', '')
            if not key:
                raise ValueError('缺少 OpenRouter 密钥。请设置环境变量 OPENROUTER_API_KEY。')
            proxy = os.environ.get('ESI_OPENROUTER_PROXY')
            if proxy:
                import httpx
                self.client = OpenAI(api_key=key, base_url=OPENROUTER_URL, http_client=httpx.Client(proxy=proxy, timeout=600))
                print(f'  [OpenRouter] 经代理 {proxy} 访问', flush=True)
            else:
                self.client = OpenAI(api_key=key, base_url=OPENROUTER_URL)
        else:
            key = api_key if api_key is not None else os.environ.get('DASHSCOPE_API_KEY', '')
            if not key:
                raise ValueError('缺少 DashScope 密钥。请设置环境变量 DASHSCOPE_API_KEY，或用 --api-key 传入。')
            self.client = OpenAI(api_key=key, base_url=os.environ.get('DASHSCOPE_BASE_URL', BASE_URL))
        self.model = model

    def generate_json(self, contents: list[Any], system_instruction: str, response_schema: dict[str, Any] | None=None, max_output_tokens: int=1024, temperature: float=0.2, top_p: float=0.9, fallback: dict[str, Any] | None=None) -> tuple[dict[str, Any], str, str | None]:
        messages = [{'role': 'system', 'content': system_instruction}, {'role': 'user', 'content': self._convert_contents(contents)}]
        kwargs: dict[str, Any] = {'model': self.model, 'messages': messages}
        use_provider_defaults = self.openrouter and os.environ.get('ESI_MODEL_PARAMETERS') == 'default'
        if not use_provider_defaults:
            kwargs['max_completion_tokens'] = max_output_tokens
        if self.openrouter:
            kwargs['extra_body'] = {'reasoning': {'effort': 'medium'}}
        _tb = os.environ.get('ESI_QWEN_THINKING_BUDGET', '').strip()
        if _tb.isdigit() and (not self.openrouter):
            kwargs['extra_body'] = {'enable_thinking': True, 'thinking_budget': int(_tb)}
        if temperature is not None and (not self.openrouter):
            kwargs['temperature'] = temperature
        if top_p is not None and (not self.openrouter):
            kwargs['top_p'] = top_p

        def once():
            try:
                response = self.client.chat.completions.create(**kwargs)
            except Exception as exc0:
                if self.openrouter and 'not available in your region' in str(exc0):
                    _openrouter_diag()
                    raise
                kwargs.pop('temperature', None)
                kwargs.pop('top_p', None)
                response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            return (response, choice.message, (choice.message.content or '').strip(), str(getattr(choice, 'finish_reason', None)))
        response, message, raw_text, finish_reason = once()
        parsed = parse_json_response(raw_text, fallback={_PARSE_FAILED: True})
        first_attempt = None
        need_action = os.environ.get('ESI_REPLY_REQUIRE_ACTION') == '1'
        no_action = lambda p_: need_action and (not p_.get(_PARSE_FAILED)) and (not (isinstance(p_.get('action'), str) and p_.get('action').strip()))
        if parsed.get(_PARSE_FAILED) or no_action(parsed):
            u0 = getattr(response, 'usage', None)
            first_attempt = {'content': raw_text[:2000], 'finish_reason': finish_reason, 'prompt_tokens': getattr(u0, 'prompt_tokens', None), 'completion_tokens': getattr(u0, 'completion_tokens', None)}
            print(f"  [模型] 回复解析不出 JSON{('（解析出来没有 action）' if no_action(parsed) else '')}（finish={finish_reason}，{len(raw_text)} 字），原样重问一次", flush=True)
            response, message, raw_text, finish_reason = once()
            parsed = parse_json_response(raw_text, fallback={_PARSE_FAILED: True})
        if parsed.get(_PARSE_FAILED):
            parsed = parse_json_response(raw_text, fallback=fallback)
        sent = []
        for item in contents:
            if isinstance(item, Path):
                sent.append({'type': 'image', 'name': item.name})
            else:
                sent.append({'type': 'text', 'text': str(item)})
        usage = getattr(response, 'usage', None)
        details = getattr(usage, 'completion_tokens_details', None)
        entry = {'system_instruction': system_instruction, 'sent': sent, 'thinking': getattr(message, 'reasoning_content', None) or getattr(message, 'reasoning', None) or '', 'content': raw_text, 'finish_reason': finish_reason, 'prompt_tokens': getattr(usage, 'prompt_tokens', None), 'completion_tokens': getattr(usage, 'completion_tokens', None), 'reasoning_tokens': getattr(details, 'reasoning_tokens', None)}
        if first_attempt is not None:
            entry['retry_after_parse_failure'] = first_attempt
        THINKING.append(entry)
        return (parsed, raw_text, finish_reason)
