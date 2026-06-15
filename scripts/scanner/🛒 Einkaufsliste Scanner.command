#!/bin/bash
# Jarvis Barcode Scanner - Desktop Button
# Selbst-installierend: schreibt barcode_scanner.py und startet es sofort.

SCRIPT_PATH="/Users/peterkrantz/Scripts/barcode_scanner.py"
mkdir -p /Users/peterkrantz/Scripts

# Python-Script in die richtige Position schreiben
cat > "$SCRIPT_PATH" << 'PYTHON_END'
#!/usr/bin/env python3
"""Jarvis Einkaufsliste Scanner – Barcode → Open Food Facts → Apple Reminders"""

import sys, json, urllib.request, subprocess, signal, http.server, threading, queue

REMINDERS_LIST = "Einkaufsliste"
PI_SERVER_PORT  = 8765
MODE            = "keyboard"   # "keyboard" = Scanner direkt am Mac
                               # "network"  = Scanner am Raspberry Pi

def lookup_product(barcode):
    url = ("https://world.openfoodfacts.org/api/v2/product/" + barcode +
           ".json?fields=product_name_de,product_name,brands")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis-Scanner/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read().decode())
        if d.get("status") == 1:
            p = d.get("product", {})
            n = p.get("product_name_de") or p.get("product_name") or p.get("brands","")
            return n.strip() or None
    except Exception:
        pass
    return None

def add_to_reminders(item):
    scpt = """
tell application "Reminders"
    if not (exists list "LISTE") then
        make new list with properties {name:"LISTE"}
    end if
    make new reminder at end of list "LISTE" with properties {name:"ARTIKEL"}
end tell
""".replace("LISTE", REMINDERS_LIST).replace("ARTIKEL", item.replace('"', '\\"'))
    return subprocess.run(["osascript", "-e", scpt], capture_output=True).returncode == 0

def process(barcode, scanned):
    barcode = barcode.strip()
    if not barcode:
        return
    print(f"  Suche: {barcode} ...", flush=True)
    name = lookup_product(barcode)
    if not name:
        print(f"  Nicht gefunden (Barcode: {barcode})")
        name = input("  Name eingeben (Enter = ueberspringen): ").strip()
        if not name:
            return
    if add_to_reminders(name):
        print(f"  OK: '{name}' -> Einkaufsliste")
        scanned.append(name)
    else:
        print(f"  FEHLER: Reminders nicht erreichbar")

class Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, q, *a, **kw):
        self._q = q; super().__init__(*a, **kw)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self._q.put(self.rfile.read(n).decode().strip())
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *_): pass

def run_network(scanned):
    q = queue.Queue()
    srv = http.server.HTTPServer(("0.0.0.0", PI_SERVER_PORT),
                                  lambda *a, **kw: Handler(q, *a, **kw))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ip = subprocess.run(["ipconfig","getifaddr","en0"],
                        capture_output=True, text=True).stdout.strip() or "MAC-IP"
    print(f"  Warte auf Raspberry Pi -> http://{ip}:{PI_SERVER_PORT}")
    print("  Beenden: Ctrl+C\n")
    try:
        while True: process(q.get(), scanned)
    except KeyboardInterrupt:
        srv.shutdown()

def run_keyboard(scanned):
    print("  Scanner anschliessen und Barcode scannen.")
    print("  Alternativ: Barcode eintippen + Enter")
    print("  Beenden: Ctrl+C\n")
    while True:
        try:
            barcode = input("  Barcode: ")
        except (EOFError, KeyboardInterrupt):
            break
        process(barcode, scanned)

def bye(*_):
    print("\n\nScanner beendet."); sys.exit(0)

signal.signal(signal.SIGINT, bye)
print("=" * 52)
print("  Jarvis Barcode Scanner")
print("=" * 52)
print(f"  Modus: {'Tastatur' if MODE=='keyboard' else 'Netzwerk (Raspberry Pi)'}")
print(f"  Ziel : Apple Reminders -> '{REMINDERS_LIST}'")
print()
scanned = []
(run_network if MODE == "network" else run_keyboard)(scanned)
if scanned:
    print(f"\nHeute gescannt ({len(scanned)}):")
    for i in scanned: print(f"   * {i}")
print()
PYTHON_END

chmod +x "$SCRIPT_PATH"

echo "===================================================="
echo "  Jarvis Barcode Scanner"
echo "===================================================="
echo ""
echo "  Scanner anschliessen und Barcode scannen."
echo "  Alternativ: Barcode eintippen + Enter"
echo "  Beenden: Ctrl+C"
echo ""

python3 "$SCRIPT_PATH"

echo ""
echo "Scanner beendet."
sleep 2
