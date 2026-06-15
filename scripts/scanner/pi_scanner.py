#!/usr/bin/env python3
"""
Jarvis Raspberry Pi Scanner
Läuft auf dem Raspberry Pi – liest Barcodes vom USB-Scanner
und schickt sie per HTTP an den Mac (barcode_scanner.py).

Installation:
  pip3 install evdev requests
  sudo python3 pi_scanner.py
"""

import sys
import time
import urllib.request
import urllib.error

# ── Konfiguration ──────────────────────────────────────────────────────────────
MAC_IP   = "192.168.1.XXX"   # ← IP-Adresse des Mac im Heimnetz eintragen
MAC_PORT = 8765
# ──────────────────────────────────────────────────────────────────────────────

# HID-Tastatur → ASCII Mapping für USB-Scanner im Keyboard-Modus
KEY_MAP = {
    2: "1", 3: "2", 4: "3", 5: "4", 6: "5",
    7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
    16: "q", 17: "w", 18: "e", 19: "r", 20: "t",
    21: "y", 22: "u", 23: "i", 24: "o", 25: "p",
    30: "a", 31: "s", 32: "d", 33: "f", 34: "g",
    35: "h", 36: "j", 37: "k", 38: "l",
    44: "z", 45: "x", 46: "c", 47: "v", 48: "b",
    49: "n", 50: "m",
    28: "\n",  # Enter = Barcode abgeschlossen
}


def find_scanner():
    """USB-Scanner (HID-Tastatur) automatisch erkennen."""
    try:
        import evdev
        devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
        for dev in devices:
            caps = dev.capabilities(verbose=True)
            if ("EV_KEY", 1) in caps:
                # Scanner bevorzugen (enthält normalerweise "scanner" oder "barcode" im Namen)
                name_lower = dev.name.lower()
                if any(kw in name_lower for kw in ["scanner", "barcode", "hid", "usb"]):
                    return dev
        # Fallback: erstes Tastaturgerät
        for dev in devices:
            if ("EV_KEY", 1) in dev.capabilities(verbose=True):
                return dev
    except ImportError:
        print("FEHLER: evdev nicht installiert → pip3 install evdev")
        sys.exit(1)
    return None


def send_barcode(barcode: str) -> bool:
    """Barcode per HTTP an den Mac schicken."""
    url  = f"http://{MAC_IP}:{MAC_PORT}"
    data = barcode.encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  ⚠️  Konnte Mac nicht erreichen: {e}")
        return False


def main():
    print("=" * 52)
    print("  🛒 Jarvis Pi Scanner")
    print("=" * 52)
    print(f"  Mac : http://{MAC_IP}:{MAC_PORT}")
    print()

    scanner = find_scanner()
    if not scanner:
        print("FEHLER: Kein USB-Scanner gefunden.")
        sys.exit(1)

    print(f"  Scanner erkannt: {scanner.name}")
    print("  Bereit – Barcode scannen …\n")

    import evdev
    current_barcode = ""

    for event in scanner.read_loop():
        if event.type != evdev.ecodes.EV_KEY:
            continue
        if event.value != 1:  # nur Key-Down
            continue

        char = KEY_MAP.get(event.code)
        if char is None:
            continue

        if char == "\n":
            if current_barcode:
                print(f"  📦 Sende: {current_barcode}")
                ok = send_barcode(current_barcode)
                print(f"  {'✅ OK' if ok else '❌ Fehler'}")
                current_barcode = ""
        else:
            current_barcode += char


if __name__ == "__main__":
    main()
