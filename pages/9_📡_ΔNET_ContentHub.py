import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import streamlit as st

st.set_page_config(page_title="📡 ΔNET Content Hub", layout="wide")

RELEASE_STATUSES = ["DRAFT", "READY", "POSTED", "ARCHIVED"]
CONTENT_STATUSES = ["DRAFT", "READY", "READY_FOR_REVIEW", "READY_FOR_RENDER", "POSTED", "ARCHIVED"]
CHANNELS = ["IG_FEED", "IG_STORY", "X", "THREADS", "IG_REEL"]
PERSONAL_LINE_CATEGORIES = ["PROCESS", "EMOTION", "THOUGHT"]
RELEASE_TYPES = ["EPISODE", "EPISODE_SUPPORT", "WORLD_DROP", "SPORT_EVENT", "ANNOUNCEMENT"]
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "content_hub_state.json"


def init_state() -> None:
	state = st.session_state
	state.setdefault("release_events", [])
	state.setdefault("content_items", [])
	state.setdefault("story_sequences", [])
	state.setdefault("story_slides", [])
	state.setdefault("personal_line_history", [])
	state.setdefault("id_counters", {"release": 1, "content": 1, "sequence": 1, "slide": 1})


def serialize_state() -> Dict:
	def _ser_dt(val):
		return val.isoformat() if isinstance(val, dt.datetime) else val

	return {
		"release_events": [
			{**ev, "release_datetime": _ser_dt(ev.get("release_datetime")), "created_at": _ser_dt(ev.get("created_at"))}
			for ev in st.session_state.get("release_events", [])
		],
		"content_items": [
			{**ci, "posted_at": _ser_dt(ci.get("posted_at"))}
			for ci in st.session_state.get("content_items", [])
		],
		"story_sequences": st.session_state.get("story_sequences", []),
		"story_slides": st.session_state.get("story_slides", []),
		"personal_line_history": st.session_state.get("personal_line_history", []),
		"id_counters": st.session_state.get("id_counters", {}),
	}


def save_state() -> None:
	STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
	with STATE_FILE.open("w", encoding="utf-8") as f:
		json.dump(serialize_state(), f, ensure_ascii=False, indent=2)


def load_state() -> None:
	if not STATE_FILE.exists():
		return
	try:
		with STATE_FILE.open("r", encoding="utf-8") as f:
			data = json.load(f)
		evts = data.get("release_events", [])
		for ev in evts:
			if ev.get("release_datetime"):
				ev["release_datetime"] = dt.datetime.fromisoformat(ev["release_datetime"])
			if ev.get("created_at"):
				ev["created_at"] = dt.datetime.fromisoformat(ev["created_at"])
		cis = data.get("content_items", [])
		for ci in cis:
			if ci.get("posted_at"):
				ci["posted_at"] = dt.datetime.fromisoformat(ci["posted_at"])
		st.session_state["release_events"] = evts
		st.session_state["content_items"] = cis
		st.session_state["story_sequences"] = data.get("story_sequences", [])
		st.session_state["story_slides"] = data.get("story_slides", [])
		st.session_state["personal_line_history"] = data.get("personal_line_history", [])
		st.session_state["id_counters"] = data.get("id_counters", {"release": 1, "content": 1, "sequence": 1, "slide": 1})
	except Exception as exc:  # noqa: BLE001
		st.warning(f"Konnte State nicht laden: {exc}")


def next_id(kind: str) -> str:
	counters = st.session_state["id_counters"]
	value = counters.get(kind, 1)
	counters[kind] = value + 1
	return f"{kind[:3].upper()}-{value:04d}"


def upsert_content_item(event_id: str, channel: str) -> Dict:
	items = st.session_state["content_items"]
	for item in items:
		if item["release_event_id"] == event_id and item["channel"] == channel:
			return item
	item = {
		"id": next_id("content"),
		"release_event_id": event_id,
		"channel": channel,
		"status": "DRAFT",
		"caption_text": "",
		"hashtags": [],
		"media_asset_ids": [],
		"post_url": None,
		"posted_at": None,
		"render_spec": None,
	}
	items.append(item)
	return item


def get_release(event_id: str) -> Optional[Dict]:
	for event in st.session_state["release_events"]:
		if event["id"] == event_id:
			return event
	return None


