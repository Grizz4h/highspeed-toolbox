import streamlit as st
from pathlib import Path
import sys

st.set_page_config(page_title="PULS Ergebnisse", layout="wide")

# Toolbox-Root ermitteln (pages/ liegt 1 Ebene unter Root)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from tools.puls_renderer import results_renderer
except Exception as e:
    results_renderer = None
    IMPORT_ERR = str(e)
else:
    IMPORT_ERR = ""

st.title("📊 PULS Ergebnisse")
st.caption("Spieltags-Ergebnisse rendern + 2-Zeiler pro Spiel aus Replay-Log (MVP).")

if results_renderer is None:
    st.error("results_renderer konnte nicht importiert werden.")
    st.code(IMPORT_ERR)
    st.stop()

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    saison = st.number_input("Saison", min_value=1, max_value=99, value=1, step=1)
with c2:
    spieltag = st.number_input("Spieltag", min_value=1, max_value=99, value=1, step=1)
with c3:
    delta_date = st.text_input("Δ Datum (z.B. 2125-10-18)", value="2125-10-18")

template_name = st.text_input("Template", value="matchday_overview_v1.png")

spieltag_path = ROOT / "data" / "spieltage" / f"saison_{int(saison):02d}" / f"spieltag_{int(spieltag):02d}.json"
st.caption(f"Input: {spieltag_path}")

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
