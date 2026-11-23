import base64
import hashlib
import os
import time
from pathlib import Path

import httpx
from PIL import Image

from api_client import PROVIDERS, validate

URLS = {
    "openai_official": "https://api.openai.com/v1/responses",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
}


class KeyTransport:
    def __init__(self, plan, http=None):
        self.provider = plan["provider"]
        self.model = plan["model"]
        validate(self.provider, self.model, plan["medium_support_confirmed"], plan.get("proxy"))
        self.key = os.environ.get(PROVIDERS[self.provider][0])
        if not self.key:
            raise ValueError("Missing " + PROVIDERS[self.provider][0])
        proxy = plan.get("proxy") if self.provider == "openrouter" else os.environ.get("PUZZLEMIX_OPENAI_PROXY") if self.provider == "openai_official" else None
        self.http = http if http is not None else httpx.Client(trust_env=False, proxy=proxy, timeout=600, follow_redirects=False)

    def request(self, role, step, system, contents):
        official = self.provider == "openai_official"
        parts, sent = [], []
        for x in contents:
            if isinstance(x, Path):
                with Image.open(x) as image:
                    if image.format != "PNG" or image.size != (640, 360):
                        raise ValueError("Expected an original 640x360 PNG")
                raw = x.read_bytes()
                url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
                parts.append({"type":"input_image","image_url":url} if official else {"type":"image_url","image_url":{"url":url}})
                sent.append({"type":"image","path":str(x),"sha256":hashlib.sha256(raw).hexdigest(),"size":[640,360]})
            elif isinstance(x,str):
                parts.append({"type":"input_text" if official else "text","text":x})
                sent.append({"type":"text","text":x})
            else:
                raise TypeError("Unexpected observation component")
        if official:
            body={"model":self.model,"instructions":system,"input":[{"role":"user","content":parts}],"reasoning":{"effort":"medium"},"store":False}
        else:
            body={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":parts}]}
            body.update({"reasoning":{"effort":"medium"}} if self.provider=="openrouter" else {"enable_thinking":True,"thinking_budget":1024})
        start=time.monotonic()
        resp=self.http.post(URLS[self.provider],json=body,headers={"Authorization":"Bearer "+self.key})
        if resp.status_code!=200:
            raise RuntimeError(f"{self.provider} HTTP {resp.status_code} on {role} request; no fallback or action executed")
        data=resp.json()
        if official:
            if data.get("status")!="completed":raise ValueError("Incomplete response")
            text="".join(c.get("text","") for m in data.get("output",[]) if m.get("type")=="message" for c in m.get("content",[]) if c.get("type")=="output_text")
        else:
            choice=data["choices"][0]
            if choice.get("finish_reason")!="stop":raise ValueError("Incomplete response")
            text=choice["message"]["content"]
        if not isinstance(text,str) or not text.strip():raise ValueError("Empty response")
        usage=data.get("usage") or {}
        return {"provider":self.provider,"access_method":"api_key","model":self.model,"returned_model":data.get("model"),"agent_role":role,"api_sequence":2*step-(role=="memory"),"system_instruction":system,"sent":sent,"content":text,"prompt_tokens":usage.get("input_tokens",usage.get("prompt_tokens")),"completion_tokens":usage.get("output_tokens",usage.get("completion_tokens")),"reasoning_effort":None if self.provider=="dashscope" else "medium","thinking_budget":1024 if self.provider=="dashscope" else None,"seconds":time.monotonic()-start,"finish_reason":"stop","response_id":data.get("id")}
