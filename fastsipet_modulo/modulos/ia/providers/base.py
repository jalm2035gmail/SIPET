"""
Base robusta para proveedores IA.
Contrato único:
- complete(prompt, **kwargs) -> dict con "response", "usage", "provider", "model", etc.
"""

from __future__ import annotations

import json
import math
import socket
from urllib import error, request


class IAProviderError(Exception):
    def __init__(self, provider: str, kind: str, message: str, status_code: int | None = None, retryable: bool = False, details: str = ""):
        super().__init__(message)
        self.provider = str(provider or "").strip().lower()
        self.kind = str(kind or "unknown")
        self.status_code = int(status_code) if status_code is not None else None
        self.retryable = bool(retryable)
        self.details = str(details or "")

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "kind": self.kind,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "message": str(self),
            "details": self.details,
        }


class IAProviderBase:
    provider_name = "generic"

    def __init__(self, api_key, base_url=None, model=None, timeout=30):
        self.api_key = str(api_key or "")
        self.base_url = str(base_url or "")
        self.model = str(model or "")
        try:
            timeout_num = int(timeout)
        except (TypeError, ValueError):
            timeout_num = 30
        self.timeout = timeout_num if timeout_num > 0 else 30

    def complete(self, prompt, **kwargs):
        raise NotImplementedError()

    def health(self):
        return True

    def _build_headers(self, include_auth: bool = True) -> dict:
        headers = {"Content-Type": "application/json"}
        if include_auth and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _http_post_json(self, url: str, payload: dict, headers: dict | None = None, timeout: int | None = None) -> dict:
        body = json.dumps(payload or {}).encode("utf-8")
        req = request.Request(url, data=body, headers=headers or self._build_headers(), method="POST")
        try:
            with request.urlopen(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                return json.loads(raw or "{}")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            status = int(getattr(exc, "code", 0) or 0)
            retryable = status in {408, 409, 425, 429, 500, 502, 503, 504}
            raise IAProviderError(
                provider=self.provider_name,
                kind="http_error",
                message=f"{self.provider_name} HTTP {status}",
                status_code=status,
                retryable=retryable,
                details=details[:1000],
            ) from exc
        except error.URLError as exc:
            reason = str(getattr(exc, "reason", exc))
            raise IAProviderError(
                provider=self.provider_name,
                kind="network_error",
                message=f"{self.provider_name} no disponible",
                retryable=True,
                details=reason,
            ) from exc
        except socket.timeout as exc:
            raise IAProviderError(
                provider=self.provider_name,
                kind="timeout",
                message=f"{self.provider_name} timeout",
                retryable=True,
                details=str(exc),
            ) from exc
        except Exception as exc:
            raise IAProviderError(
                provider=self.provider_name,
                kind="unknown_error",
                message=f"Error no controlado en {self.provider_name}",
                retryable=False,
                details=str(exc),
            ) from exc

    def _extract_text(self, raw: dict) -> str:
        if not isinstance(raw, dict):
            return str(raw or "").strip()
        if isinstance(raw.get("response"), str):
            return raw.get("response", "").strip()
        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] or {}
            if isinstance(first, dict):
                if isinstance(first.get("text"), str):
                    return first.get("text", "").strip()
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content.strip()
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if isinstance(item, dict):
                                txt = item.get("text")
                                if isinstance(txt, str):
                                    parts.append(txt.strip())
                        if parts:
                            return "\n".join([part for part in parts if part]).strip()
        if isinstance(raw.get("output_text"), str):
            return raw.get("output_text", "").strip()
        if isinstance(raw.get("text"), str):
            return raw.get("text", "").strip()
        return ""

    def _estimate_tokens(self, text_in: str) -> int:
        length = len(str(text_in or ""))
        return max(1, int(math.ceil(length / 4.0)))

    def _normalize_usage(self, raw: dict, prompt_text: str, output_text: str) -> dict:
        usage = raw.get("usage") if isinstance(raw, dict) else None
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
            total_tokens = usage.get("total_tokens")
        if prompt_tokens is None:
            prompt_tokens = self._estimate_tokens(prompt_text)
        if completion_tokens is None:
            completion_tokens = self._estimate_tokens(output_text)
        if total_tokens is None:
            total_tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
        return {
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
        }

    def _estimate_cost(self, usage: dict, kwargs: dict) -> float:
        try:
            in_rate = float(kwargs.get("cost_input_per_1k", 0) or 0)
            out_rate = float(kwargs.get("cost_output_per_1k", 0) or 0)
        except (TypeError, ValueError):
            in_rate = 0.0
            out_rate = 0.0
        return round(((usage.get("prompt_tokens", 0) / 1000.0) * in_rate) + ((usage.get("completion_tokens", 0) / 1000.0) * out_rate), 8)

    def _standardize_response(self, raw: dict, prompt_text: str, **kwargs) -> dict:
        text_out = self._extract_text(raw)
        usage = self._normalize_usage(raw if isinstance(raw, dict) else {}, prompt_text, text_out)
        cost_estimated = self._estimate_cost(usage, kwargs)
        model = self.model
        if isinstance(raw, dict):
            model = str(raw.get("model") or raw.get("model_name") or model or "")
        return {
            "provider": self.provider_name,
            "model": model,
            "response": text_out,
            "usage": usage,
            "cost_estimated": cost_estimated,
            "raw": raw if isinstance(raw, dict) else {"raw": str(raw)},
        }
