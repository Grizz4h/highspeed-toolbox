"""Data utilities for PULS renderer."""
from pathlib import Path
import streamlit as st


def get_spieltage_root() -> Path:
    """Get the spieltage root directory."""
    base_dir = Path(__file__).resolve().parents[2]
    return base_dir / "data" / "spieltage"


@st.cache_data
def discover_matchdays(season_dir: Path) -> list[Path]:
    """Discover all spieltag_XX.json files in a season directory."""
    if not season_dir.exists():
        return []
    files = sorted(season_dir.glob("spieltag_*.json"))
    return files


def season_folder(season_num: int) -> str:
    """Get the folder name for a season number."""
    return f"saison_{int(season_num):02d}"
