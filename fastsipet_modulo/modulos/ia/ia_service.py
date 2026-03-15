"""
Orquestador robusto multi-proveedor IA.

Objetivos:
- Contrato unificado de respuesta.
- Fallback configurable por cadena/proveedor.
- Reintentos con backoff y normalización de errores.
- Metadatos de uso: tokens/costo/proveedor/modelo.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List
from urllib.parse import urlparse, urlunparse

from fastapi_modulo.db import IAConfig, SessionLocal
from .providers.base import IAProviderError
from .providers.deepseek_provider import DeepSeekProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider

logger = logging.getLogger("ia_service")

PROVIDERS = {
    "chatgpt": OpenAIProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "ollama": OllamaProvider,
}

ALIAS = {
    "chatgpt": "openai",
    "gpt": "openai",
    "gpt4": "openai",
    "deepseek": "deepseek",
    "ollama": "ollama",
}


def _normalize_ollama_generate_url(raw_url: str) -> str:
    raw = str(raw_url or "").strip()
    if not raw:
        return "http://127.0.0.1:11434/api/generate"
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    path = str(parsed.path or "").rstrip("/")
    if path in {"", "/api"}:
        parsed = parsed._replace(path="/api/generate")
    return urlunparse(parsed)


def get_ia_config():
    db = SessionLocal()
    try:
        return db.query(IAConfig).order_by(IAConfig.updated_at.desc()).first()
    finally:
        db.close()


def _normalize_provider_name(value: str) -> str:
    raw = str(value or "").strip().lower()
    raw = ALIAS.get(raw, raw)
    if raw in PROVIDERS:
        return raw
    return ""


def _to_int(value, default=30):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _to_float(value, default=0.0):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed


def _json_loads(value, default):
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except Exception:
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _provider_chain_from_value(raw_value: str) -> List[str]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        parsed = _json_loads(raw, [])
        return [p for p in (_normalize_provider_name(item) for item in parsed) if p]
    return [p for p in (_normalize_provider_name(item) for item in raw.split(",")) if p]


def _fallback_map() -> Dict[str, List[str]]:
    # Ejemplo: AI_PROVIDER_FALLBACK_MAP='{"openai":["deepseek","ollama"],"deepseek":["ollama"]}'
    raw = os.environ.get("AI_PROVIDER_FALLBACK_MAP", "")
    parsed = _json_loads(raw, {})
    fmap = {}
    for key, value in parsed.items():
        pkey = _normalize_provider_name(key)
        if not pkey:
            continue
        seq = []
        if isinstance(value, list):
            seq = [p for p in (_normalize_provider_name(item) for item in value) if p and p != pkey]
        elif isinstance(value, str):
            seq = [p for p in (_normalize_provider_name(item) for item in value.split(",")) if p and p != pkey]
        if seq:
            fmap[pkey] = seq
    return fmap


def _provider_chain(config) -> List[str]:
    # Prioridad:
    # 1) AI_PROVIDER_CHAIN
    # 2) ai_provider en DB (string/csv/json/hybrid)
    # 3) primary + fallback env
    env_chain = _provider_chain_from_value(os.environ.get("AI_PROVIDER_CHAIN", ""))
    if env_chain:
        return env_chain

    raw = str(getattr(config, "ai_provider", "") or "").strip()
    if not raw:
        raw = os.environ.get("AI_PRIMARY_PROVIDER", "openai")
    raw_norm = _normalize_provider_name(raw)

    if raw.lower() == "hybrid":
        primary = _normalize_provider_name(os.environ.get("AI_PRIMARY_PROVIDER", "ollama")) or "ollama"
        fallback = _normalize_provider_name(os.environ.get("AI_FALLBACK_PROVIDER", "deepseek"))
        chain = [primary]
        if fallback and fallback != primary:
            chain.append(fallback)
        return chain

    # json/csv provider chain in db
    chain_from_db = _provider_chain_from_value(raw)
    if chain_from_db:
        return chain_from_db

    primary = raw_norm or "openai"
    chain = [primary]
    fallback_env = _normalize_provider_name(os.environ.get("AI_FALLBACK_PROVIDER", ""))
    if fallback_env and fallback_env != primary:
        chain.append(fallback_env)
    extra_fallback = _fallback_map().get(primary, [])
    for provider in extra_fallback:
        if provider not in chain:
            chain.append(provider)
    return chain or ["openai"]


def _provider_settings(provider_name, config, is_primary=False):
    provider_key = _normalize_provider_name(provider_name)
    upper = provider_key.upper()

    # MAIN de configuración (DB)
    MAIN_api_key = str(getattr(config, "ai_api_key", "") or "")
    MAIN_url = str(getattr(config, "ai_MAIN_url", "") or "")
    MAIN_model = str(getattr(config, "ai_model", "") or "")
    MAIN_timeout = _to_int(getattr(config, "ai_timeout", 30), 30)
    MAIN_temperature = _to_float(getattr(config, "ai_temperature", 0.7), 0.7)
    MAIN_top_p = _to_float(getattr(config, "ai_top_p", 0.9), 0.9)
    MAIN_num_predict = _to_int(getattr(config, "ai_num_predict", 700), 700)

    # Override por proveedor desde env
    # MAIN_url de la DB pertenece al proveedor primario; proveedores secundarios
    # solo deben usarla si se especifica via env var propio (AI_{UPPER}_MAIN_URL).
    api_key = str(os.environ.get(f"AI_{upper}_API_KEY", "") or MAIN_api_key)
    endpoint = str(os.environ.get(f"AI_{upper}_MAIN_URL", "") or (MAIN_url if is_primary else ""))
    model = str(os.environ.get(f"AI_{upper}_MODEL", "") or (MAIN_model if is_primary else ""))
    timeout = _to_int(os.environ.get(f"AI_{upper}_TIMEOUT", ""), MAIN_timeout)

    # Primario respeta DB como primer valor (si existe)
    if is_primary:
        api_key = MAIN_api_key or api_key
        # Solo aplicar MAIN_url de DB al proveedor correcto:
        # no asignar una URL de Ollama a deepseek/openai ni viceversa
        _ollama_url_pattern = "11434" in MAIN_url or "/api/generate" in MAIN_url or "/api/tags" in MAIN_url
        if provider_key == "ollama" or not _ollama_url_pattern:
            endpoint = MAIN_url or endpoint
        model = MAIN_model or model
        timeout = _to_int(MAIN_timeout, timeout)

    # Defaults por proveedor
    if provider_key == "openai":
        endpoint = endpoint or "https://api.openai.com/v1/chat/completions"
        model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    elif provider_key == "deepseek":
        endpoint = endpoint or "https://api.deepseek.com/v1/chat/completions"
        model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    elif provider_key == "ollama":
        endpoint = endpoint or os.environ.get("OLLAMA_MAIN_URL", "http://127.0.0.1:11434/api/generate")
        endpoint = _normalize_ollama_generate_url(endpoint)
        model = model or os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

    retries = _to_int(os.environ.get(f"AI_{upper}_RETRIES", os.environ.get("AI_PROVIDER_RETRIES", "1")), 1)
    if retries > 6:
        retries = 6
    MAIN_backoff_ms = _to_int(os.environ.get("AI_RETRY_MAIN_MS", "350"), 350)
    max_backoff_ms = _to_int(os.environ.get("AI_RETRY_MAX_MS", "4000"), 4000)

    # Costos por 1k tokens (opcional)
    cost_in = _to_float(os.environ.get(f"AI_{upper}_COST_INPUT_PER_1K", "0"), 0.0)
    cost_out = _to_float(os.environ.get(f"AI_{upper}_COST_OUTPUT_PER_1K", "0"), 0.0)

    temperature = _to_float(os.environ.get(f"AI_{upper}_TEMPERATURE", ""), MAIN_temperature) if os.environ.get(f"AI_{upper}_TEMPERATURE") else MAIN_temperature
    top_p = _to_float(os.environ.get(f"AI_{upper}_TOP_P", ""), MAIN_top_p) if os.environ.get(f"AI_{upper}_TOP_P") else MAIN_top_p
    num_predict = _to_int(os.environ.get(f"AI_{upper}_NUM_PREDICT", ""), MAIN_num_predict) if os.environ.get(f"AI_{upper}_NUM_PREDICT") else MAIN_num_predict

    return {
        "api_key": api_key,
        "MAIN_url": endpoint,
        "model": model,
        "timeout": timeout,
        "retries": retries,
        "MAIN_backoff_ms": MAIN_backoff_ms,
        "max_backoff_ms": max_backoff_ms,
        "cost_input_per_1k": cost_in,
        "cost_output_per_1k": cost_out,
        "temperature": temperature,
        "top_p": top_p,
        "num_predict": num_predict,
    }


def get_provider_instance(provider_name=None, config=None, is_primary=False):
    cfg = config or get_ia_config()
    if not cfg:
        raise RuntimeError("No hay configuración IA disponible")
    target_provider = _normalize_provider_name(provider_name or getattr(cfg, "ai_provider", "openai")) or "openai"
    provider_cls = PROVIDERS.get(target_provider, OpenAIProvider)
    settings = _provider_settings(target_provider, cfg, is_primary=is_primary)
    return provider_cls(
        api_key=settings["api_key"],
        MAIN_url=settings["MAIN_url"],
        model=settings["model"],
        timeout=settings["timeout"],
    ), settings


def _normalize_result(result: Any, provider_name: str, model_name: str, meta: dict) -> dict:
    # Contrato único garantizado.
    if isinstance(result, dict):
        text_response = str(result.get("response") or "").strip()
        if not text_response:
            choices = result.get("choices")
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                text_response = str((choices[0].get("message") or {}).get("content") or choices[0].get("text") or "").strip()
        usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
        normalized = {
            "provider": str(result.get("provider") or provider_name),
            "model": str(result.get("model") or model_name),
            "response": text_response,
            "usage": {
                "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
                "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
            },
            "cost_estimated": float(result.get("cost_estimated", 0) or 0),
            "raw": result.get("raw") if "raw" in result else result,
            "meta": meta,
        }
    else:
        normalized = {
            "provider": provider_name,
            "model": model_name,
            "response": str(result or "").strip(),
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "cost_estimated": 0.0,
            "raw": {"raw": str(result)},
            "meta": meta,
        }

    # Compatibilidad extra con consumidores heredados
    if not normalized["response"] and isinstance(normalized.get("raw"), dict):
        raw = normalized["raw"]
        normalized["response"] = str(raw.get("response") or "").strip()
    normalized["choices"] = [{"message": {"content": normalized["response"]}, "text": normalized["response"]}]
    normalized["model_name"] = normalized["model"]
    return normalized


def complete_with_fallback(prompt, **kwargs):
    config = get_ia_config()
    if not config:
        raise RuntimeError("No hay configuración IA disponible")
    chain = _provider_chain(config)
    if not chain:
        chain = ["openai"]

    errors: List[dict] = []
    started_at = time.time()
    for index, provider_name in enumerate(chain):
        provider, settings = get_provider_instance(provider_name, config=config, is_primary=(index == 0))
        max_attempts = int(settings.get("retries", 1))
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("IA provider=%s attempt=%s/%s", provider_name, attempt, max_attempts)
                result = provider.complete(
                    prompt,
                    **kwargs,
                    cost_input_per_1k=settings.get("cost_input_per_1k", 0),
                    cost_output_per_1k=settings.get("cost_output_per_1k", 0),
                    temperature=kwargs.get("temperature") if "temperature" in kwargs else settings.get("temperature", 0.7),
                    top_p=kwargs.get("top_p") if "top_p" in kwargs else settings.get("top_p", 0.9),
                    max_tokens=kwargs.get("max_tokens") if "max_tokens" in kwargs else settings.get("num_predict", 700),
                )
                meta = {
                    "attempt": attempt,
                    "max_attempts_provider": max_attempts,
                    "provider_chain": chain,
                    "provider_index": index,
                    "elapsed_ms": int((time.time() - started_at) * 1000),
                }
                normalized = _normalize_result(
                    result=result,
                    provider_name=provider_name,
                    model_name=settings.get("model", ""),
                    meta=meta,
                )
                normalized["fallback_errors"] = errors
                return normalized
            except IAProviderError as exc:
                err = exc.to_dict()
                err.update({"attempt": attempt, "provider_index": index})
                errors.append(err)
                logger.warning("IA provider error: %s", err)
                if attempt < max_attempts and exc.retryable:
                    delay_ms = min(int(settings.get("MAIN_backoff_ms", 350)) * (2 ** (attempt - 1)), int(settings.get("max_backoff_ms", 4000)))
                    time.sleep(delay_ms / 1000.0)
                    continue
                break
            except Exception as exc:
                err = {
                    "provider": provider_name,
                    "kind": "unexpected",
                    "retryable": False,
                    "message": str(exc),
                    "attempt": attempt,
                    "provider_index": index,
                }
                errors.append(err)
                logger.warning("IA unexpected error: %s", err)
                break

    last_error = errors[-1] if errors else {"message": "Sin detalle"}
    details = str(last_error.get("details") or "").strip()
    kind = str(last_error.get("kind") or "").strip()
    detail_suffix = f" ({kind}: {details[:200]})" if details else (f" ({kind})" if kind else "")
    raise RuntimeError(f"No se pudo completar la solicitud IA. Último error: {last_error.get('message')}{detail_suffix}")
