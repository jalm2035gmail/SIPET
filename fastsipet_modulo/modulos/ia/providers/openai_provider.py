from .base import IAProviderMAIN, IAProviderError

class OpenAIProvider(IAProviderMAIN):
    provider_name = "openai"

    def complete(self, prompt, **kwargs):
        url = self.MAIN_url or "https://api.openai.com/v1/chat/completions"
        if "/v1/" not in url:
            url = url.rstrip("/") + "/v1/chat/completions"
        model = kwargs.get("model") or self.model or "gpt-4o-mini"
        max_tokens = int(kwargs.get("max_tokens", 700) or 700)
        temperature = float(kwargs.get("temperature", 0.7) or 0.7)
        top_p = float(kwargs.get("top_p", 0.9) or 0.9)
        messages = kwargs.get("messages")
        if not isinstance(messages, list) or not messages:
            messages = [{"role": "user", "content": str(prompt or "")}]
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        response_format = kwargs.get("response_format")
        if isinstance(response_format, dict):
            payload["response_format"] = response_format
        elif kwargs.get("json_mode"):
            payload["response_format"] = {"type": "json_object"}
        raw = self._http_post_json(url=url, payload=payload, headers=self._build_headers(include_auth=True), timeout=self.timeout)
        standardized = self._standardize_response(raw, str(prompt or ""), **kwargs)
        if not standardized.get("response"):
            raise IAProviderError(
                provider=self.provider_name,
                kind="empty_response",
                message="OpenAI devolvió respuesta vacía",
                retryable=False,
                details=str(raw)[:1200],
            )
        return standardized