def validate_website_url(url: str, perform_network: bool = True) -> Dict:
	errors: List[str] = []
	parsed = urlparse(url.strip())
	if parsed.scheme not in {"https", "http"} or not parsed.netloc:
		errors.append("URL muss http(s) mit Domain + Pfad sein.")
	if perform_network and not errors:
		try:
			req = Request(url, method="HEAD")
			with urlopen(req, timeout=4) as resp:
				if resp.status >= 400:
					errors.append(f"HTTP Status {resp.status}")
		except Exception as exc:  # noqa: BLE001
			errors.append(f"HTTP Check fehlgeschlagen: {exc}")
	return {"ok": len(errors) == 0, "errors": errors}


def auto_pipeline(event: Dict, include_reel: bool) -> List[Dict]:
	channels = ["IG_FEED", "IG_STORY", "X", "THREADS"]
	if include_reel:
		channels.append("IG_REEL")
	created = []
	for ch in channels:
		created.append(upsert_content_item(event["id"], ch))
	return created


def create_release_event(release_type: str, title: str, website_url: Optional[str], episode_id: Optional[str], release_datetime: Optional[dt.datetime], key_visual_asset_id: Optional[str], include_reel: bool) -> Dict:
	event = {
		"id": next_id("release"),
		"type": release_type,
		"episode_id": episode_id,
		"title": title,
		"website_url": website_url,
		"release_datetime": release_datetime,
		"status": "DRAFT",
		"validation": None,
		"key_visual_asset_id": key_visual_asset_id,
		"created_at": dt.datetime.now(),
	}
	st.session_state["release_events"].append(event)
	auto_pipeline(event, include_reel=include_reel)
	return event


def ensure_story_sequence(event_id: str) -> Dict:
	for seq in st.session_state["story_sequences"]:
		if seq["release_event_id"] == event_id:
			return seq
	seq = {"id": next_id("sequence"), "release_event_id": event_id}
	st.session_state["story_sequences"].append(seq)
	return seq


def set_story_slides(sequence_id: str, slides: List[Dict]) -> List[Dict]:
	st.session_state["story_slides"] = [s for s in st.session_state["story_slides"] if s["sequence_id"] != sequence_id]
	stored = []
	for slide in slides:
		stored_slide = {
			"id": next_id("slide"),
			"sequence_id": sequence_id,
			"slide_index": slide.get("slide_index"),
			"template_id": slide.get("template_id"),
			"media_asset_id": slide.get("media_asset_id"),
			"overlay_text": slide.get("overlay_text"),
			"link_url": slide.get("link_url"),
		}
		stored.append(stored_slide)
	st.session_state["story_slides"].extend(stored)
	return stored


def generate_ig_caption(title: str, one_liner: str, website_url: str, tone_profile: str, hashtag_set_id: str) -> Dict:
	base = f"Neue Episode: {title}."
	hook = one_liner.strip() if one_liner else "Jetzt live."
	cta = "Link in Bio / Story"
	tone = f" [{tone_profile}]" if tone_profile else ""
	caption = f"{base} {hook} {cta}{tone}"
	tags = default_hashtags(hashtag_set_id)[:5]
	return {"caption": caption, "hashtags": tags}


def default_hashtags(hashtag_set_id: str) -> List[str]:
	mapped = {
		"default": ["#release", "#episode", "#behindthescenes", "#newdrop", "#community"],
		"calm": ["#update", "#listen", "#story"],
	}
	return mapped.get(hashtag_set_id, mapped["default"])


def generate_personal_lines(last_used: List[str]) -> List[Dict]:
	templates = {
		"PROCESS": [
			"Ich liebe den Grind hinter dieser Folge.",
			"Heute nur deep work und eine Kamera.",
			"Alles gebaut, dann direkt raus an euch.",
		],
		"EMOTION": [
			"Diese Episode hat mich mehr gepackt als gedacht.",
			"Kurzer Herzklopfen-Moment beim Upload.",
			"So viel Liebe in diesem kleinen Release.",
		],
		"THOUGHT": [
			"Wenn dich eine Idee nicht loslässt, teile sie.",
			"Das Beste passiert, wenn man drückt: Publish.",
			"Storytelling ist mein Lieblingssport.",
		],
	}
	suggestions: List[Dict] = []
	for cat in PERSONAL_LINE_CATEGORIES:
		for line in templates[cat]:
			if line not in last_used:
				suggestions.append({"category": cat, "text": line})
	offset = len(last_used) % len(suggestions) if suggestions else 0
	return suggestions[offset:offset + 5] if suggestions else []


