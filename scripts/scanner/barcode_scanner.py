#!/usr/bin/env python3
"""
Jarvis Einkaufsliste Scanner
Läuft auf dem Mac – liest Barcodes (direkt oder vom Raspberry Pi),
sucht den Produktnamen via Open Food Facts und trägt ihn in Apple Reminders ein.
"""

import sys
import json
import urllib.request
import subprocess
import signal
import http.server
import threading
import queue
import os

# ── Konfiguration ──────────────────────────────────────────────────────────────
REMINDERS_LIST = "Einkaufsliste"
PI_SERVER_PORT  = 8765          # Port, auf dem der Mac auf den Raspberry Pi hört
MODE            = "keyboard"    # "keyboard"  → Scanner direkt am Mac (USB)
                                # "network"   → Scanner am Raspberry Pi (HTTP)
# ──────────────────────────────────────────────────────────────────────────────


def lookup_product(barcode: str) -> str | None:
    """Produktname per Barcode via Open Food Facts ermitteln."""
    url = (
        f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        "?fields=product_name_de,product_name,brands"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis-Scanner/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == 1:
            p = data.get("product", {})
            name = p.get("product_name_de") or p.get("product_name") or p.get("brands", "")
            return name.strip() or None
    except Exception:
        pass
    return None


def add_to_reminders(item: str) -> bool:
    """Eintrag in Apple Reminders (Liste 'Einkaufsliste') hinzufügen."""
    script = f"""
tell application "Reminders"
    if not (exists list "{REMINDERS_LIST}") then
        make new list with properties {{name:"{REMINDERS_LIST}"}}
    end if
    make new reminder at end of list "{REMINDERS_LIST}" with properties {{name:"{item}"}}
end tell
"""
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.returncode == 0


def process_barcode(barcode: str, scanned: list) -> None:
    """Barcode nachschlagen und in Reminders eintragen."""
    barcode = barcode.strip()
    if not barcode:
        return

    print(f"  🔍 {barcode} → suche Produkt …", flush=True)
    name = lookup_product(barcode)

    if not name:
        print(f"  ⚠️  Nicht gefunden. Barcode: {barcode}")
        name = input("  Produktname eingeben (Enter = überspringen): ").strip()
        if not name:
            return

    if add_to_reminders(name):
        print(f"  ✅ '{name}' → Einkaufsliste")
        scanned.append(name)
    else:
        print(f"  ❌ Fehler beim Eintragen in Apple Reminders")


# ── Netzwerk-Modus: kleiner HTTP-Server empfängt Barcodes vom Raspberry Pi ──

class _BarcodeHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, bq, *args, **kwargs):
        self._queue = bq
        super().__init__(*args, **kwargs)

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length).decode().strip()
        self._queue.put(payload)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *_):
        pass  # kein Server-Log im Terminal


def run_network_mode(scanned: list) -> None:
    bq = queue.Queue()
    handler = lambda *a, **kw: _BarcodeHandler(bq, *a, **kw)
    server  = http.server.HTTPServer(("0.0.0.0", PI_SERVER_PORT), handler)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    local_ip = subprocess.run(
        ["ipconfig", "getifaddr", "en0"], capture_output=True, text=True
    ).stdout.strip() or "DEINE_MAC_IP"

    print(f"  📡 Warte auf Raspberry Pi → http://{local_ip}:{PI_SERVER_PORT}")
    print(f"  Beenden: Ctrl+C\n")

    try:
        while True:
            barcode = bq.get()
            process_barcode(barcode, scanned)
    except KeyboardInterrupt:
        server.shutdown()


def run_keyboard_mode(scanned: list) -> None:
    print("  Scanner anschließen und Barcode scannen.")
    print("  Alternativ: Barcode eintippen + Enter")
    print("  Beenden: Ctrl+C\n")

    while True:
        try:
            barcode = input("  Barcode: ")
        except (EOFError, KeyboardInterrupt):
            break
        process_barcode(barcode, scanned)


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def signal_handler(sig, frame):
    print("\n\n✅ Scanner beendet.")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 52)
    print("  🛒 Jarvis Barcode Scanner")
    print("=" * 52)
    print(f"  Modus : {'Tastatur (direkt)' if MODE == 'keyboard' else 'Netzwerk (Raspberry Pi)'}")
    print(f"  Ziel  : Apple Reminders → '{REMINDERS_LIST}'")
    print()

    scanned: list = []

    if MODE == "network":
        run_network_mode(scanned)
    else:
        run_keyboard_mode(scanned)

    if scanned:
        print(f"\n📋 Heute gescannt ({len(scanned)} Artikel):")
        for item in scanned:
            print(f"   • {item}")
    print()


if __name__ == "__main__":
    main()
