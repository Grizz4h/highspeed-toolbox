# Matchday Starting Six Renderer

## Übersicht

Der **Matchday Starting Six Renderer** erstellt eine Grafik mit den 6 besten Spielern eines gesamten Spieltags:
- **3 Forwards**
- **2 Defense**  
- **1 Goalie**

Diese Spieler stammen aus verschiedenen Teams und werden aus der `replay_matchday.json` gelesen, die beim Replay-Processing automatisch generiert wird.

## Unterschied zum normalen Starting6-Renderer

| Renderer | Zweck | Datenquelle |
|----------|-------|-------------|
| **Starting6 Renderer** | Starting Lineup für ein einzelnes Spiel (Home vs. Away) | `matchday.json` + `lineups.json` |
| **Matchday Starting6 Renderer** | Beste 6 Spieler des gesamten Spieltags | `replay_matchday.json` |

## Verwendung

### Python API

```python
from pathlib import Path
from tools.puls_renderer import render_matchday_starting6

replay_json = Path("data/replays/saison_01/spieltag_05/replay_matchday.json")

out_path = render_matchday_starting6(
    replay_json_path=replay_json,
    season_label="SAISON 1",
    template_name="matchday_starting6.png",  # optional
    out_name="custom_name.png",  # optional
)

print(f"Rendered: {out_path}")
```

### Streamlit App

Starte die Streamlit App:

```bash
cd /opt/highspeed/toolbox
streamlit run app.py
```

Navigiere zur Seite **"🌟 Spieltag Starting6"** im Seitenmenü.

## JSON-Struktur

Die `replay_matchday.json` muss folgende Struktur enthalten:

```json
{
  "timestamp": "2026-01-10T17:40:21.432364",
  "season": 1,
  "matchday": 5,
  "games": [...],
  "starting_six": {
    "version": 1,
    "seed": 1005,
    "source": "lineups",
    "players": [
      {
        "id": "Player Name",
        "pos": "F",
        "team": "Team Name"
      },
      ...
    ],
    "meta": {
      "fallback_used": false,
      "pool_sizes": {
        "F": 240,
        "D": 140,
        "G": 20
      }
    }
  }
}
```

## Dateien

- **Renderer**: `tools/puls_renderer/matchday_starting6_renderer.py`
- **Streamlit Page**: `pages/10_🌟_Spieltag_Starting6.py`
- **Output**: `tools/puls_renderer/output/matchday_starting6_*.png`

## Features

- ✅ Automatische Layout-Anpassung (3 Spalten für Forwards, 2 für Defense, 1 für Goalie)
- ✅ Team-Logos für jeden Spieler
- ✅ Position-Badges (F, D, G)
- ✅ Meta-Informationen (Seed, Source, Pool-Größen)
- ✅ Fallback auf schwarzen Hintergrund wenn Template fehlt
- ✅ Klare Fehlermeldungen wenn starting_six Daten fehlen

## Entwicklung

Der Renderer ist vollständig von den bestehenden PULS-Renderern getrennt, nutzt aber die gleichen Helper-Funktionen aus `renderer.py`:
- Logo-Loading
- Font-Utilities
- Watermark
- Ice Noise Text Effects

## Beispiel-Output

Das generierte Bild zeigt:
1. **Header**: "STARTING SIX DES SPIELTAGS"
2. **Sub-Header**: "SAISON 1 • SPIELTAG 5"
3. **Forwards**: 3 Spieler-Karten in einer Reihe
4. **Defense**: 2 Spieler-Karten (leicht versetzt)
5. **Goalie**: 1 Spieler-Karte zentriert
6. **Meta-Info**: Seed, Source, Pool-Größen
7. **Watermark**: "powered by HIGHspeeΔ PUX! Engine"

Jede Spieler-Karte enthält:
- Spieler-Name (groß, fett)
- Position-Badge (F/D/G)
- Team-Logo (klein)
- Team-Name (klein)