def generate_x_post(title: str, website_url: str, hashtags: List[str]) -> Dict:
	tag_str = " " + " ".join(hashtags[:2]) if hashtags else ""
	text = f"{title} — live jetzt {website_url}{tag_str}"
	return {"text": text.strip()}


def generate_threads_text(ig_caption: str, website_url: Optional[str], mode: str) -> str:
	if mode == "ADD_LINK" and website_url:
		return f"{ig_caption}\n\nMehr dazu: {website_url}"
	return ig_caption


def generate_reel_spec(key_visual_asset_id: str, title: str, audio_choice: str, duration: int) -> Dict:
	overlays = ["Neue Episode", title, "Link in Bio"]
	return {
		"template": "IG_REEL_KEN_BURNS",
		"asset_id": key_visual_asset_id,
		"audio_choice": audio_choice or "preset_default",
		"duration_seconds": duration,
		"overlays": overlays,
	}


def asset_gate(event: Dict) -> List[str]:
	missing: List[str] = []
	if not event.get("validation") or not event["validation"].get("ok"):
		missing.append("Website URL validiert")
	if not event.get("key_visual_asset_id"):
		missing.append("Key Visual (Feed)")
	seq = None
	for s in st.session_state["story_sequences"]:
		if s["release_event_id"] == event["id"]:
			seq = s
			break
	slides = [sl for sl in st.session_state["story_slides"] if seq and sl["sequence_id"] == seq["id"]]
	if not seq or not slides:
		missing.append("Story Sequence (3 Slides)")
	else:
		link_ok = any(sl.get("link_url") for sl in slides if sl.get("slide_index") in {1, 2})
		if not link_ok:
			missing.append("Link-Sticker auf Slide 1 oder 2")
		if not any(sl.get("media_asset_id") for sl in slides if sl.get("slide_index") == 1):
			missing.append("Story Slide 1 Card Asset")
		if not any(sl.get("media_asset_id") for sl in slides if sl.get("slide_index") == 2):
			missing.append("Story Slide 2 Snippet Asset")
		if not any(sl.get("media_asset_id") for sl in slides if sl.get("slide_index") == 3):
			missing.append("Story Slide 3 Personal GIF")
	x_item = next((c for c in st.session_state["content_items"] if c["release_event_id"] == event["id"] and c["channel"] == "X"), None)
	if not x_item or not x_item.get("media_asset_ids"):
		missing.append("X GIF")
	return missing


def mark_posted(content_item: Dict, post_url: Optional[str]) -> None:
	content_item["status"] = "POSTED"
	content_item["posted_at"] = dt.datetime.now()
	content_item["post_url"] = post_url or content_item.get("post_url")


def timeline_suggestion(base_time: Optional[dt.datetime]) -> List[Dict]:
	base = base_time or dt.datetime.now()
	return [
		{"channel": "Website live", "scheduled_for": base},
		{"channel": "IG Feed", "scheduled_for": base},
		{"channel": "IG Story", "scheduled_for": base},
		{"channel": "X", "scheduled_for": base},
		{"channel": "Threads", "scheduled_for": base},
		{"channel": "IG Reel (optional)", "scheduled_for": base + dt.timedelta(hours=6)},
	]


def build_calendar_entries(include_suggestions: bool = True) -> List[Dict]:
	entries: List[Dict] = []
	for ev in st.session_state["release_events"]:
		when = ev.get("release_datetime")
		if when:
			entries.append({
				"when": when,
				"what": f"Release {ev['title']}",
				"kind": "ReleaseEvent",
				"ref": ev["id"],
			})
			if include_suggestions:
				for s in timeline_suggestion(when):
					entries.append({
						"when": s["scheduled_for"],
						"what": f"{s['channel']} (Vorschlag) — {ev['title']}",
						"kind": "Suggested",
						"ref": ev["id"],
					})
	for item in st.session_state["content_items"]:
		if item.get("posted_at"):
			entries.append({
				"when": item["posted_at"],
				"what": f"Posted {item['channel']}",
				"kind": "Posted",
				"ref": item["id"],
			})
	entries.sort(key=lambda e: e["when"])
	return entries


