import streamlit as st
from pathlib import Path
import sys

# Add src to path for modular imports
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR / "src") not in sys.path:
    sys.path.insert(0, str(APP_DIR / "src"))

st.set_page_config(page_title="PULS Ergebnisse", layout="wide")

from src.modules.puls_renderer import results_renderer
from src.modules.puls_renderer.data_utils import get_spieltage_root
from src.modules.puls_renderer.ui_utils import select_season_and_matchday
    IMPORT_ERR = str(e)
else:
    IMPORT_ERR = ""

st.title("📊 PULS Ergebnisse")
st.caption("Spieltags-Ergebnisse rendern + 2-Zeiler pro Spiel aus Replay-Log (MVP).")
import re

SPIELTAGE_DIR = get_spieltage_root()

def _num_from_name(pattern: str, name: str) -> int:
    m = re.search(pattern, name)
    return int(m.group(1)) if m else -1

def list_seasons(base: Path) -> list[Path]:
    seasons = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("saison_")]
    seasons.sort(key=lambda p: _num_from_name(r"saison_(\d+)", p.name))
    return seasons

def list_spieltage(season_dir: Path) -> list[Path]:
    files = list(season_dir.glob("spieltag_*.json"))
    files.sort(key=lambda p: _num_from_name(r"spieltag_(\d+)\.json", p.name))
    return files
c1, c2, c3 = st.columns([1.2, 1.2, 2])

season_dir, spieltag_path = select_season_and_matchday(SPIELTAGE_DIR)

with c3:
    delta_date = st.text_input("Δ Datum (z.B. 2125-10-18)", value="2125-10-18")

st.caption(f"Input: {spieltag_path}")

if results_renderer is None:
    st.error("results_renderer konnte nicht importiert werden.")
    st.code(IMPORT_ERR)
    st.stop()


template_name = st.text_input("Template", value="matchday_overview_v1.png")



if not spieltag_path.exists():
    st.warning("Spieltags-JSON nicht gefunden. (Data Pull / Pfad prüfen)")
else:
    if st.button("Render Ergebnisse", use_container_width=True):
        try:
            out_path = results_renderer.render_from_spieltag_file(
                spieltag_json_path=spieltag_path,
                template_name=template_name,
                delta_date=delta_date,
            )
        except Exception as e:
            st.error("Render fehlgeschlagen.")
            st.code(str(e))
        else:
            out_path = Path(out_path)
            st.success(f"Gerendert: {out_path}")

            if out_path.exists():
                st.image(str(out_path))
                st.code(str(out_path))

                with out_path.open("rb") as f:
                    st.download_button(
                        "PNG herunterladen",
                        data=f,
                        file_name=out_path.name,
                        mime="image/png",
                        use_container_width=True,
                    )
            else:
                st.warning("Output-Datei wurde nicht gefunden, obwohl Render keinen Fehler geworfen hat.")
