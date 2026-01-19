"""
Renderer für Starting Six des Spieltags aus replay_matchday.json
Zeigt die 6 besten Spieler des gesamten Spieltags (3F, 2D, 1G)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont

from .layout_config import Starting6LayoutV1
from .adapter import slugify_team

# Importiere shared helpers
from .renderer import (
    RenderPaths,
    _safe_load_json,
    _fit_text,
    draw_text_ice_noise_bbox,
    _load_logo,
    _draw_watermark,
)


def _draw_player_card(
    img: Image.Image,
    draw: ImageDraw.Draw,
    center: Tuple[int, int],
    player: Dict[str, Any],
    font_name: ImageFont.FreeTypeFont,
    font_team: ImageFont.FreeTypeFont,
    font_pos: ImageFont.FreeTypeFont,
    color_text: Tuple[int, int, int, int],
    color_accent: Tuple[int, int, int, int],
    paths: RenderPaths,
    logo_size: int = 60,
) -> None:
    """
    Zeichnet eine Spieler-Karte mit:
    - Name (fett, groß)
    - Position Badge
    - Team-Logo (klein)
    - Team-Name (klein, unten)
    """
    x, y = center
    
    # Player Name
    player_name = player.get("id", "Unknown").replace("_", " ")
    
    # Prüfe ob Name zu lang ist und kürze ggf.
    bbox = draw.textbbox((x, y), player_name, font=font_name, anchor="mm")
    name_width = bbox[2] - bbox[0]
    max_width = 250
    
    if name_width > max_width:
        # Verkürze den Namen
        words = player_name.split()
        if len(words) > 1:
            # Zeige Vorname initial + Nachname
            player_name = f"{words[0][0]}. {' '.join(words[1:])}"
    
    draw.text((x, y), player_name, font=font_name, fill=color_text, anchor="mm")
    
    # Trikotnummer Badge (rechts vom Namen)
    number = player.get("number", player.get("NUMBER", ""))
    if number:
        bbox = draw.textbbox((x, y), player_name, font=font_name, anchor="mm")
        badge_x = bbox[2] + 18
        badge_y = y
        
        # Badge Hintergrund (kleiner Kreis)
        badge_radius = 15
        draw.ellipse(
            [badge_x - badge_radius, badge_y - badge_radius,
             badge_x + badge_radius, badge_y + badge_radius],
            fill=color_accent
        )
        draw.text((badge_x, badge_y), str(number), font=font_pos, fill=(0, 0, 0, 255), anchor="mm")
    
    # Team Logo (unter dem Namen)
    team_name = player.get("team", "")
    team_id = slugify_team(team_name)
    logo = _load_logo(paths.logos_dir, team_id, logo_size, color_accent)
    logo_y = y + 40
    img.alpha_composite(logo, (x - logo_size // 2, logo_y))


def _draw_section_label(
    draw: ImageDraw.Draw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int, int],
) -> None:
    """Zeichnet ein Section-Label (z.B. "FORWARDS", "DEFENSE", "GOALIE")"""
    draw.text((x, y), text, font=font, fill=color, anchor="mm")


def render_matchday_starting6(
    replay_json_path: Path,
    template_name: str = "starting6v1.png",
    out_name: Optional[str] = None,
    season_label: str = "SAISON 1",
) -> Path:
    """
    Rendert die Starting Six des Spieltags aus replay_matchday.json
    
    Args:
        replay_json_path: Path to replay_matchday.json
        template_name: Name des Template-Bildes
        out_name: Output filename (optional)
        season_label: Season label für Header
        
    Returns:
        Path zum generierten Bild
    """
    base_dir = Path(__file__).resolve().parent
    paths = RenderPaths(base_dir=base_dir)
    layout = Starting6LayoutV1()
    
    # Load replay data
    replay_data = _safe_load_json(replay_json_path)
    
    if "starting_six" not in replay_data:
        raise ValueError(f"No 'starting_six' found in {replay_json_path}")
    
    starting_six = replay_data["starting_six"]
    matchday = replay_data.get("matchday", "X")
    season = replay_data.get("season", 1)
    
    players = starting_six.get("players", [])
    if len(players) != 6:
        raise ValueError(f"Expected 6 players in starting_six, got {len(players)}")
    
    # Gruppiere Spieler nach Position
    forwards = [p for p in players if p.get("pos") == "F"]
    defense = [p for p in players if p.get("pos") == "D"]
    goalies = [p for p in players if p.get("pos") == "G"]
    
    # Template laden (fallback auf schwarzen Hintergrund)
    template_path = paths.templates_dir / template_name
    if template_path.exists():
        img = Image.open(template_path).convert("RGBA")
    else:
        # Fallback: schwarzer Hintergrund (kompakte Größe)
        img = Image.new("RGBA", (1080, 1350), (10, 10, 15, 255))
    
    draw = ImageDraw.Draw(img)
    
    # Fonts
    font_bold = paths.fonts_dir / "PULS_Schriftart.ttf"
    font_med = paths.fonts_dir / "PULS_Schriftart.ttf"
    
    # Header (nur Sub-Zeile, Titel ist im Template)
    sub = f"{season_label} • SPIELTAG {matchday}"
    
    font_sub = _fit_text(draw, sub.upper(), font_med, max_width=980, start_size=20, min_size=14)
    draw.text((540, 180), sub.upper(), font=font_sub, fill=layout.color_accent, anchor="mm")
    
    # Divider
    draw.line((110, 195, 970, 195), fill=layout.color_divider, width=2)
    
    # Fonts für Player Cards
    font_name = ImageFont.truetype(str(font_bold), size=26)
    font_team = ImageFont.truetype(str(font_med), size=15)
    font_pos = ImageFont.truetype(str(font_bold), size=13)
    
    # Layout positions (3 Spalten)
    col_x = [270, 540, 810]  # X-Positionen für 3 Spalten
    
    # FORWARDS (3 Spieler) - in Bogen angeordnet
    y_forwards_base = 330
    forwards_y = [y_forwards_base + 60, y_forwards_base, y_forwards_base + 60]  # Links+Rechts leicht nach unten
    
    for i, player in enumerate(forwards[:3]):
        _draw_player_card(
            img, draw,
            center=(col_x[i], forwards_y[i]),
            player=player,
            font_name=font_name,
            font_team=font_team,
            font_pos=font_pos,
            color_text=layout.color_text,
            color_accent=layout.color_accent,
            paths=paths,
            logo_size=130,
        )
    
    # DEFENSE (2 Spieler)
    y_defense = 720
    for i, player in enumerate(defense[:2]):
        x_pos = 405 if i == 0 else 675  # Zentriert mit Abstand
        _draw_player_card(
            img, draw,
            center=(x_pos, y_defense),
            player=player,
            font_name=font_name,
            font_team=font_team,
            font_pos=font_pos,
            color_text=layout.color_text,
            color_accent=layout.color_accent,
            paths=paths,
            logo_size=130,
        )
    
    # GOALIE (1 Spieler)
    y_goalie = 1000
    if goalies:
        _draw_player_card(
            img, draw,
            center=(540, y_goalie),
            player=goalies[0],
            font_name=font_name,
            font_team=font_team,
            font_pos=font_pos,
            color_text=layout.color_text,
            color_accent=layout.color_accent,
            paths=paths,
            logo_size=130,
        )
    
    # Watermark
    wm_font = ImageFont.truetype(str(paths.fonts_dir / "Inter-Medium.ttf"), size=20)
    _draw_watermark(
        img,
        draw,
        text="powered by HIGHspeeΔ PUX! Engine",
        font=wm_font,
        margin=22,
        opacity=90,
    )
    
    # Save
    if out_name is None:
        out_name = f"matchday_starting6_s{season:02d}_spieltag{matchday:02d}.png"
    
    out_path = paths.output_dir / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    img.save(out_path)
    return out_path