def group_entries_by_day(entries: List[Dict]) -> Dict[str, List[Dict]]:
	grouped: Dict[str, List[Dict]] = {}
	for e in entries:
		key = e["when"].strftime("%Y-%m-%d")
		grouped.setdefault(key, []).append(e)
	return grouped


init_state()
load_state()
st.title("📡 ΔNET Content Hub")

st.caption("Usecases UC-01 bis UC-11 als kompakte Workflow-UI. Session State = Speicher.")

with st.expander("UC-01 Release Event anlegen (GENERIC)", expanded=True):
	col1, col2, col3 = st.columns(3)
	with col1:
		release_type = st.selectbox("Release Type", RELEASE_TYPES, index=0)
		title = st.text_input("Title", placeholder="Episode 04 Release")
		website_url = st.text_input("Website URL (optional)", placeholder="https://example.com/episode-04")
	with col2:
		episode_id = st.text_input("Episode ID (nur wenn erlaubt)", placeholder="episode-04")
		release_datetime = st.datetime_input("Release Datetime (optional)", value=None)
		key_visual_asset_id = st.text_input("Key Visual Asset ID (optional)")
	with col3:
		include_reel = st.checkbox("Optional Reel vorplanen", value=True)
		create_btn = st.button("Create Release Event", type="primary")
		created_event = None
		if create_btn:
			errors = []
			if not title:
				errors.append("Title ist Pflicht.")
			# Rule engine for episode_id
			if release_type == "EPISODE" and not episode_id:
				errors.append("Episode ID ist Pflicht für EPISODE.")
			if release_type in {"WORLD_DROP", "SPORT_EVENT", "ANNOUNCEMENT"} and episode_id:
				errors.append("Episode ID muss leer sein für diesen Release Type.")
			if errors:
				st.error("; ".join(errors))
			else:
				stored_episode_id = episode_id or None
				created_event = create_release_event(
					release_type=release_type,
					title=title,
					website_url=website_url or None,
					episode_id=stored_episode_id,
					release_datetime=release_datetime,
					key_visual_asset_id=key_visual_asset_id or None,
					include_reel=include_reel,
				)
				st.success(f"ReleaseEvent {created_event['id']} erstellt + Pipeline auf DRAFT gesetzt.")
				with st.expander("Debug: ReleaseEvent JSON", expanded=False):
					st.json({"ReleaseEvent": created_event})
				save_state()

st.divider()

if not st.session_state["release_events"]:
	st.info("Noch keine Release Events angelegt.")
	st.stop()

event_ids = [f"{ev['id']} — {ev['title']}" for ev in st.session_state["release_events"]]
selected_label = st.selectbox("Arbeits-Release", options=event_ids)
current_event = next(ev for ev in st.session_state["release_events"] if selected_label.startswith(ev["id"]))
st.write(f"Aktueller Status: {current_event['status']}")

with st.expander("UC-02 Website validieren & Status setzen", expanded=False):
	do_head = st.checkbox("HTTP HEAD ausfuehren", value=False)
	if st.button("Validate Website", key="validate"):
		validation = validate_website_url(current_event["website_url"], perform_network=do_head)
		current_event["validation"] = validation
		if validation["ok"]:
			st.success("Website Validation OK")
		else:
			st.error("Validation Errors")
			st.write(validation["errors"])
		save_state()
	if current_event.get("validation"):
		with st.expander("Debug: Validation JSON", expanded=False):
			st.json(current_event["validation"])

with st.expander("UC-03 IG Feed Copy", expanded=False):
	one_liner = st.text_input("One-Liner (optional)")
	tone_profile = st.text_input("Tone Profile (optional)")
	hashtag_set_id = st.selectbox("Hashtag Set", ["default", "calm", "custom"], index=0)
	if st.button("Generate IG Feed Copy"):
		hashtags = default_hashtags(hashtag_set_id) if hashtag_set_id != "custom" else []
		result = generate_ig_caption(current_event["title"], one_liner, current_event["website_url"], tone_profile, hashtag_set_id)
		item = upsert_content_item(current_event["id"], "IG_FEED")
		item["caption_text"] = result["caption"]
		item["hashtags"] = hashtags[:5] if hashtags else result["hashtags"]
		item["status"] = "READY_FOR_REVIEW"
		st.success("IG Feed Copy generiert und Item auf READY_FOR_REVIEW gesetzt.")
		st.text_area("Caption", value=item["caption_text"], height=120)
		st.write({"hashtags": item["hashtags"]})
		save_state()

