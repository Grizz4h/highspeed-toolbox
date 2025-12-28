"""UI utilities for PULS renderer."""
from pathlib import Path
from typing import Tuple
import streamlit as st


def select_season(root: Path) -> Path:
    """Select a season with latest as default."""
    seasons = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("saison_")])
    
    if not seasons:
        st.error(f"Keine Saison-Ordner gefunden unter: {root.as_posix()}")
        st.stop()
    
    season_labels = [p.name for p in seasons]
    default_idx = len(season_labels) - 1  # Latest season
    
    selected = st.selectbox(
        "Saison",
        season_labels,
        index=default_idx,
        format_func=lambda s: f"Saison {s.replace('saison_', '')}"
    )
    
    return root / selected


def select_season_and_matchday(root: Path) -> Tuple[Path, Path]:
    """Select season and matchday with latest defaults."""
    seasons = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("saison_")])
    
    if not seasons:
        st.error(f"Keine Saison-Ordner gefunden unter: {root.as_posix()}")
        st.stop()
    
    season_labels = [p.name for p in seasons]
    default_season_idx = len(season_labels) - 1  # Latest season
    
    selected_season = st.selectbox(
        "Saison",
        season_labels,
        index=default_season_idx,
        format_func=lambda s: f"Saison {s.replace('saison_', '')}"
    )
    
    season_dir = root / selected_season
    
    matchdays = sorted(season_dir.glob("spieltag_*.json"))
    if not matchdays:
        st.warning(f"Keine Spieltage gefunden unter: {season_dir.as_posix()}")
        st.stop()
    
    matchday_labels = [p.name for p in matchdays]
    default_matchday_idx = len(matchday_labels) - 1  # Latest matchday
    
    selected_matchday = st.selectbox(
        "Spieltag",
        matchday_labels,
        index=default_matchday_idx
    )
    
    return season_dir, season_dir / selected_matchday
