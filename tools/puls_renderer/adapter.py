import re
import unicodedata
from typing import Dict, Any, List

UMLAUT_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "ae", "Ö": "oe", "Ü": "ue",
    "ß": "ss",
}

def slugify_team(name: str) -> str:
    # Umlaut-Handling
    for k, v in UMLAUT_MAP.items():
        name = name.replace(k, v)

    # Unicode normalisieren (Akzente entfernen)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))

    # Sonderzeichen raus, Whitespace -> "-"
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-{2,}", "-", name)
    return name

def convert_generator_json_to_matchday(data: Dict[str, Any]) -> Dict[str, Any]:
    spieltag = data["spieltag"]
    timestamp = data.get("timestamp", "")
    date = timestamp.split("T")[0] if "T" in timestamp else timestamp

    nord: List[Dict[str, str]] = []
    sued: List[Dict[str, str]] = []

    for r in data["results"]:
        home_id = slugify_team(r["home"])
        away_id = slugify_team(r["away"])
        conf = r.get("conference", "").lower()

        item = {"home": home_id, "away": away_id}

        if conf == "nord":
            nord.append(item)
        elif conf in ("süd", "sued"):
            sued.append(item)
        else:
            raise ValueError(f"Unknown conference: {r.get('conference')}")

    if len(nord) != 5 or len(sued) != 5:
        raise ValueError(f"Expected 5 nord + 5 sued matches. Got nord={len(nord)} sued={len(sued)}")

    return {
        "spieltag": spieltag,
        "date": date,
        "nord": nord,
        "sued": sued,
    }