with st.expander("UC-04 IG Story Sequence (3 Slides)", expanded=False):
	seq = ensure_story_sequence(current_event["id"])
	key_visual = st.text_input("Key Visual Asset ID", value=current_event.get("key_visual_asset_id", ""))
	snippet_asset = st.text_input("Snippet Asset ID")
	personal_gif = st.text_input("Personal GIF Asset ID")
	overlay_snippet = st.text_input("Snippet Overlay (optional)")
	slide3_text = st.text_input("Slide 3 Text (Personal)")
	link_url = st.text_input("Link Sticker URL", value=current_event.get("website_url", ""))
	if st.button("Create IG Story Sequence"):
		if not link_url:
			st.error("Link Sticker ist Pflicht auf Slide 1 oder 2.")
		else:
			slides = [
				{"slide_index": 1, "template_id": "ANNOUNCE", "media_asset_id": key_visual, "overlay_text": f"Neue Episode online: {current_event['title']}", "link_url": link_url},
				{"slide_index": 2, "template_id": "SNIPPET", "media_asset_id": snippet_asset, "overlay_text": overlay_snippet, "link_url": link_url},
				{"slide_index": 3, "template_id": "PERSONAL", "media_asset_id": personal_gif, "overlay_text": slide3_text, "link_url": None},
			]
			set_story_slides(seq["id"], slides)
			story_item = upsert_content_item(current_event["id"], "IG_STORY")
			story_item["status"] = "READY_FOR_REVIEW"
			st.success("Story Sequence gespeichert (Render-Spec 1080x1920).")
			save_state()
	st.dataframe([s for s in st.session_state["story_slides"] if s["sequence_id"] == seq["id"]])

with st.expander("UC-05 Slide 3 Personal Lines", expanded=False):
	last_used = st.session_state["personal_line_history"]
	if st.button("Suggest Slide 3 Lines"):
		suggestions = generate_personal_lines(last_used)
		if not suggestions:
			st.info("Keine neuen Vorschlaege verfuegbar.")
		else:
			st.table(suggestions)
			choice = st.selectbox("Zeile uebernehmen?", options=[s["text"] for s in suggestions])
			if st.button("Use Selected Line"):
				st.session_state["personal_line_history"].append(choice)
				seq_id = ensure_story_sequence(current_event["id"])["id"]
				slides = [s for s in st.session_state["story_slides"] if s["sequence_id"] == seq_id]
				for sl in slides:
					if sl["slide_index"] == 3:
						sl["overlay_text"] = choice
				st.success("Slide 3 Text aktualisiert.")
				save_state()

with st.expander("UC-06 X Post", expanded=False):
	gif_asset = st.text_input("X GIF Asset ID")
	add_hashtags = st.text_input("Hashtags (max 2, comma)", value="")
	if st.button("Generate X Post"):
		tags = [h.strip() for h in add_hashtags.split(",") if h.strip()][:2]
		result = generate_x_post(current_event["title"], current_event["website_url"], tags)
		item = upsert_content_item(current_event["id"], "X")
		item["caption_text"] = result["text"]
		if gif_asset:
			item["media_asset_ids"] = [gif_asset]
		item["status"] = "READY_FOR_REVIEW"
		st.success("X Post vorbereitet.")
		st.text_area("X Copy", value=item["caption_text"], height=100)
		save_state()

with st.expander("UC-07 Threads Post", expanded=False):
	threads_mode = st.selectbox("Threads Mode", ["REPOST", "ADD_LINK"], index=0)
	if st.button("Create Threads from IG"):
		ig_item = upsert_content_item(current_event["id"], "IG_FEED")
		threads_text = generate_threads_text(ig_item.get("caption_text", ""), current_event.get("website_url"), threads_mode)
		item = upsert_content_item(current_event["id"], "THREADS")
		item["caption_text"] = threads_text
		item["status"] = "READY_FOR_REVIEW"
		st.success("Threads Copy gesetzt.")
		st.text_area("Threads Text", value=item["caption_text"], height=100)
		save_state()

