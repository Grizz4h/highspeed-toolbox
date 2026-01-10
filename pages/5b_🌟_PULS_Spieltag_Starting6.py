"""
Streamlit Page: Starting Six des Spieltags Renderer
Liest replay_matchday.json und rendert die Starting Six des gesamten Spieltags
"""
import json
from pathlib import Path

import streamlit as st

from tools.puls_renderer.matchday_starting6_renderer import render_matchday_starting6

st.set_page_config(page_title="PULS Spieltag Starting6", layout="centered")
st.title("🌟 PULS – Spieltag Starting6")
st.caption("Rendert die besten 6 Spieler des Spieltags aus replay_matchday.json.")

BASE_DIR = Path(__file__).resolve().parent.parent
REPLAY_ROOT = BASE_DIR / "data" / "replays"


# -----------------------------
# Helpers
# -----------------------------
def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_seasons(replay_root: Path) -> list[Path]:
    """Listet alle Saison-Ordner auf"""
    if not replay_root.exists():
        return []
    return sorted([d for d in replay_root.iterdir() if d.is_dir()], key=lambda p: p.name)


def list_spieltage(season_dir: Path) -> list[Path]:
    """Listet alle Spieltag-Ordner in einer Saison auf"""
    if not season_dir.exists():
        return []
    return sorted([d for d in season_dir.iterdir() if d.is_dir()], key=lambda p: p.name)


def find_replay_matchday_json(spieltag_dir: Path) -> Path | None:
    """Sucht nach replay_matchday.json im Spieltag-Ordner"""
    replay_file = spieltag_dir / "replay_matchday.json"
    if replay_file.exists():
        return replay_file
    return None


# -----------------------------
st.divider()
st.subheader("1️⃣ Saison & Spieltag auswählen")
# -----------------------------

seasons = list_seasons(REPLAY_ROOT)
if not seasons:
    st.error(f"Keine Saisons gefunden in: {REPLAY_ROOT.as_posix()}")
    st.stop()

season_dir = st.selectbox(
    "Saison",
    seasons,
    format_func=lambda p: p.name,
    index=len(seasons) - 1,  # Latest season
)

st.caption(f"Aktiver Ordner: `{season_dir.as_posix()}`")

spieltage = list_spieltage(season_dir)
if not spieltage:
    st.error(f"Keine Spieltage gefunden in: {season_dir.as_posix()}")
    st.stop()

spieltag_dir = st.selectbox(
    "Spieltag",
    spieltage,
    format_func=lambda p: p.name,
    index=len(spieltage) - 1,  # Latest matchday
)

replay_json = find_replay_matchday_json(spieltag_dir)
if not replay_json:
    st.error(f"Keine replay_matchday.json gefunden in: {spieltag_dir.as_posix()}")
    st.stop()

st.caption(f"Quelle: `{replay_json.name}`")


# -----------------------------
st.divider()
st.subheader("2️⃣ Daten-Vorschau")
# -----------------------------

try:
    data = _load_json(replay_json)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Saison", data.get("season", "?"))
    with col2:
        st.metric("Spieltag", data.get("matchday", "?"))
    with col3:
        st.metric("Spiele", len(data.get("games", [])))
    
    # Starting Six Preview
    if "starting_six" not in data:
        st.warning("⚠️ Keine 'starting_six' Daten in replay_matchday.json gefunden")
        st.info("Die Starting Six Daten werden beim Replay-Processing generiert.")
        st.stop()
        
    starting_six = data["starting_six"]
    players = starting_six.get("players", [])
    
    if not players:
        st.warning("Keine Spieler in starting_six gefunden")
        st.stop()
    
    # Spieler nach Position gruppieren
    forwards = [p for p in players if p.get("pos") == "F"]
    defense = [p for p in players if p.get("pos") == "D"]
    goalies = [p for p in players if p.get("pos") == "G"]
    
    with st.expander("Starting Six Übersicht", expanded=False):
        st.write(f"**{len(forwards)}** Forwards • **{len(defense)}** Defense • **{len(goalies)}** Goalies")
        st.dataframe(
            players,
            use_container_width=True,
            hide_index=True,
        )

except Exception as e:
    st.error(f"Fehler beim Laden der Daten: {e}")
    st.stop()


# -----------------------------
st.divider()
st.subheader("3️⃣ Render-Optionen")
# -----------------------------

season_label = st.text_input(
    "Season Label",
    value=f"SAISON {data.get('season', 1)}",
)


# -----------------------------
st.divider()
st.subheader("4️⃣ Rendern")
# -----------------------------

if st.button("🎨 Starting Six rendern", type="primary"):
    try:
        out_path = render_matchday_starting6(
            replay_json_path=replay_json,
            season_label=season_label,
        )
        
        out_path = Path(out_path)
        st.success(f"✅ Gerendert: `{out_path.name}`")
        
        # Zeige Vorschau
        st.image(str(out_path), width=800)
        
        # Download Button
        img_bytes = out_path.read_bytes()
        st.download_button(
            "PNG herunterladen",
            data=img_bytes,
            file_name=out_path.name,
            mime="image/png",
            type="primary",
        )
    
    except Exception as e:
        st.error(f"Render fehlgeschlagen: {e}")
        import traceback
        st.code(traceback.format_exc())


# -----------------------------
st.divider()
st.caption("ℹ️ **Info:** Zeigt die 6 besten Spieler des Spieltags (3F, 2D, 1G) aus allen Teams.")
