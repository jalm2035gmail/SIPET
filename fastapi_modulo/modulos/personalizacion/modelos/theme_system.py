from __future__ import annotations

import colorsys
import re
from typing import Dict


MAIN_THEME_KEYS = (
    "sidebar-top",
    "sidebar-bottom",
    "navbar-bg",
    "button-bg",
    "field-color",
)


DEFAULT_MAIN_THEME: Dict[str, str] = {
    "sidebar-top": "#1f2a3d",
    "sidebar-bottom": "#0f172a",
    "navbar-bg": "#ffffff",
    "button-bg": "#0f172a",
    "field-color": "#ffffff",
}


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_hex_color(value: str | None, fallback: str) -> str:
    raw = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", raw):
        raw = "#" + "".join(ch * 2 for ch in raw[1:])
    if _HEX_COLOR_RE.fullmatch(raw):
        return raw.lower()
    return fallback.lower()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    color = normalize_hex_color(value, "#000000")
    return tuple(int(color[idx:idx + 2], 16) for idx in (1, 3, 5))


def rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{max(0, min(255, int(round(red)))):02x}{max(0, min(255, int(round(green)))):02x}{max(0, min(255, int(round(blue)))):02x}"


def mix_hex_colors(left: str, right: str, ratio: float) -> str:
    weight = max(0.0, min(1.0, float(ratio)))
    left_rgb = hex_to_rgb(left)
    right_rgb = hex_to_rgb(right)
    return rgb_to_hex(
        left_rgb[0] * (1.0 - weight) + right_rgb[0] * weight,
        left_rgb[1] * (1.0 - weight) + right_rgb[1] * weight,
        left_rgb[2] * (1.0 - weight) + right_rgb[2] * weight,
    )


def adjust_lightness(value: str, amount: float) -> str:
    red, green, blue = hex_to_rgb(value)
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255.0, green / 255.0, blue / 255.0)
    next_lightness = max(0.0, min(1.0, lightness + amount))
    next_red, next_green, next_blue = colorsys.hls_to_rgb(hue, next_lightness, saturation)
    return rgb_to_hex(next_red * 255.0, next_green * 255.0, next_blue * 255.0)


def complementary_hex_color(value: str) -> str:
    red, green, blue = hex_to_rgb(value)
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255.0, green / 255.0, blue / 255.0)
    next_hue = (hue + 0.5) % 1.0
    next_red, next_green, next_blue = colorsys.hls_to_rgb(next_hue, lightness, saturation)
    return rgb_to_hex(next_red * 255.0, next_green * 255.0, next_blue * 255.0)


def _relative_luminance(value: str) -> float:
    def channel_to_linear(channel: int) -> float:
        color = channel / 255.0
        return color / 12.92 if color <= 0.03928 else ((color + 0.055) / 1.055) ** 2.4

    red, green, blue = hex_to_rgb(value)
    red_lin = channel_to_linear(red)
    green_lin = channel_to_linear(green)
    blue_lin = channel_to_linear(blue)
    return (0.2126 * red_lin) + (0.7152 * green_lin) + (0.0722 * blue_lin)


def readable_text_color(background: str, dark: str = "#0f172a", light: str = "#ffffff") -> str:
    return dark if _relative_luminance(background) >= 0.45 else light


def sanitize_MAIN_theme(raw_colors: Dict[str, str] | None) -> Dict[str, str]:
    source = raw_colors or {}
    return {
        key: normalize_hex_color(source.get(key), fallback)
        for key, fallback in DEFAULT_MAIN_THEME.items()
    }


def build_institutional_theme(raw_colors: Dict[str, str] | None = None) -> Dict[str, str]:
    MAIN = sanitize_MAIN_theme(raw_colors)
    sidebar_top = MAIN["sidebar-top"]
    sidebar_bottom = MAIN["sidebar-bottom"]
    navbar_bg = MAIN["navbar-bg"]
    button_bg = MAIN["button-bg"]
    field_color = MAIN["field-color"]

    sidebar_top_opposite = complementary_hex_color(sidebar_top)
    sidebar_bottom_opposite = complementary_hex_color(sidebar_bottom)
    navbar_bg_opposite = complementary_hex_color(navbar_bg)
    button_bg_opposite = complementary_hex_color(button_bg)
    field_color_opposite = complementary_hex_color(field_color)

    sidebar_text = readable_text_color(mix_hex_colors(sidebar_top, sidebar_bottom, 0.5))
    navbar_text = readable_text_color(navbar_bg)
    button_text = readable_text_color(button_bg)
    field_text = readable_text_color(field_color, dark="#0f172a", light="#ffffff")

    return {
        **MAIN,
        "sidebar-text": sidebar_text,
        "sidebar-icon": mix_hex_colors(sidebar_bottom_opposite, sidebar_text, 0.35),
        "sidebar-hover": mix_hex_colors(sidebar_bottom, sidebar_bottom_opposite, 0.18),
        "navbar-text": navbar_text,
        "button-text": button_text,
        "field-text": field_text,
        "field-border": mix_hex_colors(field_color, field_color_opposite, 0.22),
        "field-focus": mix_hex_colors(button_bg, button_bg_opposite, 0.22),
        "page-bg": mix_hex_colors(navbar_bg, navbar_bg_opposite, 0.08),
        "content-bg": adjust_lightness(field_color, 0.02 if readable_text_color(field_color) == "#0f172a" else -0.02),
        "body-text": mix_hex_colors(field_text, navbar_text, 0.2),
        "page-title-color": sidebar_bottom,
        "sidebar-top-opposite": sidebar_top_opposite,
        "sidebar-bottom-opposite": sidebar_bottom_opposite,
        "navbar-bg-opposite": navbar_bg_opposite,
        "button-bg-opposite": button_bg_opposite,
        "field-color-opposite": field_color_opposite,
        "institutional-accent": sidebar_bottom,
        "institutional-accent-contrast": sidebar_bottom_opposite,
        "institutional-navbar-accent": navbar_bg_opposite,
        "institutional-button-hover": mix_hex_colors(button_bg, button_bg_opposite, 0.14),
        "institutional-button-active": mix_hex_colors(button_bg, button_bg_opposite, 0.22),
        "institutional-field-soft": mix_hex_colors(field_color, field_color_opposite, 0.08),
        "institutional-panel-soft": mix_hex_colors(navbar_bg, sidebar_bottom_opposite, 0.05),
    }
