#!/bin/bash
# Jarvis Barcode Scanner - Netzwerk-Modus (Raspberry Pi)
# Doppelklick genuegt – installiert sich selbst und startet sofort.

SCRIPT_PATH="$HOME/Scripts/barcode_scanner.py"
mkdir -p "$HOME/Scripts"

cat > "$SCRIPT_PATH" << 'PYTHON_END'
#!/usr/bin/env python3
import sys, json, urllib.request, subprocess, signal, http.server, threading, queue

REMINDERS_LIST = 'Einkaufsliste'
PI_SERVER_PORT = 8765

def lookup_product(barcode):
    url = 'https://world.openfoodfacts.org/api/v2/product/' + barcode + '.json?fields=product_name_de,product_name,brands'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Jarvis-Scanner/1.0'})
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read().decode())
        if d.get('status') == 1:
            p = d.get('product', {})
            n = p.get('product_name_de') or p.get('product_name') or p.get('brands', '')
            return n.strip() or None
    except Exception:
        pass
    return None

def add_to_reminders(item):
    item = item.replace('"', '')
    lines = [
        'tell application "Reminders"',
        'if not (exists list "' + REMINDERS_LIST + '") then',
        'make new list with properties {name:"' + REMINDERS_LIST + '"}',
        'end if',
        'make new reminder at end of list "' + REMINDERS_LIST + '" with properties {name:"' + item + '"}',
        'end tell',
    ]
    scpt = '\n'.join(lines)
    return subprocess.run(['osascript', '-e', scpt], capture_output=True).returncode == 0

def process(barcode, scanned):
    barcode = barcode.strip()
    if not barcode:
        return
    print('  Suche: ' + barcode + ' ...', flush=True)
    name = lookup_product(barcode)
    if not name:
        print('  Nicht gefunden (Barcode: ' + barcode + ')')
        try:
            name = input('  Name eingeben (Enter = ueberspringen): ').strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not name:
            return
    if add_to_reminders(name):
        print('  OK: ' + name + ' -> Einkaufsliste')
        scanned.append(name)
    else:
        print('  FEHLER: Reminders nicht erreichbar')

class Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, q, *a, **kw):
        self._q = q
        super().__init__(*a, **kw)
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        self._q.put(self.rfile.read(n).decode().strip())
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Jarvis Scanner laeuft')
    def log_message(self, *_):
        pass

def get_local_ip():
    for iface in ('en0', 'en1'):
        try:
            ip = subprocess.run(['ipconfig', 'getifaddr', iface], capture_output=True, text=True).stdout.strip()
            if ip:
                return ip
        except Exception:
            pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'unbekannt'

def run_network(scanned):
    q = queue.Queue()
    srv = http.server.HTTPServer(('0.0.0.0', PI_SERVER_PORT), lambda *a, **kw: Handler(q, *a, **kw))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ip = get_local_ip()
    print('  Mac-IP:   ' + ip)
    print('  Pi sendet an: http://' + ip + ':' + str(PI_SERVER_PORT))
    print('  Bereit – warte auf Barcodes vom Raspberry Pi ...')
    print()
    try:
        while True:
            process(q.get(), scanned)
    except KeyboardInterrupt:
        srv.shutdown()

def bye(*a):
    print('\nScanner beendet.')
    sys.exit(0)

signal.signal(signal.SIGINT, bye)
print('=' * 52)
print('  Jarvis Barcode Scanner  [Netzwerk-Modus]')
print('=' * 52)
print('  Ziel: Apple Reminders -> Einkaufsliste')
print()
scanned = []
run_network(scanned)
PYTHON_END

chmod +x "$SCRIPT_PATH"

clear
echo "======================================================"
echo "  Jarvis Barcode Scanner  [Netzwerk-Modus]"
echo "======================================================"
echo "  Ziel: Apple Reminders -> Einkaufsliste"
echo ""

python3 "$SCRIPT_PATH"

echo ""
echo "Scanner beendet."
sleep 3
