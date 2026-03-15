import logging

from .base import IAProviderMAIN, IAProviderError

logger = logging.getLogger("deepseek_provider")

# Modelos válidos en la API de DeepSeek (https://platform.deepseek.com/api-docs)
DEEPSEEK_VALID_MODELS = {"deepseek-chat", "deepseek-reasoner"}


class DeepSeekProvider(IAProviderMAIN):
    provider_name = "deepseek"

    @staticmethod
    def _validate_model(model: str) -> str:
        """Devuelve el modelo si es válido; en caso contrario usa deepseek-chat."""
        m = str(model or "").strip()
        if m in DEEPSEEK_VALID_MODELS:
            return m
        if m:
            logger.warning(
                "DeepSeek: modelo '%s' no es válido. Usando 'deepseek-chat'. "
                "Modelos soportados: %s",
                m,
                sorted(DEEPSEEK_VALID_MODELS),
            )
        # Modelo desconocido / vacío → caer al modelo por defecto seguro
        return "deepseek-chat"

    @staticmethod
    def _resolve_url(MAIN_url: str) -> str:
        """Devuelve la URL correcta del endpoint, descartando URLs de Ollama/locales."""
        url = str(MAIN_url or "").strip()
        # Descartar URLs que claramente son de Ollama u otros proveedores locales
        if not url or "11434" in url or "/api/generate" in url or "/api/tags" in url:
            return "https://api.deepseek.com/v1/chat/completions"
        if "/v1/" not in url and "/v1" not in url.rstrip("/"):
            return url.rstrip("/") + "/v1/chat/completions"
        return url

    def complete(self, prompt, **kwargs):
        url = self._resolve_url(self.MAIN_url)
        model = self._validate_model(kwargs.get("model") or self.model or "deepseek-chat")
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
                message="DeepSeek devolvió respuesta vacía",
                retryable=False,
                details=str(raw)[:1200],
            )
        return standardized
