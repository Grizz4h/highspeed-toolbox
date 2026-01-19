# tools/puls_renderer/results_renderer.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .layout_config import MatchdayLayoutV1, ConferenceLayoutV1


# ----------------------------
# Paths (gleich wie renderer.py)
# ----------------------------
@dataclass
class RenderPaths:
    base_dir: Path

    @property
    def templates_dir(self) -> Path:
        return self.base_dir / "assets" / "templates"

    @property
    def logos_dir(self) -> Path:
        return self.base_dir / "assets" / "logos"

    @property
    def fonts_dir(self) -> Path:
        return self.base_dir / "assets" / "fonts"

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def toolbox_root(self) -> Path:
        # base_dir = .../tools/puls_renderer
        return self.base_dir.parent.parent  # .../HIGHspeed-toolbox


# ----------------------------
# Helpers: IO / Fonts
# ----------------------------
def _safe_load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not font_path.exists():
        raise FileNotFoundError(f"Font not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def _text_w(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0])


def _truncate_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    if _text_w(draw, text, font) <= max_w:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        cand = text[:mid].rstrip() + ell
        if _text_w(draw, cand, font) <= max_w:
            lo = mid + 1
        else:
            hi = mid
    return text[: max(0, lo - 1)].rstrip() + ell


def _wrap_to_n_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int, n: int) -> List[str]:
    """
    Sehr simple Wort-Wrapping auf exakt n Zeilen (alles darüber wird gekürzt).
    """
    text = (text or "").strip()
    if not text:
        return [""] * n

    words = text.split()
    lines: List[str] = []
    cur = ""

    for w in words:
        cand = (cur + " " + w).strip()
        if _text_w(draw, cand, font) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w

    if cur:
        lines.append(cur)

    # auf n Zeilen begrenzen, aber NICHT abschneiden
    if len(lines) <= n:
        lines += [""] * (n - len(lines))
        return lines[:n]
    # zu viele: n-1 behalten, Rest als letzte Zeile (ohne Truncation)
    head = lines[: n - 1]
    tail = " ".join(lines[n - 1 :])
    return head + [tail]

def _draw_watermark(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    margin: int = 24,
    opacity: int = 110,
):
    w, h = img.size

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # bottom-right
    x = w - tw - margin
    y = h - th - margin

    fill = (255, 255, 255, opacity)
    shadow_fill = (0, 0, 0, int(opacity * 0.6))

    draw.text((x + 1, y + 1), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)


# ----------------------------
# Text FX (clean)
# ----------------------------
def draw_text_fx(
    img: Image.Image,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int, int],
    anchor: str = "mm",
    shadow: bool = True,
    shadow_offset: Tuple[int, int] = (0, 2),
    shadow_alpha: int = 140,
    stroke: bool = True,
    stroke_width: int = 2,
    stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 190),
    glow: bool = False,
    glow_radius: int = 8,
    glow_alpha: int = 120,
) -> None:
    x, y = pos

    base = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(base)

    if shadow:
        sx, sy = shadow_offset
        d.text((x + sx, y + sy), text, font=font, fill=(0, 0, 0, shadow_alpha), anchor=anchor)

    if stroke and stroke_width > 0:
        d.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            anchor=anchor,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )

    d.text((x, y), text, font=font, fill=fill, anchor=anchor)

    if glow:
        glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        gd.text((x, y), text, font=font, fill=(fill[0], fill[1], fill[2], glow_alpha), anchor=anchor)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        img.alpha_composite(glow_layer)

    img.alpha_composite(base)


# ----------------------------
# Slugs / Logos
# ----------------------------
def _slugify_team_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = (
        s.replace("ä", "ae")
         .replace("ö", "oe")
         .replace("ü", "ue")
         .replace("ß", "ss")
    )
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def _load_team_display_map(assets_dir: Path) -> Dict[str, str]:
    # gleiche Regel wie bisher: assets/team_display_names.json
    p = assets_dir / "team_display_names.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _team_name_to_logo_slug(team_name: str, display_map: Dict[str, str]) -> str:
    """
    display_map ist slug -> display-name (euer Setup).
    Wir reverse-mappen display -> slug.
    """
    reverse = {v.strip().lower(): k for k, v in display_map.items()}
    key = (team_name or "").strip().lower()
    if key in reverse:
        return reverse[key]
    return _slugify_team_name(team_name)


