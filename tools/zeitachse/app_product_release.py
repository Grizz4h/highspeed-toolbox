import streamlit as st
import json
from datetime import date, timedelta
from pathlib import Path

from .canon_time import load_config as load_canon_config
from .product_releases_store import (
    load_releases, save_releases, add_release, delete_release, releases_by_brand
)

BASE_DIR = Path(__file__).resolve().parent
BRANDS_CONFIG_PATH = BASE_DIR / "product_brands_config.json"
CANON_CONFIG_PATH = BASE_DIR / "canon_time_config.json"


# -------------------------
# Helpers
# -------------------------
def load_brands_config(path: Path):
    """Laden der Marken-Konfiguration"""
    if not path.exists():
        raise FileNotFoundError(f"Brands config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_brand_by_id(brands_config, brand_id: str):
    """Findet eine Marke nach ID"""
    for brand_type in brands_config["brands"].values():
        for brand in brand_type:
            if brand["id"] == brand_id:
                return brand
    return None


def validate_release_date(brand: dict, release_date: date) -> tuple[bool, str]:
    """
    Validiert, dass das Release-Datum nicht vor dem Gründungsdatum liegt.
    Gibt (is_valid, message) zurück
    """
    founding = date.fromisoformat(brand["founding_date"])
    if release_date < founding:
        return False, f"Release-Datum {release_date.isoformat()} liegt vor Gründungsdatum {founding.isoformat()}"
    return True, "OK"


# -------------------------
# RENDER ENTRYPOINT
# -------------------------
def render():
    st.title("🏭 Produkt Release Manager")
    st.caption("Breeder Strains & Bike Marken Releases mit Canon-Zeit Validierung")

    # -------------------------
    # Load configs
    # -------------------------
    try:
        brands_config = load_brands_config(BRANDS_CONFIG_PATH)
        canon_config = load_canon_config(CANON_CONFIG_PATH)
    except Exception as e:
        st.error(f"Config konnte nicht geladen werden: {e}")
        st.stop()

    # -------------------------
    # Load releases
    # -------------------------
    if "product_releases" not in st.session_state:
        st.session_state["product_releases"] = load_releases()
    
    releases = st.session_state["product_releases"]

    # -------------------------
    # Sidebar: Verwaltung
    # -------------------------
    with st.sidebar:
        st.subheader("💾 Verwaltung")
        if st.button("💾 Releases speichern", key="btn_save_releases"):
            save_releases(releases)
            st.success("Releases gespeichert.")
        st.caption("Releases liegen in `product_releases.json`.")

    # -------------------------
    # Tabs für verschiedene Ansichten
    # -------------------------
    tab_katalog, tab_releases, tab_verwaltung = st.tabs(["📚 Produkt-Katalog", "📅 Release-Planung", "⚙️ Verwaltung"])

    with tab_katalog:
        render_product_catalog(releases, brands_config)

    with tab_releases:
        render_release_planner(releases, brands_config, canon_config)

    with tab_verwaltung:
        render_brand_management(brands_config, releases)


# -------------------------
# KATALOG-ANSICHT
# -------------------------
def render_product_catalog(releases, brands_config):
    st.header("📚 Produkt-Katalog")
    st.caption("Alle verfügbaren Produkte nach Marken geordnet")

    # Such- und Filter-Optionen
    col_search, col_filter_type, col_filter_brand = st.columns([2, 1, 1])
    
    with col_search:
        search_term = st.text_input("🔍 Suche nach Produkt", placeholder="Produktname eingeben...")
    
    with col_filter_type:
        type_filter = st.selectbox("Typ filtern", ["Alle"] + list(brands_config["brands"].keys()))
    
    with col_filter_brand:
        # Alle Marken sammeln
        all_brands = []
        for brand_type, brands in brands_config["brands"].items():
            if type_filter == "Alle" or type_filter == brand_type:
                all_brands.extend([(b["id"], b["name"], brand_type) for b in brands])
        
        brand_options = ["Alle"] + [f"{name} ({typ})" for _, name, typ in all_brands]
        brand_filter = st.selectbox("Marke filtern", brand_options)

    # Releases filtern
    filtered_releases = releases.copy()
    
    if search_term:
        filtered_releases = [r for r in filtered_releases if search_term.lower() in r.product_name.lower()]
    
    if type_filter != "Alle":
        filtered_releases = [r for r in filtered_releases if get_brand_by_id(brands_config, r.brand_id)["type"] == type_filter]
    
    if brand_filter != "Alle":
        selected_brand_name = brand_filter.split(" (")[0]
        filtered_releases = [r for r in filtered_releases if r.brand_name == selected_brand_name]

    # Nach Marken gruppieren
    releases_by_brand_grouped = {}
    for rel in filtered_releases:
        brand_key = rel.brand_name
        if brand_key not in releases_by_brand_grouped:
            releases_by_brand_grouped[brand_key] = []
        releases_by_brand_grouped[brand_key].append(rel)

    # Anzeige
    if not filtered_releases:
        st.info("Keine Produkte gefunden.")
    else:
        st.success(f"📦 {len(filtered_releases)} Produkte gefunden")
        
        # Marken durchgehen
        for brand_name, brand_releases in sorted(releases_by_brand_grouped.items()):
            brand_info = None
            for brand_type in brands_config["brands"].values():
                for b in brand_type:
                    if b["name"] == brand_name:
                        brand_info = b
                        break
                if brand_info:
                    break
            
            if not brand_info:
                continue
                
            with st.expander(f"🏷️ {brand_name} ({brand_info['type'].upper()}) - {len(brand_releases)} Produkte", expanded=True):
                # Marken-Info
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("Gründung", date.fromisoformat(brand_info["founding_date"]).strftime("%d.%m.%Y"))
                with col_info2:
                    st.metric("Typ", brand_info["type"].title())
                with col_info3:
                    if "specialization" in brand_info:
                        st.metric("Spezialisierung", brand_info["specialization"])
                
                # Produkte als Karten
                cols = st.columns(3)
                for i, rel in enumerate(sorted(brand_releases, key=lambda r: r.release_date)):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.subheader(f"🌱 {rel.product_name}")
                            st.caption(f"**{rel.product_type.upper()}**")
                            st.write(f"📅 Release: {rel.release_date}")
                            if rel.notes:
                                st.text(f"📝 {rel.notes[:100]}{'...' if len(rel.notes) > 100 else ''}")


# -------------------------
# RELEASE-PLANER
# -------------------------
def render_release_planner(releases, brands_config, canon_config):
    st.header("📅 Release-Planung")
    st.caption("Neue Produkte planen und vorhandene verwalten")

    # -------------------------
    # Release hinzufügen
    # -------------------------
    st.subheader("➕ Neuen Product Release erstellen")

    # Marke auswählen
    brand_type = st.selectbox("Markentyp", ["breeder", "bike"], key="brand_type_select")
    
    brands_of_type = brands_config["brands"][brand_type]
    brand_names = {b["id"]: b["name"] for b in brands_of_type}
    brand_options = list(brand_names.keys())
    
    if not brand_options:
        st.warning(f"Keine {brand_type} Marken konfiguriert.")
    else:
        selected_brand_id = st.selectbox(
            "Marke wählen",
            options=brand_options,
            format_func=lambda x: brand_names[x]
        )
        
        selected_brand = get_brand_by_id(brands_config, selected_brand_id)
        founding_date = date.fromisoformat(selected_brand["founding_date"])
        st.info(f"Gründungsdatum: **{founding_date.isoformat()}** ({founding_date.strftime('%A')})")
        
        # Spezialisierung anzeigen
        if "specialization" in selected_brand:
            st.caption(f"🎯 Spezialisierung: {selected_brand['specialization']}")

        # Produkttyp - gefiltert nach Marken-Spezialisierung
        all_product_types = brands_config["product_types"][brand_type]
        allowed_types = selected_brand.get("allowed_product_types", all_product_types)
        
        # Nur erlaubte Typen zeigen
        available_types = [t for t in all_product_types if t in allowed_types]
        
        if not available_types:
            st.error(f"❌ Keine erlaubten Produkttypen für diese Marke konfiguriert.")
            st.stop()
        
        product_type = st.selectbox("Produkttyp", available_types)

        # Produktname mit Vorschlägen
        suggested_products = brands_config.get("product_suggestions", {}).get(brand_type, {}).get(selected_brand_id, [])
        
        col_prod1, col_prod2 = st.columns([2, 1])
        with col_prod1:
            product_name = st.text_input("Produktname")
        
        if suggested_products:
            with col_prod2:
                st.caption("💡 Übliche Produkte:")
                for prod in suggested_products[:2]:
                    if st.button(prod, key=f"suggest_{prod}", use_container_width=True):
                        st.session_state["_suggested_product"] = prod
                        st.rerun()
        
        if "_suggested_product" in st.session_state:
            product_name = st.session_state["_suggested_product"]
            del st.session_state["_suggested_product"]

        # Release-Datum
        min_offset, max_offset = brands_config["release_offset_rules"].get(product_type, [-7, 0])
        
        st.write(f"**Offset-Regel für '{product_type}'**: [{min_offset}, {max_offset}] Tage")
        
        default_release = founding_date + timedelta(days=0)
        release_date = st.date_input("Release-Datum", value=default_release, min_value=founding_date)

        # Notes
        release_notes = st.text_area("Notizen", height=60)

        if st.button("✅ Release erstellen", key="btn_create_release"):
            if not product_name.strip():
                st.error("Produktname fehlt.")
            else:
                # Validierung: Nicht vor Gründungsdatum
                is_valid, msg = validate_release_date(selected_brand, release_date)
                
                if not is_valid:
                    st.error(f"❌ {msg}")
                else:
                    add_release(
                        releases,
                        release_date=release_date,
                        brand_id=selected_brand_id,
                        brand_name=selected_brand["name"],
                        product_type=product_type,
                        product_name=product_name,
 notes=release_notes,
                    )
                    save_releases(releases)
                    st.success(f"✅ {selected_brand['name']} – {product_name} für {release_date.isoformat()} geplant.")
                    st.rerun()

    st.divider()

    # -------------------------
    # Releases verwalten
    # -------------------------
    st.subheader("📋 Release-Verwaltung")

    if not releases:
        st.info("Noch keine Releases geplant.")
    else:
        # Sortiert nach Datum
        sorted_releases = sorted(releases, key=lambda r: r.release_date)
        
        for rel in sorted_releases:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{rel.brand_name}** – {rel.product_name}")
                    st.caption(f"{rel.product_type.upper()} | {rel.release_date}")
                    if rel.notes:
                        st.text(f"📝 {rel.notes}")
                
                with col2:
                    if st.button("🗑️", key=f"del_{rel.id}", use_container_width=True):
                        delete_release(releases, rel.id)
                        save_releases(releases)
                        st.rerun()


# -------------------------
# MARKEN-VERWALTUNG
# -------------------------
def render_brand_management(brands_config, releases):
    st.header("⚙️ Marken-Verwaltung")
    st.caption("Breeder und Bike-Marken konfigurieren")

    # -------------------------
    # Neue Marke hinzufügen
    # -------------------------
    st.subheader("➕ Neue Marke hinzufügen")
    with st.expander("Marke hinzufügen", expanded=False):
        new_brand_name = st.text_input("Markenname")
        new_brand_type = st.selectbox("Typ", ["breeder", "bike"])
        new_founding_date = st.date_input("Gründungsdatum")

        if st.button("✅ Marke speichern", key="btn_save_brand"):
            if not new_brand_name.strip():
                st.error("Markenname fehlt.")
            else:
                # In config speichern
                brand_id = new_brand_name.lower().replace(" ", "_")
                new_brand_obj = {
                    "id": brand_id,
                    "name": new_brand_name,
                    "founding_date": new_founding_date.isoformat(),
                    "type": new_brand_type
                }
                brands_config["brands"][new_brand_type].append(new_brand_obj)
                BRANDS_CONFIG_PATH.write_text(json.dumps(brands_config, indent=2, ensure_ascii=False), encoding="utf-8")
                st.success(f"Marke '{new_brand_name}' hinzugefügt.")
                st.rerun()

    st.divider()

    # -------------------------
    # Bestehende Marken anzeigen
    # -------------------------
    st.subheader("📋 Bestehende Marken")

    for brand_type, brands in brands_config["brands"].items():
        st.subheader(f"🏷️ {brand_type.title()} Marken")
        
        if not brands:
            st.info(f"Keine {brand_type} Marken konfiguriert.")
        else:
            for brand in brands:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**{brand['name']}**")
                        st.caption(f"ID: {brand['id']}")
                    
                    with col2:
                        founding = date.fromisoformat(brand["founding_date"])
                        st.write(f"📅 {founding.strftime('%d.%m.%Y')}")
                        if "specialization" in brand:
                            st.caption(f"🎯 {brand['specialization']}")
                    
                    with col3:
                        st.metric("Produkte", len([r for r in releases if r.brand_id == brand["id"]]))


# Standalone run
if __name__ == "__main__":
    st.set_page_config(page_title="Produkt Release Manager", layout="wide")
    render()
