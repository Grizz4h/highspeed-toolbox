import re
import streamlit as st
from pathlib import Path

from tools.puls_renderer import render_table_from_matchday_json

st.title("📊 PULS Tabellen-Renderer")

BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (wenn pages/ eine Ebene tiefer liegt)
SPIELTAGE_ROOT = BASE_DIR / "data" / "spieltage"

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
# Saison-Auswahl
# -----------------------------
seasons = list_seasons(SPIELTAGE_ROOT)

if not seasons:
    st.warning(f"Keine Saison-Ordner gefunden unter: {SPIELTAGE_ROOT.as_posix()}")
    st.stop()

season_labels = [p.name for p in seasons]
default_season_idx = max(0, len(season_labels) - 1)  # letzte Saison als Default

selected_season_label = st.selectbox("Saison auswählen", season_labels, index=default_season_idx)
season_dir = SPIELTAGE_ROOT / selected_season_label

# -----------------------------
# Spieltag-Auswahl
# -----------------------------
files = list_matchdays(season_dir)

if not files:
    st.warning(f"Keine spieltag_XX.json gefunden unter: {season_dir.as_posix()}")
    st.stop()

file_labels = [p.name for p in files]
default_file_idx = max(0, len(file_labels) - 1)  # letzter Spieltag als Default

selected_file_label = st.selectbox("Spieltag JSON auswählen", file_labels, index=default_file_idx)
selected_file = season_dir / selected_file_label

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