def _load_logo(
    logos_dir: Path,
    team_id: str,
    size: int,
    accent: Tuple[int, int, int, int],
) -> Image.Image:
    p = logos_dir / f"{team_id}.png"
    if p.exists():
        im = Image.open(p).convert("RGBA")
        return im.resize((size, size), Image.LANCZOS)

    # fallback placeholder
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((3, 3, size - 3, size - 3), outline=accent, width=3)
    return im


# ----------------------------
# Replay -> 2-Satz MVP
# ----------------------------
def _guess_replay_path(toolbox_root: Path, saison: int, spieltag: int, home_name: str, away_name: str) -> Path:
    # genau nach deinem Muster: data/replays/saison_01/spieltag_01/Home-Away.json
    fn = f"{home_name}-{away_name}.json"
    return toolbox_root / "data" / "replays" / f"saison_{saison:02d}" / f"spieltag_{spieltag:02d}" / fn


def _load_latest_json(latest_path: Path) -> Dict[str, Any]:
    if latest_path.exists():
        return _safe_load_json(latest_path)
    return {"teams": []}


def _load_narratives_json(narratives_path: Path) -> Dict[str, Any]:
    if narratives_path.exists():
        return _safe_load_json(narratives_path)
    return {}


def _get_last5_for_team(latest_data: Dict[str, Any], team_name: str) -> List[str]:
    teams = latest_data.get("teams", [])
    for team in teams:
        if team.get("team") == team_name:
            return team.get("last5", [])
    return []


def _get_line1_for_match(narratives_data: Dict[str, Any], home_name: str, away_name: str) -> str:
    key = f"{home_name}-{away_name}"
    match_data = narratives_data.get(key, {})
    return match_data.get("line1", "")


# ----------------------------
# Adapter: Spieltag JSON -> render-data
# ----------------------------
def convert_spieltag_json_to_results(spieltag_json: Dict[str, Any]) -> Dict[str, Any]:
    saison = int(spieltag_json.get("saison") or 0)
    spieltag = int(spieltag_json.get("spieltag") or 0)
    results = spieltag_json.get("results", []) or []

    def norm_conf(raw: str) -> str:
        s = (raw or "").strip().lower()
        # deutsche Varianten
        s = s.replace("ü", "ue")
        if s in ("nord", "north"):
            return "north"
        if s in ("sued", "süd", "south"):
            return "south"
        return ""  # unknown

    all_games: List[Dict[str, Any]] = []
    for r in results:
        # akzeptiere beide Schemas
        home_name = r.get("home_team") or r.get("home") or ""
        away_name = r.get("away_team") or r.get("away") or ""

        gh = r.get("goals_home")
        if gh is None:
            gh = r.get("g_home")
        ga = r.get("goals_away")
        if ga is None:
            ga = r.get("g_away")

        conf = norm_conf(r.get("conference"))

        # Neue Flags
        overtime = bool(r.get("overtime", False))
        shootout = bool(r.get("shootout", False))

        item = {
            "home_name": str(home_name),
            "away_name": str(away_name),
            "goals_home": int(gh or 0),
            "goals_away": int(ga or 0),
            "conference": conf,
            "overtime": overtime,
            "shootout": shootout,
        }
        all_games.append(item)

    nord = [g for g in all_games if g["conference"] == "north"]
    sued = [g for g in all_games if g["conference"] == "south"]

    # Fallback fürs Template: wenn Conference fehlt/komisch ist oder alles in einer Gruppe landet
    if (len(nord) == 0 and len(sued) == 0) and len(all_games) == 10:
        nord = all_games[:5]
        sued = all_games[5:]

    if len(nord) == 0 and len(sued) == 10:
        nord = all_games[:5]
        sued = all_games[5:]

    if len(nord) == 10 and len(sued) == 0:
        nord = all_games[:5]
        sued = all_games[5:]

    return {"saison": saison, "spieltag": spieltag, "nord": nord, "sued": sued}


