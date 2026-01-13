# tools/puls_renderer/results_renderer.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .layout_config import MatchdayLayoutV1


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

    # auf n Zeilen begrenzen + letzte kürzen
    if len(lines) <= n:
        lines += [""] * (n - len(lines))
        return lines[:n]

    # zu viele: n-1 behalten, letzte zusammenfassen + trunc
    head = lines[: n - 1]
    tail = " ".join(lines[n - 1 :])
    tail = _truncate_line(draw, tail, font, max_w)
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


def _two_sentence_blurb_from_replay(replay_json: Dict[str, Any], home_name: str, away_name: str, score_home: int, score_away: int) -> str:
    events = replay_json.get("events", []) or []
    goals = [e for e in events if (e.get("type") == "goal")]

    if not goals:
        return f"{home_name} gewinnt {score_home}:{score_away} gegen {away_name}. Wenig Highlights im Protokoll."

    # Reihenfolge: wie im Log
    first = goals[0]
    first_team = first.get("team", "")
    first_scorer = ((first.get("scorer") or {}).get("id") or "").replace("_", " ").strip()

    # wer hat den "Siegtreffer" gemacht? -> letzter goal-event
    last = goals[-1]
    last_team = last.get("team", "")
    last_scorer = ((last.get("scorer") or {}).get("id") or "").replace("_", " ").strip()

    # Teams aus Log sind meist "home"/"away" oder echte Namen – wir machen’s robust
    def _team_label(t: str) -> str:
        tl = (t or "").strip().lower()
        if tl == "home":
            return home_name
        if tl == "away":
            return away_name
        # falls Teamname drinsteht
        if tl:
            return t
        return ""

    first_team_lbl = _team_label(first_team)
    last_team_lbl = _team_label(last_team)

    s1 = f"{first_team_lbl} eröffnete das Spiel früh"
    if first_scorer:
        s1 += f" durch {first_scorer}."
    else:
        s1 += "."

    # Satz 2: Siegtreffer/Unterschied
    if last_team_lbl:
        s2 = f"Am Ende setzte sich {home_name} {score_home}:{score_away} durch – den Unterschied machte {last_scorer or last_team_lbl}."
    else:
        s2 = f"Am Ende setzte sich {home_name} {score_home}:{score_away} durch."

    return f"{s1} {s2}"


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

        item = {
            "home_name": str(home_name),
            "away_name": str(away_name),
            "goals_home": int(gh or 0),
            "goals_away": int(ga or 0),
            "conference": conf,
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
    blurb_list: Optional[List[Dict[str, str]]] = None,
) -> Path:
    layout = layout or MatchdayLayoutV1()

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Fonts (wie bei euch)
    font_display_path = paths.fonts_dir / "PULS_Schriftart.ttf"   # NEW (nur für "SPIELTAG")
    font_bold_path = paths.fonts_dir / "Inter-Bold.ttf"
    font_med_path = paths.fonts_dir / "Inter-Medium.ttf"

    # Größen (MVP)
    team_size = 23
    score_size = 34
    spieltag_size = 72
    date_size = 20
    blurb_size = layout.blurb_font_size

    # display map: slug -> display-name
    display_map = _load_team_display_map(paths.fonts_dir.parent)

    saison = int(spieltag_data.get("saison") or 0)
    spieltag = int(spieltag_data.get("spieltag") or 0)

    blurb_list = blurb_list or []

    # Header: Test-Titel für Schriftart
        # Header: Generischer Test-Titel
    header_text = "HEADER TEST"
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



    import streamlit as st
    font_spieltag = _load_font(font_display_path, spieltag_size)
    st.write(f"[DEBUG] Font für SPIELTAG geladen: {font_spieltag}")
    st.write(f"[DEBUG] Font-Pfad: {font_display_path}")
    st.write(f"[DEBUG] Header-Text: {header_text}")
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

    # Wir halten erstmal an 5/5 fest, weil Template so ist.
    if len(nord) != 5 or len(sued) != 5:
        raise ValueError(f"Template erwartet 5 nord + 5 sued. Got nord={len(nord)} sued={len(sued)}")

    team_font = _load_font(font_bold_path, team_size)
    score_font = _load_font(font_bold_path, score_size)
    blurb_font = _load_font(font_med_path, blurb_size)

    # Textblock rechts: Platz (MVP) – musst du ggf. feinjustieren
    # Wir nehmen den Bereich rechts innerhalb der Match-Box.
 

    def _display_team(slug: str) -> str:
        return (display_map.get(slug, slug.replace("-", " "))).upper()

    def draw_blurb(x: int, y: int, line1: str, line2: str) -> None:
        if not line1 and not line2:
            return
        text = f"{line1}\n{line2}".strip()
        if not text:
            return
        # Wrap to fit
        wrapped = _wrap_to_n_lines(draw, text, blurb_font, layout.max_width_blurb, 2)
        for i, line in enumerate(wrapped):
            if line:
                draw_text_fx(
                    img,
                    (x, y + i * 14),  # 14 pixel pro Zeile
                    line,
                    blurb_font,
                    fill=layout.color_text,
                    anchor="la",
                    glow=False,
                    shadow=True,
                    shadow_offset=(0, 1),
                    shadow_alpha=120,
                    stroke=False,
                )

    def draw_match_row(y: int, home_name: str, away_name: str, gh: int, ga: int) -> None:
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

        # Score in der Mitte statt VS
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


    for i, m in enumerate(nord):
        draw_match_row(layout.y_nord[i], m["home_name"], m["away_name"], m["goals_home"], m["goals_away"])
        if i < len(blurb_list):
            blurb = blurb_list[i]
            draw_blurb(layout.x_blurb, layout.y_blurb_nord[i], blurb.get("line1", ""), blurb.get("line2", ""))

    for i, m in enumerate(sued):
        draw_match_row(layout.y_sued[i], m["home_name"], m["away_name"], m["goals_home"], m["goals_away"])
        idx = i + len(nord)
        if idx < len(blurb_list):
            blurb = blurb_list[idx]
            draw_blurb(layout.x_blurb, layout.y_blurb_sued[i], blurb.get("line1", ""), blurb.get("line2", ""))

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
) -> Path:
    base_dir = Path(__file__).resolve().parent  # tools/puls_renderer
    paths = RenderPaths(base_dir=base_dir)

    raw = _safe_load_json(spieltag_json_path)
    data = convert_spieltag_json_to_results(raw)

    spieltag = int(data.get("spieltag") or 0)
    saison = int(data.get("saison") or 0)

    template_path = paths.templates_dir / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    if out_name is None:
        out_name = f"results_s{saison:02d}_spieltag_{spieltag:02d}.png"

    out_path = paths.output_dir / out_name

    return render_matchday_results_overview(
        template_path=template_path,
        spieltag_data=data,
        paths=paths,
        out_path=out_path,
        layout=MatchdayLayoutV1(),
        delta_date=delta_date,
    )


if __name__ == "__main__":
    # Quick local test:
    # python tools/puls_renderer/results_renderer.py data/spieltage/saison_01/spieltag_01.json 2125-10-18
    import sys
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python tools/puls_renderer/results_renderer.py <spieltag_json> <delta_date>")
    render_from_spieltag_file(Path(sys.argv[1]), delta_date=sys.argv[2])
