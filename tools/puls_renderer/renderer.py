import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont

from .layout_config import MatchdayLayoutV1
from .adapter import convert_generator_json_to_matchday



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


def _safe_load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not font_path.exists():
        raise FileNotFoundError(f"Font not found: {font_path}")
    return ImageFont.truetype(str(font_path), size)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font_path: Path, max_width: int, start_size: int, min_size: int = 18):
    size = start_size
    while size >= min_size:
        font = _load_font(font_path, size)
        w = draw.textlength(text, font=font)
        if w <= max_width:
            return font
        size -= 2
    return _load_font(font_path, min_size)


def _load_logo(logos_dir: Path, team_id: str, size: int, accent: Tuple[int, int, int, int]) -> Image.Image:
    p = logos_dir / f"{team_id}.png"
    if p.exists():
        img = Image.open(p).convert("RGBA")
        return img.resize((size, size), Image.LANCZOS)

    # Fallback: Platzhalterlogo (Kreis)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((3, 3, size - 3, size - 3), outline=accent, width=3)
    return img


def render_matchday_overview(
    template_path: Path,
    data: Dict[str, Any],
    logos_dir: Path,
    fonts_dir: Path,
    out_path: Path,
    layout: Optional[MatchdayLayoutV1] = None,
    enable_draw_vs: bool = False,
    delta_date: Optional[str] = None,   # <<< NEU
) -> Path:
    """
    Rendert eine Spieltagsübersicht:
    [Logo Heim] [Name Heim]   (VS frei)   [Name Away] [Logo Away]
    - Spieltag + Datum aus JSON
    - Nord 5 Paarungen, Süd 5 Paarungen
    """
    layout = layout or MatchdayLayoutV1()

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Fonts
    font_bold_path = fonts_dir / "Inter-Bold.ttf"
    font_med_path = fonts_dir / "Inter-Medium.ttf"

    # Basissizes (werden bei langen Namen automatisch verkleinert)
    team_size = 23
    spieltag_size = 72
    date_size = 20
    vs_size = 34

    # Header: SPIELTAG {n}
    spieltag = data.get("spieltag")
    if spieltag is None:
        raise ValueError("JSON missing required field: spieltag")

    header_text = f"SPIELTAG {spieltag}"
    font_spieltag = _fit_text(draw, header_text, font_bold_path, max_width=900, start_size=spieltag_size, min_size=34)
    draw.text(
        (layout.header_center_x, layout.header_spieltag_y),
        header_text,
        font=font_spieltag,
        fill=layout.color_accent,
        anchor="mm",
    )

    # Footer: Δ-Datum kommt aus UI (nicht aus JSON)
    if not delta_date:
        raise ValueError("Δ-Datum fehlt. Bitte im Renderer-UI eintragen (z.B. 2125-10-18).")

    # Normalisieren: Benutzer kann mit oder ohne Δ eingeben
    delta_date = str(delta_date).strip()
    if delta_date.lower().startswith("delta"):
        delta_date = delta_date[5:].strip()
    if delta_date.startswith("Δ"):
        delta_date = delta_date[1:].strip()

    date_str = f"Δ{delta_date}"

    font_date = _fit_text(draw, date_str, font_med_path, max_width=700, start_size=date_size, min_size=24)
    draw.text(
        (layout.footer_date_center_x, layout.footer_date_y),
        date_str,
        font=font_date,
        fill=layout.color_accent,
        anchor="mm",
    )

    def _truncate_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        if draw.textlength(text, font=font) <= max_width:
            return text
        ell = "…"
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            cand = text[:mid].rstrip() + ell
            if draw.textlength(cand, font=font) <= max_width:
                lo = mid + 1
            else:
                hi = mid
        return text[:max(0, lo - 1)].rstrip() + ell


    # Matches
    nord: List[Dict[str, str]] = data.get("nord", [])
    sued: List[Dict[str, str]] = data.get("sued", [])

    if len(nord) != 5 or len(sued) != 5:
        raise ValueError(f"Expected 5 nord + 5 sued matches. Got nord={len(nord)} sued={len(sued)}")

    display_map_path = fonts_dir.parent / "team_display_names.json"
    display_map = {}
    if display_map_path.exists():
        import json
        display_map = json.loads(display_map_path.read_text(encoding="utf-8"))



    def draw_match_row(y: int, home_id: str, away_id: str):
        # Logos
        logo_home = _load_logo(logos_dir, home_id, layout.logo_size, layout.color_accent)
        logo_away = _load_logo(logos_dir, away_id, layout.logo_size, layout.color_accent)

        # Text (Uppercase, weil Newsdesk)
        home_label = display_map.get(home_id, home_id.replace("-", " "))
        away_label = display_map.get(away_id, away_id.replace("-", " "))
        home_txt = home_label.upper()
        away_txt = away_label.upper()

        team_font = _load_font(font_bold_path, team_size)
        home_txt = _truncate_to_width(draw, home_txt, team_font, layout.max_width_home)
        away_txt = _truncate_to_width(draw, away_txt, team_font, layout.max_width_away)

        # Positioning (Symmetrie)
        # Logos vertikal zentriert auf Zeilen-Y
        img.alpha_composite(logo_home, (layout.x_logo_home, int(y - layout.logo_size / 2)))
        img.alpha_composite(logo_away, (layout.x_logo_away, int(y - layout.logo_size / 2)))

        # Teamnamen: Heim links, Away rechts
        draw.text((layout.x_text_home, y), home_txt, font=team_font, fill=layout.color_text, anchor="lm")
        draw.text((layout.x_text_away, y), away_txt, font=team_font, fill=layout.color_text, anchor="rm")

        # VS optional (du willst es erstmal ins Template malen -> default False)
        if enable_draw_vs:
            font_vs = _fit_text(draw, "VS", font_med_path, max_width=120, start_size=vs_size, min_size=22)
            draw.text((layout.center_x, y), "VS", font=font_vs, fill=layout.color_accent, anchor="mm")

    # Nord rows
    for i, m in enumerate(nord):
        draw_match_row(layout.y_nord[i], m["home"], m["away"])

    # Süd rows
    for i, m in enumerate(sued):
        draw_match_row(layout.y_sued[i], m["home"], m["away"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def render_from_json_file(
    json_path: Path,
    template_name: str = "matchday_overview_v1.png",
    out_name: Optional[str] = None,
    enable_draw_vs: bool = False,
    delta_date: Optional[str] = None, 
) -> Path:
    """
    Convenience: rendert direkt aus einer JSON-Datei.
    """
    base_dir = Path(__file__).resolve().parent
    paths = RenderPaths(base_dir=base_dir)
    layout = MatchdayLayoutV1()

    raw = _safe_load_json(json_path)
# Wenn generator-json: hat "results" und keine "nord"/"sued"
    if "results" in raw and "nord" not in raw and "sued" not in raw:
        data = convert_generator_json_to_matchday(raw)
    else:
        data = raw

    template_path = paths.templates_dir / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    spieltag = data.get("spieltag", "XX")
    if out_name is None:
        out_name = f"spieltag_{int(spieltag):02d}.png" if str(spieltag).isdigit() else f"spieltag_{spieltag}.png"

    out_path = paths.output_dir / out_name

    return render_matchday_overview(
        template_path=template_path,
        data=data,
        logos_dir=paths.logos_dir,
        fonts_dir=paths.fonts_dir,
        out_path=out_path,
        layout=layout,
        enable_draw_vs=enable_draw_vs,
        delta_date=delta_date,   # <<< NEU
    )
