import json
import uuid
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
RELEASES_PATH = BASE_DIR / "product_releases.json"

@dataclass
class ProductRelease:
    id: str
    release_date: str                # ISO yyyy-mm-dd
    brand_id: str
    brand_name: str
    product_type: str
    product_name: str
    notes: str = ""
    meta: Optional[Dict[str, Any]] = None

def load_releases() -> List[ProductRelease]:
    if not RELEASES_PATH.exists():
        return []
    try:
        raw = json.loads(RELEASES_PATH.read_text(encoding="utf-8"))
        out: List[ProductRelease] = []
        for r in raw:
            out.append(ProductRelease(
                id=str(r.get("id") or uuid.uuid4().hex),
                release_date=str(r["release_date"]),
                brand_id=str(r["brand_id"]),
                brand_name=str(r["brand_name"]),
                product_type=str(r["product_type"]),
                product_name=str(r["product_name"]),
                notes=str(r.get("notes", "")),
                meta=r.get("meta"),
            ))
        return out
    except Exception:
        return []

def save_releases(releases: List[ProductRelease]) -> None:
    RELEASES_PATH.write_text(
        json.dumps([asdict(r) for r in releases], indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def add_release(
    releases: List[ProductRelease],
    *,
    release_date: date,
    brand_id: str,
    brand_name: str,
    product_type: str,
    product_name: str,
    notes: str = "",
    meta: Dict[str, Any] = None
) -> ProductRelease:
    r = ProductRelease(
        id=uuid.uuid4().hex,
        release_date=release_date.isoformat(),
        brand_id=brand_id,
        brand_name=brand_name,
        product_type=product_type,
        product_name=product_name,
        notes=notes.strip(),
        meta=meta,
    )
    releases.append(r)
    return r

def delete_release(releases: List[ProductRelease], release_id: str) -> None:
    releases[:] = [r for r in releases if r.id != release_id]

def releases_by_brand(releases: List[ProductRelease], brand_id: str) -> List[ProductRelease]:
    return [r for r in releases if r.brand_id == brand_id]
