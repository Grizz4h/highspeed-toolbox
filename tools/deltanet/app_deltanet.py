import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
FORMATS_PATH = BASE_DIR / "deltanet_formats.json"
HASHTAGS_PATH = BASE_DIR / "deltanet_hashtags.json"
POSTS_PATH = BASE_DIR / "deltanet_posts.json"

def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def _hashtags(platform: str, pillar_id: str, hashtags_cfg: dict) -> list[str]:
    out = []
    out += hashtags_cfg.get("defaults", {}).get(platform, [])
    out += hashtags_cfg.get("by_pillar", {}).get(pillar_id, {}).get(platform, [])
    # unique, keep order
    seen = set()
    uniq = []
    for h in out:
        if h not in seen:
            uniq.append(h)
            seen.add(h)
    return uniq

def render():
    st.title("📡 ΔNET Content Hub")
    st.caption("Kanal-agnostischer Content-Planer (TikTok / Instagram / X / GIFs) – JSON-erweiterbar.")

    cfg = _load_json(FORMATS_PATH, {})
    hashtags_cfg = _load_json(HASHTAGS_PATH, {})
    posts = _load_json(POSTS_PATH, [])

    platforms = cfg.get("platforms", ["tiktok", "instagram", "x", "gifs"])
    pillars = cfg.get("pillars", [])
    formats = cfg.get("formats", [])

    if not pillars or not formats:
        st.error("Config fehlt/leer: deltanet_formats.json")
        st.stop()

    col1, col2, col3 = st.columns([1,1,1])

    with col1:
        platform = st.selectbox("Plattform", options=platforms, key="dn_platform")

    with col2:
        pillar_label = st.selectbox("Säule", options=[p["label"] for p in pillars], key="dn_pillar")
        pillar_id = next(p["id"] for p in pillars if p["label"] == pillar_label)

    with col3:
        viable = [f for f in formats if platform in f.get("platforms", []) and pillar_id in f.get("pillars", [])]
        if not viable:
            st.warning("Keine Formate für diese Kombination.")
            st.stop()
        format_label = st.selectbox("Format", options=[f["label"] for f in viable], key="dn_format")
        fmt = next(f for f in viable if f["label"] == format_label)

    st.divider()

    st.subheader("✍️ Inhalt")
    hook = st.text_input("Hook (kurz)", placeholder="z.B. GAMEDAY. / ΔNET | Kurzmeldung / Systemfehler.")
    text = st.text_area("Text / Caption", height=120, placeholder="1–2 Sätze, keine Erklär-Romane.")
    asset = st.text_input("Asset/Datei (optional)", placeholder="z.B. /exports/gifs/jaro_glitch_01.gif")

    suggested = _hashtags(platform, pillar_id, hashtags_cfg)
    st.subheader("🏷️ Hashtags / Tags (Vorschlag)")
    st.code(" ".join(suggested), language="text")

    st.subheader("📦 Output (copy/paste)")
    if platform == "x":
        out = f"{hook}\n{text}\n\n" + " ".join(suggested)
    elif platform == "gifs":
        out = f"{hook}\n{text}\nTags: {', '.join([t.strip('#') for t in suggested])}"
    else:
        out = f"{hook}\n\n{text}\n\n" + " ".join(suggested)

    st.text_area("Final", value=out.strip(), height=160)

    st.divider()

    st.subheader("🧾 Log")
    if st.button("✅ Als Post speichern", key="dn_save_post"):
        posts.append({
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "platform": platform,
            "pillar": pillar_id,
            "format": fmt["id"],
            "hook": hook.strip(),
            "text": text.strip(),
            "asset": asset.strip(),
            "hashtags": suggested
        })
        _save_json(POSTS_PATH, posts)
        st.success("Gespeichert.")
        st.rerun()

    if posts:
        st.caption(f"{len(posts)} Einträge")
        for p in reversed(posts[-10:]):
            with st.container(border=True):
                st.write(f"**{p['platform']} / {p['pillar']} / {p['format']}** — {p['ts']}")
                st.write(p.get("hook",""))
                st.write(p.get("text",""))
                if p.get("asset"):
                    st.caption(f"asset: {p['asset']}")
                st.code(" ".join(p.get("hashtags", [])))
