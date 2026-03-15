"""
image_utils.py — Optimización de imágenes subidas al servidor.

Redimensiona y convierte a backendP con calidad mínima suficiente.
Los SVG se pasan sin cambios. Los archivos originales nunca se escriben
a disco; sólo se guarda el resultado optimizado.

Funciones públicas:
  optimize_image(data, ext, profile)       → (bytes, ext)
  generate_thumbnails(data, ext, profile)  → {size_name: bytes}
  add_watermark(data, text, **kwargs)      → bytes
  image_info(data)                         → dict
"""
from __future__ import annotations

import io
from typing import Dict, Optional, Tuple

# ── Perfiles de optimización por tipo de uso ─────────────────────────────────
# (max_width, max_height, backendp_quality)
_PROFILES: Dict[str, Tuple[int, int, int]] = {
    "avatar":      (300,  300,  82),
    "favicon":     (256,  256,  85),
    "logo":        (800,  800,  85),
    "background":  (1920, 1080, 78),
    "asset":       (1200, 1200, 82),
    "default":     (1200, 1200, 82),
}

# ── Sets de tamaños para generación de thumbnails ────────────────────────────
_THUMB_SETS: Dict[str, Dict[str, Tuple[int, int]]] = {
    "avatar":     {"sm": (48, 48),    "lg": (300, 300)},
    "favicon":    {"sm": (32, 32),    "md": (64, 64),   "lg": (256, 256)},
    "logo":       {"sm": (120, 120),  "lg": (800, 800)},
    "background": {"preview": (640, 360), "full": (1920, 1080)},
    "asset":      {"sm": (200, 200),  "lg": (1200, 1200)},
    "default":    {"sm": (200, 200),  "lg": (1200, 1200)},
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
    - El resto → backendP optimizado redimensionado según el perfil
    - Si Pillow no está disponible → devuelve los bytes originales sin cambio
    """
    ext = (original_ext or "").lower().strip()
    if not ext.startswith("."):
        ext = "." + ext

    if ext == ".svg":
        return data, ".svg"

    try:
        from PIL import Image
    except ImportError:
        return data, ext

    max_w, max_h, quality = _PROFILES.get(profile, _PROFILES["default"])

    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            orig_w, orig_h = img.size
            if orig_w > max_w or orig_h > max_h:
                img.thumbnail((max_w, max_h), Image.LANCZOS)

            out = io.BytesIO()
            img.save(out, format="backendP", quality=quality, method=4)
            return out.getvalue(), ".backendp"

    except Exception:
        return data, ext


def generate_thumbnails(
    data: bytes,
    original_ext: str,
    profile: str = "default",
) -> Dict[str, bytes]:
    """
    Genera múltiples variantes backendP desde un único upload, todas en una sola
    apertura de imagen — más eficiente que llamar optimize_image N veces.

    Devuelve ``{nombre: bytes_backendp}``. Los nombres son las claves del set
    de tamaños del perfil (p.ej. ``"sm"``, ``"lg"`` para "avatar").

    Si la imagen es SVG o Pillow no está disponible devuelve
    ``{"original": data}``.
    """
    ext = (original_ext or "").lower().strip()
    if not ext.startswith("."):
        ext = "." + ext
    if ext == ".svg":
        return {"original": data}

    try:
        from PIL import Image
    except ImportError:
        return {"original": data}

    sizes = _THUMB_SETS.get(profile, _THUMB_SETS["default"])
    _, _, quality = _PROFILES.get(profile, _PROFILES["default"])

    try:
        with Image.open(io.BytesIO(data)) as src:
            if src.mode in ("RGBA", "P", "LA"):
                src = src.convert("RGBA")
            elif src.mode != "RGB":
                src = src.convert("RGB")

            result: Dict[str, bytes] = {}
            for name, (max_w, max_h) in sizes.items():
                thumb = src.copy()
                thumb.thumbnail((max_w, max_h), Image.LANCZOS)
                buf = io.BytesIO()
                thumb.save(buf, format="backendP", quality=quality, method=4)
                result[name] = buf.getvalue()
            return result

    except Exception:
        return {"original": data}


def add_watermark(
    data: bytes,
    text: str,
    *,
    opacity: int = 40,
    position: str = "bottom-right",
    font_size_ratio: float = 0.04,
) -> bytes:
    """
    Superpone texto semitransparente sobre la imagen y devuelve backendP.

    Args:
        data:            Bytes de la imagen fuente.
        text:            Texto a superponer (p.ej. nombre de la organización).
        opacity:         Alpha del texto 0-255 (por defecto 40 → sutil).
        position:        "bottom-right" | "bottom-left" | "top-right" |
                         "top-left" | "center"
        font_size_ratio: Tamaño de fuente = ancho_imagen × ratio (mín. 12 px).

    En caso de error devuelve ``data`` sin modificar.
    """
    if not text:
        return data

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return data

    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            else:
                img = img.copy()

            w, h = img.size
            font_size = max(12, int(w * font_size_ratio))

            # Intentar fuente TrueType; fallback a fuente bitmap por defecto
            font: object = None
            for font_path in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ]:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except (OSError, IOError):
                    continue
            if font is None:
                font = ImageFont.load_default()

            # Capa RGBA transparente para no alterar la imagen MAIN
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            margin = max(10, int(w * 0.02))

            pos_map = {
                "bottom-right": (w - tw - margin, h - th - margin),
                "bottom-left":  (margin, h - th - margin),
                "top-right":    (w - tw - margin, margin),
                "top-left":     (margin, margin),
                "center":       ((w - tw) // 2, (h - th) // 2),
            }
            x, y = pos_map.get(position, pos_map["bottom-right"])

            # Sombra ligera para legibilidad sobre fondos claros
            draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, opacity // 2))
            draw.text((x, y), text, font=font, fill=(255, 255, 255, opacity))

            composite = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            buf = io.BytesIO()
            composite.save(buf, format="backendP", quality=85, method=4)
            return buf.getvalue()

    except Exception:
        return data


def image_info(data: bytes) -> Dict[str, object]:
    """
    Devuelve metadatos de la imagen sin modificarla ni guardarla:
    ``{"width": int, "height": int, "mode": str, "format": str, "size_kb": float}``

    Útil para validar dimensiones antes de aceptar un upload.
    Devuelve ceros si los bytes no son una imagen válida o Pillow no está.
    """
    try:
        from PIL import Image
    except ImportError:
        return {"width": 0, "height": 0, "mode": "", "format": "", "size_kb": 0.0}
    try:
        with Image.open(io.BytesIO(data)) as img:
            return {
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
                "format": (img.format or "").upper(),
                "size_kb": round(len(data) / 1024, 1),
            }
    except Exception:
        return {"width": 0, "height": 0, "mode": "", "format": "", "size_kb": 0.0}


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
