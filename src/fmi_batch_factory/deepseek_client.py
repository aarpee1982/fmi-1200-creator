from __future__ import annotations

import json
from typing import Any

import requests


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete_json(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 4000) -> dict[str, Any]:
        text = self.complete_text(system, user, temperature=temperature, max_tokens=max_tokens)
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def complete_text(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
