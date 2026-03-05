"""
image_utils.py — Optimización de imágenes subidas al servidor.

Redimensiona y convierte a WebP con calidad mínima suficiente.
Los SVG se pasan sin cambios. Los archivos originales nunca se escriben
a disco; sólo se guarda el resultado optimizado.
"""
from __future__ import annotations

import io
from typing import Tuple, Optional

# Perfiles de optimización por tipo de uso
_PROFILES: dict[str, Tuple[int, int, int]] = {
    # (max_width, max_height, webp_quality)
    "avatar":      (300,  300,  82),   # fotos de colaboradores
    "favicon":     (256,  256,  85),   # favicon institucional
    "logo":        (800,  800,  85),   # logo empresa / login
    "background":  (1920, 1080, 78),   # fondos escritorio / móvil
    "asset":       (1200, 1200, 82),   # assets genéricos de personalización
    "default":     (1200, 1200, 82),
}


def optimize_image(
    data: bytes,
    original_ext: str,
    profile: str = "default",
) -> Tuple[bytes, str]:
    """
    Recibe los bytes originales y la extensión (.png/.jpg/etc.) y devuelve
    (bytes_optimizados, nueva_extension).

    - SVG → devuelve sin modificar con ext ".svg"
    - El resto → WebP optimizado redimensionado según el perfil
    - Si Pillow no está disponible → devuelve los bytes originales sin cambio
    """
    ext = (original_ext or "").lower().strip()
    if not ext.startswith("."):
        ext = "." + ext

    # SVG: no se puede comprimir con Pillow, devolver tal cual
    if ext == ".svg":
        return data, ".svg"

    try:
        from PIL import Image
    except ImportError:
        # Pillow no instalado: devolver sin cambios
        return data, ext

    max_w, max_h, quality = _PROFILES.get(profile, _PROFILES["default"])

    try:
        with Image.open(io.BytesIO(data)) as img:
            # Convertir a RGB para WebP (descarta canal alpha sólo si no lo tiene)
            if img.mode in ("RGBA", "P", "LA"):
                # Mantener transparencia en WebP
                img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Redimensionar respetando proporción (sólo encoge, nunca amplía)
            orig_w, orig_h = img.size
            if orig_w > max_w or orig_h > max_h:
                img.thumbnail((max_w, max_h), Image.LANCZOS)

            out = io.BytesIO()
            img.save(out, format="WEBP", quality=quality, method=4)
            return out.getvalue(), ".webp"

    except Exception:
        # Si algo falla, devolver original sin optimizar
        return data, ext


def profile_for_prefix(prefix: str) -> str:
    """Infiere el perfil de optimización a partir del prefijo de nombre de archivo."""
    p = (prefix or "").lower()
    if "favicon" in p:
        return "favicon"
    if "logo" in p:
        return "logo"
    if "fondo" in p or "background" in p or "bg" in p:
        return "background"
    if "avatar" in p or "colab" in p or "foto" in p or "user" in p:
        return "avatar"
    if "asset" in p or "personaliz" in p:
        return "asset"
    return "default"
