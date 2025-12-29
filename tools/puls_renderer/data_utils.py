"""Data utilities for PULS renderer."""
from pathlib import Path
import streamlit as st


def get_spieltage_root() -> Path:
    """Get the spieltage root directory."""
    # Start from this file's location in tools/puls_renderer/
    # Go up to toolbox root, then into data symlink -> spieltage
    toolbox_root = Path(__file__).resolve().parents[2]  # /opt/highspeed/toolbox
    return toolbox_root / "data" / "spieltage"


def discover_matchdays(season_dir: Path) -> list[Path]:
    """Discover all spieltag_XX.json files in a season directory.
    
    Note: Cache removed to ensure fresh file discovery after data repo updates.
    """
    if not season_dir.exists():
        return []
    files = sorted(season_dir.glob("spieltag_*.json"))
    return files


def season_folder(season_num: int) -> str:
    """Get the folder name for a season number."""
    return f"saison_{int(season_num):02d}"
