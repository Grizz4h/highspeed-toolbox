import re
import streamlit as st
from pathlib import Path

from src.modules.puls_renderer import render_from_json_file
from src.modules.puls_renderer.ui_utils import select_season
from src.modules.puls_renderer.data_utils import get_spieltage_root, discover_matchdays, season_folder

st.set_page_config(page_title="PULS Renderer", layout="centered")

st.title("🏒 PULS – Spieltags-Renderer")
st.caption("JSON rein → Spieltagsübersicht PNG raus. Δ-Datum kommt aus UI (nicht aus JSON).")

SPIELTAGE_ROOT = get_spieltage_root()

# ----------------------------
# Helpers
# ----------------------------
def season_folder(season: int) -> str:
    return f"saison_{int(season):02d}"

def discover_seasons(root: Path) -> list[int]:
    seasons: list[int] = []
    if not root.exists():
        return seasons
    for p in root.iterdir():
        if p.is_dir():
            m = re.match(r"(?i)saison_(\d+)$", p.name)
            if m:
                try:
                    seasons.append(int(m.group(1)))
                except Exception:
                    pass
    return sorted(set(seasons))

def discover_matchdays(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    # nur spieltag_XX.json
    files = sorted(folder.glob("spieltag_[0-9][0-9].json"))
    return files

# ----------------------------
# Saison-Auswahl
# ----------------------------
st.divider()
st.subheader("0) Saison wählen")

DATA_DIR = select_season(SPIELTAGE_ROOT)

st.caption(f"Aktiver Ordner: `{DATA_DIR.as_posix()}`")

# ----------------------------
# JSON Auswahl / Upload
# ----------------------------
st.divider()
st.subheader("1) JSON wählen")

uploaded = st.file_uploader("JSON hochladen", type=["json"])

local_files = discover_matchdays(DATA_DIR)
choice = None
if local_files:
    choice = st.selectbox(
        "…oder eine JSON aus /data auswählen",
        ["—"] + [p.name for p in local_files],
    )
else:
    st.info("In dieser Saison liegen noch keine `spieltag_XX.json` Dateien.")

json_path: Path | None = None

if uploaded is not None:
    # Upload immer in die gewählte Saison speichern
    target = DATA_DIR / uploaded.name
    target.write_bytes(uploaded.getvalue())
    json_path = target
    st.success(f"Gespeichert: data/spieltage/{season_folder(sel_season)}/{uploaded.name}")
elif choice and choice != "—":
    json_path = DATA_DIR / choice

# ----------------------------
# Renderer Optionen
# ----------------------------
st.divider()
st.subheader("2) Δ-Datum setzen")
st.caption("Gib nur '2125-10-18' ein. Das Δ setzt der Renderer automatisch davor.")
delta_date_input = st.text_input("Δ-Datum", value="2125-10-18", help="Format: 2125-10-18 (ohne Δ).")

enable_vs = st.toggle("Renderer soll 'VS' in die Mitte schreiben (sonst frei lassen)", value=False)
enable_team_fx = st.toggle("Teamnamen mit FX (Stroke/Shadow)", value=True)

# ----------------------------
# Rendern
# ----------------------------
st.divider()

if json_path:
    st.subheader("3) Rendern")
    st.caption(f"Quelle: `{json_path.name}` (Saison {int(sel_season):02d})")

    if st.button("Render Spieltagsübersicht", type="primary"):
        try:
            out_path = render_from_json_file(
                json_path=json_path,
                enable_draw_vs=enable_vs,
                delta_date=delta_date_input,
                enable_fx_on_teams=enable_team_fx,
                header_fx="ice_noise",
            )
            out_path = Path(out_path)

            st.success(f"Gerendert: {out_path.name}")

            img_bytes = out_path.read_bytes()
            st.image(img_bytes, caption=out_path.name, use_container_width=True)
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