# ----------------------------
# Renderer
# ----------------------------
def render_matchday_results_overview(
    template_path: Path,
    spieltag_data: Dict[str, Any],
    paths: RenderPaths,
    out_path: Path,
    layout: Optional[MatchdayLayoutV1] = None,
    delta_date: Optional[str] = None,
    latest_path: Optional[Path] = None,
    narratives_path: Optional[Path] = None,
) -> Path:
    # Wähle Layout basierend auf Daten
    if len(spieltag_data.get("nord", [])) > 0 and len(spieltag_data.get("sued", [])) > 0:
        layout = MatchdayLayoutV1()
    else:
        layout = ConferenceLayoutV1()

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Load additional data
    latest_data = _load_latest_json(latest_path) if latest_path else {"teams": []}
    narratives_data = _load_narratives_json(narratives_path) if narratives_path else {}

    # Fonts (wie bei euch)
    font_bold_path = paths.fonts_dir / "PULS_Schriftart.ttf"
    font_display_path = paths.fonts_dir / "PULS_Schriftart.ttf"
    # Für Datum und Watermark wieder Inter-Medium.ttf verwenden
    font_med_path = paths.fonts_dir / "Inter-Medium.ttf"

    # Größen (MVP)
    team_size = 23
    score_size = 60
    spieltag_size = 72
    date_size = 20
    blurb_size = 20

    # display map: slug -> display-name
    display_map = _load_team_display_map(paths.fonts_dir.parent)

    saison = int(spieltag_data.get("saison") or 0)
    spieltag = int(spieltag_data.get("spieltag") or 0)

    # Header: "SPIELTAG X" mit PULS_Schriftart.ttf
    header_text = f"SPIELTAG {spieltag}"
    font_spieltag = _load_font(font_display_path, spieltag_size)
    draw_text_fx(
        img,
        (layout.header_center_x, layout.header_spieltag_y),
        header_text,
        font_spieltag,
        fill=layout.color_text,
        anchor="mm",
        glow=False,
        shadow=True,
        shadow_offset=(0, 3),
        shadow_alpha=170,
        stroke=True,
        stroke_width=3,
        stroke_fill=(0, 0, 0, 200),
    )

    # Footer date: Δ...
    if not delta_date:
        raise ValueError("Δ-Datum fehlt. Bitte im Renderer-UI eintragen (z.B. 2125-10-18).")
    delta_date = str(delta_date).strip()
    if delta_date.lower().startswith("delta"):
        delta_date = delta_date[5:].strip()
    if delta_date.startswith("Δ"):
        delta_date = delta_date[1:].strip()
    date_str = f"Δ{delta_date}"

    font_date = _load_font(font_med_path, date_size)
    draw.text(
        (layout.footer_date_center_x, layout.footer_date_y),
        date_str,
        font=font_date,
        fill=layout.color_accent,
        anchor="mm",
    )

    # Match rows
    nord: List[Dict[str, Any]] = spieltag_data.get("nord", [])
    sued: List[Dict[str, Any]] = spieltag_data.get("sued", [])

    # Anpassen für separate Renderings
    team_font = _load_font(font_bold_path, team_size)
    score_font = _load_font(font_display_path, score_size)
    blurb_font = _load_font(font_display_path, blurb_size)

    # Textblock rechts: Platz (MVP) – musst du ggf. feinjustieren
    # Wir nehmen den Bereich rechts innerhalb der Match-Box.
 

    def _display_team(slug: str) -> str:
        return (display_map.get(slug, slug.replace("-", " "))).upper()

    def draw_match_row(y: int, home_name: str, away_name: str, gh: int, ga: int, overtime: bool, shootout: bool, last5_home: List[str], last5_away: List[str], line1: str) -> None:
        home_slug = _team_name_to_logo_slug(home_name, display_map)
        away_slug = _team_name_to_logo_slug(away_name, display_map)

        logo_home = _load_logo(paths.logos_dir, home_slug, layout.logo_size, layout.color_accent)
        logo_away = _load_logo(paths.logos_dir, away_slug, layout.logo_size, layout.color_accent)

        home_txt = _display_team(home_slug)
        away_txt = _display_team(away_slug)

        # Logos
        img.alpha_composite(logo_home, (layout.x_logo_home, int(y - layout.logo_size / 2)))
        img.alpha_composite(logo_away, (layout.x_logo_away, int(y - layout.logo_size / 2)))

        # Team text (clean FX)
        draw_text_fx(
            img,
            (layout.x_text_home, y),
            home_txt,
            team_font,
            fill=layout.color_text,
            anchor="lm",
            glow=False,
            shadow=True,
            shadow_offset=(0, 2),
            shadow_alpha=140,
            stroke=True,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 190),
        )
        draw_text_fx(
            img,
            (layout.x_text_away, y),
            away_txt,
            team_font,
            fill=layout.color_text,
            anchor="rm",
            glow=False,
            shadow=True,
            shadow_offset=(0, 2),
            shadow_alpha=140,
            stroke=True,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 190),
        )

        # Score in der Mitte
        score_txt = f"{gh}:{ga}"
        draw_text_fx(
            img,
            (layout.center_x, y),
            score_txt,
            score_font,
            fill=layout.color_accent,
            anchor="mm",
            glow=False,
            shadow=True,
            shadow_offset=(0, 2),
            shadow_alpha=140,
            stroke=True,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 180),
        )

        # OT/SO als Badge rechts neben Score
        if overtime or shootout:
            badge_txt = "OT" if overtime else "SO"
            badge_x = layout.center_x + _text_w(draw, score_txt, score_font) // 2 + 10  # rechts neben Score
            badge_font = _load_font(font_med_path, 16)  # kleiner
            draw_text_fx(
                img,
                (badge_x, y),
                badge_txt,
                badge_font,
                fill=layout.color_accent,
                anchor="lm",
                glow=False,
                shadow=True,
                shadow_offset=(0, 1),
                shadow_alpha=150,
                stroke=True,
                stroke_width=1,
                stroke_fill=(0, 0, 0, 200),
            )

        # last5 unter Logos
        last5_home_txt = " ".join(last5_home[-5:])  # letzte 5
        last5_away_txt = " ".join(last5_away[-5:])
        last5_font = _load_font(font_bold_path, layout.last5_font_size)
        last5_home_y = y + layout.logo_size + layout.last5_y_offset
        last5_away_y = y + layout.logo_size + layout.last5_y_offset
        draw_text_fx(
            img,
            (layout.x_logo_home + layout.last5_x_offset_home, last5_home_y),
            last5_home_txt,
            last5_font,
            fill=layout.color_text,
            anchor="lm",  # linksbündig
        )
        draw_text_fx(
            img,
            (layout.x_logo_away + layout.logo_size + layout.last5_x_offset_away, last5_away_y),
            last5_away_txt,
            last5_font,
            fill=layout.color_text,
            anchor="rm",  # rechtsbündig
        )

        # Line1 und Line2 unter dem Score
        # Hole narratives (line1, line2) aus narratives_data falls vorhanden
        key = f"{home_name}-{away_name}"
        match_data = narratives_data.get(key, {})
        line2 = match_data.get("line2", "")
        if line1 or line2:
            line1_y = y + 50
            max_width = int(layout.center_x * 0.85)
            # Beide Zeilen als ein Block, dann auf 2 Zeilen umbrechen
            textblock = " ".join([t for t in [line1, line2] if t]).strip()
            if textblock:
                wrapped = _wrap_to_n_lines(draw, textblock, blurb_font, max_width, 2)
                for j, ln in enumerate(wrapped):
                    if ln:
                        draw_text_fx(
                            img,
                            (layout.center_x, line1_y + j * 24),
                            ln,
                            blurb_font,
                            fill=layout.color_text,
                            anchor="mm",
                            glow=False,
                            shadow=True,
                            shadow_offset=(0, 1),
                            shadow_alpha=120,
                            stroke=False,
                        )


    if isinstance(layout, ConferenceLayoutV1):
        # Für separate Konferenzen: verwende y_matches
        matches = nord if nord else sued
        for i, m in enumerate(matches):
            last5_home = _get_last5_for_team(latest_data, m["home_name"])
            last5_away = _get_last5_for_team(latest_data, m["away_name"])
            line1 = _get_line1_for_match(narratives_data, m["home_name"], m["away_name"])
            draw_match_row(layout.y_matches[i], m["home_name"], m["away_name"], m["goals_home"], m["goals_away"], m["overtime"], m["shootout"], last5_home, last5_away, line1)
    else:
        # Für kombinierte: verwende y_nord und y_sued
        for i, m in enumerate(nord):
            last5_home = _get_last5_for_team(latest_data, m["home_name"])
            last5_away = _get_last5_for_team(latest_data, m["away_name"])
            line1 = _get_line1_for_match(narratives_data, m["home_name"], m["away_name"])
            draw_match_row(layout.y_nord[i], m["home_name"], m["away_name"], m["goals_home"], m["goals_away"], m["overtime"], m["shootout"], last5_home, last5_away, line1)

        for i, m in enumerate(sued):
            last5_home = _get_last5_for_team(latest_data, m["home_name"])
            last5_away = _get_last5_for_team(latest_data, m["away_name"])
            line1 = _get_line1_for_match(narratives_data, m["home_name"], m["away_name"])
            draw_match_row(layout.y_sued[i], m["home_name"], m["away_name"], m["goals_home"], m["goals_away"], m["overtime"], m["shootout"], last5_home, last5_away, line1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
        # ---- Watermark (wie im Spieltag-Renderer) ----
    wm_font = ImageFont.truetype(str(font_med_path), size=20)
    _draw_watermark(
        img,
        draw,
        text="powered by HIGHspeeΔ PUX! Engine",
        font=wm_font,
        margin=22,
        opacity=110,
    )

    
    
    img.save(out_path)
    return out_path


def render_from_spieltag_file(
    spieltag_json_path: Path,
    template_name: str = "matchday_overview_v1.png",
    out_name: Optional[str] = None,
    delta_date: Optional[str] = None,
    latest_path: Optional[Path] = None,
    narratives_path: Optional[Path] = None,
    edited_blurbs: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Path]:
    base_dir = Path(__file__).resolve().parent  # tools/puls_renderer
    paths = RenderPaths(base_dir=base_dir)

    raw = _safe_load_json(spieltag_json_path)
    data = convert_spieltag_json_to_results(raw)

    spieltag = int(data.get("spieltag") or 0)
    saison = int(data.get("saison") or 0)

    template_path = paths.templates_dir / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    out_paths = []

    # Render Nord
    nord_data = {"saison": saison, "spieltag": spieltag, "nord": data["nord"], "sued": []}
    nord_template_name = "matchday_results_v1_nord.png" if data["nord"] else template_name
    nord_template_path = paths.templates_dir / nord_template_name
    if not nord_template_path.exists():
        nord_template_path = paths.templates_dir / template_name  # fallback
    if out_name is None:
        nord_out_name = f"results_nord_s{saison:02d}_spieltag_{spieltag:02d}.png"
    else:
        nord_out_name = out_name.replace(".png", "_nord.png")
    nord_out_path = paths.output_dir / nord_out_name
    out_paths.append(render_matchday_results_overview(
        template_path=nord_template_path,
        spieltag_data=nord_data,
        paths=paths,
        out_path=nord_out_path,
        layout=ConferenceLayoutV1(),
        delta_date=delta_date,
        latest_path=latest_path,
        narratives_path=narratives_path,
    ))

    # Render Süd
    sued_data = {"saison": saison, "spieltag": spieltag, "nord": [], "sued": data["sued"]}
    sued_template_name = "matchday_results_v1.png" if data["sued"] else template_name
    sued_template_path = paths.templates_dir / sued_template_name
    if not sued_template_path.exists():
        sued_template_path = paths.templates_dir / template_name  # fallback
    if out_name is None:
        sued_out_name = f"results_sued_s{saison:02d}_spieltag_{spieltag:02d}.png"
    else:
        sued_out_name = out_name.replace(".png", "_sued.png")
    sued_out_path = paths.output_dir / sued_out_name
    out_paths.append(render_matchday_results_overview(
        template_path=sued_template_path,
        spieltag_data=sued_data,
        paths=paths,
        out_path=sued_out_path,
        layout=ConferenceLayoutV1(),
        delta_date=delta_date,
        latest_path=latest_path,
        narratives_path=narratives_path,
    ))

    return out_paths


if __name__ == "__main__":
    # Quick local test:
    # python tools/puls_renderer/results_renderer.py data/spieltage/saison_01/spieltag_01.json 2125-10-18
    import sys
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python tools/puls_renderer/results_renderer.py <spieltag_json> <delta_date>")
    spieltag_path = Path(sys.argv[1])
    delta_date = sys.argv[2]
    
    # Errate Pfade
    toolbox_root = spieltag_path.parents[3]  # .../toolbox
    saison = int(spieltag_path.parent.name.split('_')[1])  # saison_01 -> 1
    spieltag = int(spieltag_path.name.split('_')[1].split('.')[0])  # spieltag_01.json -> 1
    latest_path = toolbox_root / "data" / "stats" / f"saison_{saison:02d}" / "league" / f"after_spieltag_{spieltag:02d}_detail.json"
    print(f"[DEBUG] last5 latest_path: {latest_path}")
    narratives_path = toolbox_root / "data" / "replays" / f"saison_{saison:02d}" / f"spieltag_{spieltag:02d}" / "narratives.json"

    paths = render_from_spieltag_file(spieltag_path, delta_date=delta_date, latest_path=latest_path, narratives_path=narratives_path)
    print(f"Generated: {paths}")
