import streamlit as st
from pathlib import Path

from tools.puls_renderer import render_table_from_matchday_json
from tools.puls_renderer.data_utils import get_spieltage_root
from tools.puls_renderer.ui_utils import select_season_and_matchday

st.title("📊 PULS Tabellen-Renderer")
st.caption("Rendert Liga-Tabelle aus Spieltag-JSON.")

SPIELTAGE_ROOT = get_spieltage_root()

# -----------------------------
st.divider()
st.subheader("1️⃣ Daten auswählen")
# -----------------------------
season_dir, selected_file = select_season_and_matchday(SPIELTAGE_ROOT)

# -----------------------------
st.divider()
st.subheader("2️⃣ Render-Optionen")
# -----------------------------
delta_date = st.text_input("Δ-Datum (z.B. 2125-10-18)", value="2125-10-18")
template_name = st.text_input("Template (assets/templates)", value="league_table_v1.png")

# -----------------------------
st.divider()
st.subheader("3️⃣ Rendern")
# -----------------------------
if st.button("🎨 Tabelle rendern", type="primary"):
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