with st.expander("UC-08 Optional Reel", expanded=False):
	audio_choice = st.text_input("Audio Choice (optional)")
	duration = st.slider("Duration seconds", min_value=6, max_value=12, value=8)
	if st.button("Generate Reel Job"):
		if not current_event.get("key_visual_asset_id"):
			st.error("Key Visual Asset ID fehlt.")
		else:
			spec = generate_reel_spec(current_event["key_visual_asset_id"], current_event["title"], audio_choice, duration)
			item = upsert_content_item(current_event["id"], "IG_REEL")
			item["render_spec"] = spec
			item["status"] = "READY_FOR_RENDER"
			st.success("Reel Render Spec erzeugt.")
			with st.expander("Debug: Reel Spec JSON", expanded=False):
				st.json(spec)
			save_state()

with st.expander("UC-09 Asset Checklist (Gating)", expanded=False):
	if st.button("Run Asset Gate"):
		missing = asset_gate(current_event)
		if missing:
			st.error("Fehlende Assets")
			st.write(missing)
		else:
			current_event["status"] = "READY"
			st.success("Alle Assets vorhanden. Release auf READY.")
		save_state()

with st.expander("UC-10 Posting Tracker", expanded=False):
	items = [c for c in st.session_state["content_items"] if c["release_event_id"] == current_event["id"]]
	for item in items:
		col_a, col_b, col_c = st.columns([2, 2, 1])
		with col_a:
			st.markdown(f"**{item['channel']}** — Status: {item['status']}")
			post_url = st.text_input(f"Post URL {item['channel']}", value=item.get("post_url") or "", key=f"url_{item['id']}")
		with col_b:
			st.text_area(f"Caption {item['channel']}", value=item.get("caption_text", ""), height=80, key=f"cap_{item['id']}")
		with col_c:
			if st.button("Mark as Posted", key=f"posted_{item['id']}"):
				mark_posted(item, post_url)
				st.success(f"{item['channel']} als POSTED markiert.")
				save_state()

with st.expander("UC-11 Release Timeline Suggestion", expanded=False):
	tz_info = "Europe/Berlin"
	base_time = current_event.get("release_datetime")
	suggested = timeline_suggestion(base_time)
	st.write(f"Zeitzone: {tz_info}")
	st.table([
		{"channel": s["channel"], "scheduled_for": s["scheduled_for"].strftime("%Y-%m-%d %H:%M")} for s in suggested
	])

st.divider()

tab_overview, tab_calendar = st.tabs(["Overview", "Kalender"])

with tab_overview:
	st.subheader("Release Events Overview")
	st.dataframe([
		{
			"id": ev["id"],
			"type": ev.get("type"),
			"episode_id": ev.get("episode_id"),
			"title": ev["title"],
			"status": ev["status"],
			"website_url": ev["website_url"],
			"release_datetime": ev["release_datetime"].strftime("%Y-%m-%d %H:%M") if ev.get("release_datetime") else "-",
		}
		for ev in st.session_state["release_events"]
	])

	st.subheader("Content Items Overview")
	st.dataframe([
		{
			"id": c["id"],
			"release_event_id": c["release_event_id"],
			"channel": c["channel"],
			"status": c["status"],
			"post_url": c.get("post_url"),
			"posted_at": c.get("posted_at").strftime("%Y-%m-%d %H:%M") if c.get("posted_at") else None,
		}
		for c in st.session_state["content_items"]
	])

with tab_calendar:
	st.subheader("Kalender")
	entries = build_calendar_entries(include_suggestions=True)
	if not entries:
		st.info("Keine datierten Einträge (Release-Datetime oder Posted-At) vorhanden.")
	else:
		view = st.radio("Ansicht", ["Liste", "Tages-Kalender"], horizontal=True)
		if view == "Liste":
			st.dataframe([
				{
					"when": e["when"].strftime("%Y-%m-%d %H:%M"),
					"what": e["what"],
					"kind": e["kind"],
					"ref": e["ref"],
				}
				for e in entries
			])
		else:
			grouped = group_entries_by_day(entries)
			for day, day_entries in grouped.items():
				with st.container(border=True):
					st.markdown(f"**{day}**")
					for e in day_entries:
						st.write(f"{e['when'].strftime('%H:%M')} — {e['what']} ({e['kind']}) [{e['ref']}]")
