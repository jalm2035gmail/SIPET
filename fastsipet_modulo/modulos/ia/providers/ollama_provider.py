import json
from urllib import request as _urllib_request, error as _urllib_error

from .base import IAProviderBase, IAProviderError


class OllamaProvider(IAProviderBase):
    provider_name = "ollama"

    def _base_host(self) -> str:
        """Devuelve el host base de Ollama (sin path)."""
        raw = self.base_url or "http://127.0.0.1:11434/api/generate"
        # Extraer scheme+host: http://host:port
        parts = raw.split("/")
        return "/".join(parts[:3])  # "http://127.0.0.1:11434"

    def _list_local_models(self) -> list[str]:
        """Consulta /api/tags y devuelve los nombres de modelos disponibles."""
        try:
            tags_url = f"{self._base_host()}/api/tags"
            req = _urllib_request.Request(tags_url, method="GET")
            with _urllib_request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            models = data.get("models") or []
            return [str(m.get("name") or m.get("model") or "") for m in models if m]
        except Exception:
            return []

    def _do_generate(self, url: str, model: str, prompt: str, max_tokens: int, temperature: float, top_p: float = 0.9) -> dict:
        data = {
            "model": model,
            "prompt": str(prompt or ""),
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            },
        }
        return self._http_post_json(url=url, payload=data, headers=self._build_headers(include_auth=False), timeout=self.timeout)

    def complete(self, prompt, **kwargs):
        url = self.base_url or "http://127.0.0.1:11434/api/generate"
        model = kwargs.get("model") or self.model or "llama3.1:8b"
        max_tokens = int(kwargs.get("max_tokens", 700) or 700)
        temperature = float(kwargs.get("temperature", 0.7) or 0.7)
        top_p = float(kwargs.get("top_p", 0.9) or 0.9)

        try:
            raw = self._do_generate(url, model, prompt, max_tokens, temperature, top_p)
        except IAProviderError as exc:
            # Si el modelo no existe (404), intentar con el primer modelo disponible
            if exc.status_code == 404 and "not found" in str(exc.details).lower():
                available = self._list_local_models()
                if available:
                    fallback_model = available[0]
                    try:
                        raw = self._do_generate(url, fallback_model, prompt, max_tokens, temperature, top_p)
                        model = fallback_model  # actualizar para el response
                    except IAProviderError:
                        raise IAProviderError(
                            provider=self.provider_name,
                            kind="model_not_found",
                            message=f"ollama: modelo '{model}' no encontrado. Disponibles: {', '.join(available[:5])}",
                            status_code=404,
                            retryable=False,
                            details=f"Se intentó con '{fallback_model}' y también falló.",
                        )
                else:
                    raise IAProviderError(
                        provider=self.provider_name,
                        kind="model_not_found",
                        message=f"ollama: modelo '{model}' no encontrado y no hay modelos instalados",
                        status_code=404,
                        retryable=False,
                        details="Ejecute 'ollama pull <modelo>' en el servidor para instalar un modelo.",
                    )
            else:
                raise

        # Normalizar métricas
        if isinstance(raw, dict) and "usage" not in raw:
            raw["usage"] = {
                "prompt_tokens": int(raw.get("prompt_eval_count", 0) or 0),
                "completion_tokens": int(raw.get("eval_count", 0) or 0),
                "total_tokens": int((raw.get("prompt_eval_count", 0) or 0) + (raw.get("eval_count", 0) or 0)),
            }
            raw["model"] = str(raw.get("model") or model)
        standardized = self._standardize_response(raw, str(prompt or ""), **kwargs)
        if not standardized.get("response"):
            raise IAProviderError(
                provider=self.provider_name,
                kind="empty_response",
                message="Ollama devolvió respuesta vacía",
                retryable=False,
                details=str(raw)[:1200],
            )
        return standardized
