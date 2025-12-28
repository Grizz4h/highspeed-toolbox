import streamlit as st
import streamlit as st
from pathlib import Path
from typing import Tuple
from .data_utils import get_spieltage_root, list_seasons, list_matchdays

def select_season(root: Path) -> Path:
    seasons = list_seasons(root)
    if not seasons:
        st.error("Keine Saison-Ordner gefunden.")
        st.stop()
    season_labels = [p.name for p in seasons]
    default_season_idx = len(season_labels) - 1  # latest
    selected_season_label = st.selectbox("Saison", season_labels, index=default_season_idx)
    return root / selected_season_label

def select_season_and_matchday(root: Path) -> Tuple[Path, Path]:
    season_dir = select_season(root)
    matchdays = list_matchdays(season_dir)
    if not matchdays:
        st.error("Keine Spieltag-JSONs gefunden.")
        st.stop()
    selected_file = st.selectbox("Spieltag JSON", matchdays, index=len(matchdays)-1, format_func=lambda p: p.name)
    return season_dir, selected_file