from pathlib import Path
from typing import List
import json
import streamlit as st

def get_spieltage_root() -> Path:
    return Path("data/spieltage")

def get_lineups_root() -> Path:
    return Path("data/lineups")

def season_folder(season: int) -> str:
    return f"saison_{season:02d}"

def list_seasons(root: Path) -> List[Path]:
    if not root.exists():
        return []
    seasons = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("saison_")]
    seasons.sort(key=lambda p: int(p.name.split('_')[1]))
    return seasons

def list_matchdays(season_dir: Path) -> List[Path]:
    if not season_dir.exists():
        return []
    files = sorted(season_dir.glob("spieltag_*.json"), key=lambda p: int(p.name.split('_')[1].split('.')[0]))
    return files

def discover_matchdays(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    files = sorted(folder.glob("spieltag_*.json"), key=lambda p: int(p.name.split('_')[1].split('.')[0]))
    return files

def extract_spieltag_number(filename: str) -> int | None:
    import re
    m = re.search(r"spieltag_(\d+)", filename)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

@st.cache_data
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))