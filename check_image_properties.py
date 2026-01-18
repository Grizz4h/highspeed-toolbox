from PIL import Image

def check_image(path):
    img = Image.open(path)
    print(f"Datei: {path}")
    print(f"Format: {img.format}")
    print(f"Größe (Pixel): {img.size}")
    print(f"Modus (Farbraum): {img.mode}")
    print(f"Info: {img.info}")

    # Prüfe auf Transparenz
    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        print("Transparenz: Ja")
    else:
        print("Transparenz: Nein")

    # DPI auslesen (falls vorhanden)
    dpi = img.info.get("dpi")
    if dpi:
        print(f"DPI: {dpi}")
    else:
        print("DPI: Nicht gesetzt")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python check_image_properties.py <image.png>")
    else:
        check_image(sys.argv[1])
