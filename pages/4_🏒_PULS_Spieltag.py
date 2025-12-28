import streamlit as st
from pathlib import Path

from tools.puls_renderer import render_from_json_file
from tools.puls_renderer.ui_utils import select_season
from tools.puls_renderer.data_utils import get_spieltage_root, discover_matchdays

st.set_page_config(page_title="PULS Renderer", layout="centered")

st.title("🏒 PULS – Spieltags-Renderer")
st.caption("Rendert Spieltagsübersicht aus Matchday-JSON.")

SPIELTAGE_ROOT = get_spieltage_root()

# ----------------------------
st.divider()
st.subheader("1️⃣ Daten auswählen")
# ----------------------------

DATA_DIR = select_season(SPIELTAGE_ROOT)

st.caption(f"Aktiver Ordner: `{DATA_DIR.as_posix()}`")

# JSON Auswahl (erst lokale Files, dann Upload)
local_files = discover_matchdays(DATA_DIR)
choice = None
if local_files:
    file_names = [p.name for p in local_files]
    default_idx = len(file_names)  # Latest file (last in list + 1 for "—")
    choice = st.selectbox(
        "Spieltag-JSON aus /data",
        ["—"] + file_names,
        index=default_idx,
    )
else:
    st.info("In dieser Saison liegen noch keine `spieltag_XX.json` Dateien.")

uploaded = st.file_uploader("Oder JSON hochladen", type=["json"])

json_path: Path | None = None

if uploaded is not None:
    # Upload immer in die gewählte Saison speichern
    target = DATA_DIR / uploaded.name
    target.write_bytes(uploaded.getvalue())
    json_path = target
    st.success(f"Gespeichert: {uploaded.name}")
elif choice and choice != "—":
    json_path = DATA_DIR / choice

# ----------------------------
st.divider()
st.subheader("2️⃣ Render-Optionen")
# ----------------------------
delta_date_input = st.text_input("Δ-Datum", value="2125-10-18", help="Format: 2125-10-18 (ohne Δ).")

col1, col2 = st.columns(2)
with col1:
    enable_vs = st.toggle("'VS' in die Mitte schreiben", value=False)
with col2:
    enable_team_fx = st.toggle("Teamnamen mit FX", value=True)

# ----------------------------
st.divider()
st.subheader("3️⃣ Rendern")
# ----------------------------

if json_path:
    st.caption(f"Quelle: `{json_path.name}`")

    if st.button("🎨 Spieltag rendern", type="primary"):
        try:
            out_path = render_from_json_file(
                json_path=json_path,
                enable_draw_vs=enable_vs,
                delta_date=delta_date_input,
                enable_fx_on_teams=enable_team_fx,
                header_fx="ice_noise",
            )
            out_path = Path(out_path)

            st.success(f"✅ Gerendert: `{out_path.name}`")
            st.image(str(out_path), width=800)
            st.download_button(
                "PNG herunterladen",
                data=img_bytes,
                file_name=out_path.name,
                mime="image/png",
            )

        except Exception as e:
            st.error(f"Render fehlgeschlagen: {e}")
else:
    st.info("Wähle oder lade eine JSON-Datei, dann kannst du rendern.")
