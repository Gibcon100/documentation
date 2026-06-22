#!/usr/bin/env python3
"""
Jarvis Einkaufsliste Scanner
Laueft auf dem Mac - liest Barcodes (direkt oder vom Raspberry Pi),
sucht den Produktnamen via Open Food Facts und traegt ihn in Apple Reminders ein.
"""

import sys
import json
import urllib.request
import subprocess
import signal
import http.server
import threading
import queue
import socket

# ── Konfiguration ──────────────────────────────────────────────────────────────
REMINDERS_LIST = "Einkaufsliste"
PI_SERVER_PORT  = 8765          # Port, auf dem der Mac auf den Raspberry Pi hoert
MODE            = "keyboard"    # "keyboard"  -> Scanner direkt am Mac (USB)
                                # "network"   -> Scanner am Raspberry Pi (HTTP)
# ──────────────────────────────────────────────────────────────────────────────


def lookup_product(barcode: str) -> str | None:
    """Produktname per Barcode via Open Food Facts ermitteln."""
    url = (
        f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        "?fields=product_name_de,product_name,brands"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis-Scanner/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == 1:
            p = data.get("product", {})
            name = p.get("product_name_de") or p.get("product_name") or p.get("brands", "")
            return name.strip() or None
    except Exception:
        pass
    return None


def add_to_reminders(item: str) -> tuple[bool, str]:
    """Eintrag in Apple Reminders (iCloud-Account) hinzufuegen.

    Nutzt osascript argv - kein String-Escaping noetig, funktioniert mit
    allen Sonderzeichen. Zielt explizit auf iCloud, nicht lokalen Account.
    """
    script = """
on run argv
    set itemName to item 1 of argv
    set listName to item 2 of argv
    tell application "Reminders"
        set targetAccount to missing value
        repeat with acc in accounts
            if name of acc contains "iCloud" then
                set targetAccount to acc
                exit repeat
            end if
        end repeat
        if targetAccount is missing value then
            if (count of accounts) > 0 then
                set targetAccount to first account
            else
                error "Kein Reminders-Account gefunden"
            end if
        end if
        if not (exists list listName of targetAccount) then
            make new list at targetAccount with properties {name:listName}
        end if
        make new reminder at end of list listName of targetAccount with properties {name:itemName}
        return name of targetAccount
    end tell
end run
"""
    result = subprocess.run(
        ["osascript", "-e", script, item, REMINDERS_LIST],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Reminders-Fehler: {result.stderr.strip() or 'Keine Berechtigung?'}")
        print(f"  -> Systemeinstellungen -> Datenschutz -> Automatisierung -> Terminal -> Reminders anhaken")
    return result.returncode == 0, result.stdout.strip()


def process_barcode(barcode: str, scanned: list) -> None:
    """Barcode nachschlagen und in Reminders eintragen."""
    barcode = barcode.strip()
    if not barcode:
        return

    print(f"  Suche: {barcode} ...", flush=True)
    name = lookup_product(barcode)

    if not name:
        print(f"  Nicht gefunden. Barcode: {barcode}")
        name = input("  Produktname eingeben (Enter = ueberspringen): ").strip()
        if not name:
            return

    ok, account = add_to_reminders(name)
    if ok:
        print(f"  OK: '{name}' -> Einkaufsliste  [Account: {account}]")
        scanned.append(name)
    else:
        print(f"  FEHLER beim Eintragen in Apple Reminders")


# ── Netzwerk-Modus: kleiner HTTP-Server empfaengt Barcodes vom Raspberry Pi ──

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

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Jarvis Scanner laeuft")

    def log_message(self, *_):
        pass


def run_network_mode(scanned: list) -> None:
    bq = queue.Queue()
    handler = lambda *a, **kw: _BarcodeHandler(bq, *a, **kw)
    server  = http.server.HTTPServer(("0.0.0.0", PI_SERVER_PORT), handler)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = subprocess.run(
            ["ipconfig", "getifaddr", "en0"], capture_output=True, text=True
        ).stdout.strip() or "DEINE_MAC_IP"

    print(f"  Mac-IP: {local_ip}  Port: {PI_SERVER_PORT}")
    print(f"  Pi sendet an: http://{local_ip}:{PI_SERVER_PORT}")
    print(f"  Beenden: Ctrl+C\n")

    try:
        while True:
            barcode = bq.get()
            process_barcode(barcode, scanned)
    except KeyboardInterrupt:
        server.shutdown()


def run_keyboard_mode(scanned: list) -> None:
    print("  Scanner anschliessen und Barcode scannen.")
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
    print("\n\nScanner beendet.")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 52)
    print("  Jarvis Barcode Scanner")
    print("=" * 52)
    print(f"  Modus : {'Tastatur (direkt)' if MODE == 'keyboard' else 'Netzwerk (Raspberry Pi)'}")
    print(f"  Ziel  : Apple Reminders -> '{REMINDERS_LIST}'")
    print()

    scanned: list = []

    if MODE == "network":
        run_network_mode(scanned)
    else:
        run_keyboard_mode(scanned)

    if scanned:
        print(f"\nHeute gescannt ({len(scanned)} Artikel):")
        for item in scanned:
            print(f"   * {item}")
    print()


if __name__ == "__main__":
    main()
