"""
theme_loader.py

Loads color themes from JSON files and provides utilities for resolving
color names to hex values for rrdtool graph commands.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


def load_theme(theme_name: str, config_dir: Path = Path("/config")) -> Optional[dict]:
    """
    Load a theme JSON file by name.

    Args:
        theme_name: Name of the theme (e.g., "unraid-dark")
        config_dir: Base config directory (default: /config)

    Returns:
        Theme dictionary or None if not found
    """
    theme_path = config_dir / "themes" / f"{theme_name}.json"

    if not theme_path.exists():
        print(f"Warning: Theme file not found: {theme_path}")
        return None

    try:
        with open(theme_path, "r") as f:
            theme = json.load(f)
        print(f"Loaded theme: {theme.get('name', theme_name)}")
        return theme
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in theme file {theme_path}: {e}")
        return None
    except Exception as e:
        print(f"Error loading theme {theme_path}: {e}")
        return None


def resolve_color(color_ref: str, theme: Optional[dict]) -> str:
    """
    Resolve a color reference to a hex value.

    Args:
        color_ref: Either a hex color (e.g., "#FF0000") or a named color (e.g., "PRIMARY")
        theme: Theme dictionary from load_theme()

    Returns:
        Hex color string (e.g., "#FF0000" or "#FF0000CC" with alpha)
    """
    # If already a hex color, return as-is
    if color_ref.startswith("#"):
        return color_ref

    # If no theme loaded, can't resolve named colors
    if not theme:
        print(f"Warning: Cannot resolve named color '{color_ref}' without a theme, using black")
        return "#000000"

    # Normalize to uppercase for case-insensitive lookup
    color_name = color_ref.upper()

    # Try to find in series colors
    if "series" in theme and color_name in theme["series"]:
        return theme["series"][color_name]

    # Try to find in alarm colors
    if "alarms" in theme and color_name in theme["alarms"]:
        return theme["alarms"][color_name]

    # Try to find in scaffolding (less common for data series)
    if "scaffolding" in theme and color_name in theme["scaffolding"]:
        return theme["scaffolding"][color_name]

    # Not found
    print(f"Warning: Named color '{color_ref}' not found in theme, using black")
    return "#000000"


def get_rrdtool_colors(theme: Optional[dict]) -> list[str]:
    """
    Generate rrdtool --color options from a theme.

    Args:
        theme: Theme dictionary from load_theme()

    Returns:
        List of rrdtool color options (e.g., ["--color", "BACK#0F1115", "--color", "CANVAS#0B0E14"])
    """
    if not theme or "scaffolding" not in theme:
        return []

    scaffolding = theme["scaffolding"]
    color_options = []

    # Map theme keys to rrdtool color names
    # rrdtool supports: BACK, CANVAS, SHADEA, SHADEB, GRID, MGRID, FONT, AXIS, FRAME, ARROW
    rrd_color_map = {
        "BACK": "BACK",
        "CANVAS": "CANVAS",
        "FRAME": "FRAME",
        "FONT": "FONT",
        "AXIS": "AXIS",
        "GRID": "GRID",
        "MGRID": "MGRID",
        "ARROW": "ARROW"
    }

    for theme_key, rrd_key in rrd_color_map.items():
        if theme_key in scaffolding:
            color_hex = scaffolding[theme_key]
            color_options.extend(["--color", f"{rrd_key}{color_hex}"])

    return color_options


def get_rrdtool_fonts(theme: Optional[dict]) -> list[str]:
    """
    Generate rrdtool --font options from a theme.

    Args:
        theme: Theme dictionary from load_theme()

    Returns:
        List of rrdtool font options (e.g., ["--font", "DEFAULT:11", "--font", "TITLE:13"])
    """
    if not theme or "fonts" not in theme:
        return []

    fonts = theme["fonts"]
    font_options = []

    # RRDtool font format: --font NAME:size[:font]
    # Supported names: DEFAULT, TITLE, AXIS, UNIT, LEGEND, WATERMARK
    for font_name, size in fonts.items():
        font_options.extend(["--font", f"{font_name}:{size}"])

    return font_options


def get_theme_colors_list(theme: Optional[dict]) -> dict[str, str]:
    """
    Get a flat dictionary of all available named colors in a theme.

    Args:
        theme: Theme dictionary from load_theme()

    Returns:
        Dictionary mapping color names to hex values
    """
    if not theme:
        return {}

    colors = {}

    if "scaffolding" in theme:
        colors.update(theme["scaffolding"])

    if "series" in theme:
        colors.update(theme["series"])

    if "alarms" in theme:
        colors.update(theme["alarms"])

    return colors
