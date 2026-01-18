import streamlit as st
from pathlib import Path
import json

from src.modules.puls_renderer import results_renderer
from tools.puls_renderer.data_utils import get_spieltage_root
from tools.puls_renderer.ui_utils import select_season_and_matchday

st.set_page_config(page_title="PULS Ergebnisse", layout="wide")

# Session state für generierte Bilder
if "rendered_results" not in st.session_state:
    st.session_state.rendered_results = []

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
latest_path = toolbox_root / "data" / "stats" / f"saison_{saison:02d}" / "league" / f"after_spieltag_{spieltag:02d}_detail.json"
st.caption(f"[DEBUG] last5 latest_path: {latest_path}")
narratives_path = toolbox_root / "data" / "replays" / f"saison_{saison:02d}" / f"spieltag_{spieltag:02d}" / "narratives.json"

st.caption(f"Latest: {latest_path}")
st.caption(f"Narratives: {narratives_path}")

# Lade narratives.json und zeige editierbare Texte
narratives_data = {}
if narratives_path.exists():
    with narratives_path.open("r", encoding="utf-8") as f:
        narratives_data = json.load(f)
    st.caption(f"Narratives geladen: {len(narratives_data)} Einträge")
    st.caption(f"Narratives Keys: {list(narratives_data.keys())[:5]}...")  # Erste 5 Keys anzeigen
else:
    st.warning(f"Narratives-Datei nicht gefunden: {narratives_path}")

# Sammle alle Spiele aus spieltag.json
spieltag_data = {}
if spieltag_path.exists():
    with spieltag_path.open("r", encoding="utf-8") as f:
        spieltag_data = json.load(f)

games = spieltag_data.get("results", [])
game_keys = []
for g in games:
    home = g.get("home_team") or g.get("home") or ""
    away = g.get("away_team") or g.get("away") or ""
    game_keys.append(f"{home}-{away}")
st.caption(f"Spiele aus spieltag.json: {game_keys}")

# UI für Texte bearbeiten
st.divider()
st.subheader("2️⃣ Texte bearbeiten")
st.caption("Passe die Spielzusammenfassungen an (aus narratives.json geladen).")

edited_blurbs = {}
for i, (game_key, g) in enumerate(zip(game_keys, games)):
    game_narr = narratives_data.get(game_key, {})
    line1 = game_narr.get("line1", "")
    line2 = game_narr.get("line2", "")
    
    # Extrahiere Ergebnis
    
    # Extrahiere Ergebnis
    gh = g.get("goals_home") or g.get("g_home") or 0
    ga = g.get("goals_away") or g.get("g_away") or 0
    
    st.write(f"**Spiel {i+1}: {game_key} ({gh}:{ga})**")
    col1, col2 = st.columns(2)
    with col1:
        edited_line1 = st.text_area(f"Zeile 1 für {game_key}", value=line1, height=60, key=f"line1_{saison}_{spieltag}_{i}")
    with col2:
        edited_line2 = st.text_area(f"Zeile 2 für {game_key}", value=line2, height=60, key=f"line2_{i}")
    
    edited_blurbs[game_key] = {"line1": edited_line1, "line2": edited_line2}
    
    # Replay Events einblenden (eingeklappt)
    replay_path = toolbox_root / "data" / "replays" / f"saison_{saison:02d}" / f"spieltag_{spieltag:02d}" / f"{game_key}.json"
    if replay_path.exists():
        with st.expander(f"Spielverlauf für {game_key}"):
            try:
                with replay_path.open("r", encoding="utf-8") as f:
                    replay_data = json.load(f)
                events = replay_data.get("events", [])
                if events:
                    for event in events:
                        st.write(f"- {event.get('type', 'unknown')}: {event.get('description', '')}")
                else:
                    st.write("Keine Events gefunden.")
            except Exception as e:
                st.write(f"Fehler beim Laden der Replay: {e}")
    else:
        with st.expander(f"Spielverlauf für {game_key}"):
            st.write("Replay-Datei nicht gefunden.")

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
                edited_blurbs=edited_blurbs,  # Neue Parameter
            )
            # Speichere im session_state
            st.session_state.rendered_results = out_paths
        except Exception as e:
            st.error("Render fehlgeschlagen.")
            st.code(str(e))
        else:
            st.success(f"Gerendert: {len(out_paths)} Bilder")

    # Zeige gespeicherte Bilder aus session_state
    if st.session_state.rendered_results:
        for out_path in st.session_state.rendered_results:
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
                        key=f"download_{out_path.name}",
                    )
            else:
                st.warning(f"Output-Datei {out_path} wurde nicht gefunden.")
