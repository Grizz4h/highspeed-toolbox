import streamlit as st
from pathlib import Path

from src.modules.puls_renderer import results_renderer
from tools.puls_renderer.data_utils import get_spieltage_root
from tools.puls_renderer.ui_utils import select_season_and_matchday

st.set_page_config(page_title="PULS Ergebnisse", layout="wide")

st.title("📊 PULS Ergebnisse")
st.caption("Rendert Ergebnisübersicht aus Spieltag-JSON + Replay-Logs.")

SPIELTAGE_DIR = get_spieltage_root()

# -----------------------------
st.divider()
st.subheader("1️⃣ Daten auswählen")
# -----------------------------
season_dir, spieltag_path = select_season_and_matchday(SPIELTAGE_DIR)

c1, c2, c3 = st.columns([1.2, 1.2, 2])

with c3:
    delta_date = st.text_input("Δ Datum (z.B. 2125-10-18)", value="2125-10-18")

st.caption(f"Input: {spieltag_path}")

if results_renderer is None:
    st.error("results_renderer konnte nicht importiert werden.")
    st.code(IMPORT_ERR)
    st.stop()


template_name = st.text_input("Template", value="matchday_results_v1.png")

# Berechne zusätzliche Pfade
toolbox_root = Path(__file__).parents[1]  # .../toolbox
saison = int(spieltag_path.parent.name.split('_')[1])  # saison_01 -> 1
spieltag = int(spieltag_path.name.split('_')[1].split('.')[0])  # spieltag_01.json -> 1
latest_path = toolbox_root / "data" / "stats" / f"saison_{saison:02d}" / "league" / "latest.json"
narratives_path = toolbox_root / "data" / "replays" / f"saison_{saison:02d}" / f"spieltag_{spieltag:02d}" / "narratives.json"

st.caption(f"Latest: {latest_path}")
st.caption(f"Narratives: {narratives_path}")

if not spieltag_path.exists():
    st.warning("Spieltags-JSON nicht gefunden. (Data Pull / Pfad prüfen)")
else:
    if st.button("Render Ergebnisse", use_container_width=True, type="primary"):
        try:
            out_paths = results_renderer.render_from_spieltag_file(
                spieltag_json_path=spieltag_path,
                template_name=template_name,
                delta_date=delta_date,
                latest_path=latest_path,
                narratives_path=narratives_path,
            )
        except Exception as e:
            st.error("Render fehlgeschlagen.")
            st.code(str(e))
        else:
            for out_path in out_paths:
                out_path = Path(out_path)
                st.success(f"Gerendert: {out_path}")

                if out_path.exists():
                    st.image(str(out_path))
                    st.code(str(out_path))

                    with out_path.open("rb") as f:
                        st.download_button(
                            f"PNG herunterladen ({out_path.name})",
                            data=f,
                            file_name=out_path.name,
                            mime="image/png",
                            use_container_width=True,
                            type="primary",
                        )
                else:
                    st.warning(f"Output-Datei {out_path} wurde nicht gefunden.")
