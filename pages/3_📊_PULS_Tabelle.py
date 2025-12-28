import re
import streamlit as st
from pathlib import Path

from src.modules.puls_renderer import render_table_from_matchday_json
from src.modules.puls_renderer.data_utils import get_spieltage_root
from src.modules.puls_renderer.ui_utils import select_season_and_matchday

st.title("📊 PULS Tabellen-Renderer")

SPIELTAGE_ROOT = get_spieltage_root()

# -----------------------------
# Helpers
# -----------------------------
def _to_index(value: str) -> int:
    m = re.search(r"(\d+)", str(value))
    if not m:
        return -1
    return int(m.group(1))

def list_seasons(root: Path) -> list[Path]:
    if not root.exists():
        return []
    seasons = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("saison_")]
    seasons.sort(key=lambda p: _to_index(p.name))
    return seasons

def list_matchdays(season_dir: Path) -> list[Path]:
    if not season_dir.exists():
        return []
    files = sorted(season_dir.glob("spieltag_[0-9][0-9].json"), key=lambda p: _to_index(p.name))
    return files

# -----------------------------
# Saison- und Spieltag-Auswahl
# -----------------------------
season_dir, selected_file = select_season_and_matchday(SPIELTAGE_ROOT)

# Spieltag ist bereits ausgewählt via select_season_and_matchday

# -----------------------------
# Inputs
# -----------------------------
delta_date = st.text_input("Δ-Datum (z.B. 2125-10-18)", value="2125-10-18")
template_name = st.text_input("Template (assets/templates)", value="league_table_v1.png")

# -----------------------------
# Render
# -----------------------------
if st.button("Rendern"):
    try:
        out = render_table_from_matchday_json(
            matchday_json_path=selected_file,
            template_name=template_name,
            delta_date=delta_date,
        )
        st.success(f"OK: {out}")
        st.image(str(out))

        png_bytes = Path(out).read_bytes()
        st.download_button(
            "PNG herunterladen",
            data=png_bytes,
            file_name=Path(out).name,
            mime="image/png",
        )
    except Exception as e:
        st.error(str(e))
