#!/usr/bin/env python3
"""
Jarvis Raspberry Pi Scanner
Laueft auf dem Raspberry Pi - liest Barcodes vom USB-Scanner
und schickt sie per HTTP an den Mac.

Installation:
  pip3 install evdev
  sudo python3 pi_scanner.py
"""

import sys
import time
import socket
import urllib.request
import urllib.error

# ── Konfiguration ──────────────────────────────────────────────────────────────
MAC_HOSTNAME = "Minizwei.local"   # Mac Bonjour-Hostname (aendert sich nie)
MAC_PORT     = 8765
# ──────────────────────────────────────────────────────────────────────────────

KEY_MAP = {
    2: "1", 3: "2", 4: "3", 5: "4", 6: "5",
    7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
    16: "q", 17: "w", 18: "e", 19: "r", 20: "t",
    21: "y", 22: "u", 23: "i", 24: "o", 25: "p",
    30: "a", 31: "s", 32: "d", 33: "f", 34: "g",
    35: "h", 36: "j", 37: "k", 38: "l",
    44: "z", 45: "x", 46: "c", 47: "v", 48: "b",
    49: "n", 50: "m",
    28: "\n",
}


def resolve_mac():
    """Loest Mac-Hostname auf und gibt IP zurueck (oder None)."""
    try:
        ip = socket.gethostbyname(MAC_HOSTNAME)
        return ip
    except socket.gaierror:
        return None


def test_connection():
    """Testet ob der Mac erreichbar ist. Gibt (ok, info) zurueck."""
    try:
        req = urllib.request.Request(
            f"http://{MAC_HOSTNAME}:{MAC_PORT}",
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True, resp.read().decode()
    except urllib.error.URLError as e:
        return False, str(e.reason)
    except Exception as e:
        return False, str(e)


def send_barcode(barcode: str) -> bool:
    """Barcode per HTTP POST an den Mac schicken. Retry bei Fehler."""
    url  = f"http://{MAC_HOSTNAME}:{MAC_PORT}"
    data = barcode.encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            if attempt < 2:
                print(f"  Versuch {attempt+1} fehlgeschlagen, nochmal ...")
                time.sleep(1)
            else:
                print(f"  Mac nicht erreichbar: {e}")
                print(f"  Pruefe ob Scanner_Netzwerk.command auf dem Mac laeuft!")
    return False


def find_scanner():
    """USB-Scanner (HID-Tastatur) automatisch erkennen."""
    try:
        import evdev
    except ImportError:
        print("FEHLER: evdev nicht installiert!")
        print("  Ausfuehren: pip3 install evdev")
        sys.exit(1)

    devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
    if not devices:
        print("FEHLER: Keine Input-Geraete gefunden.")
        print("  Pruefe ob der Scanner per USB angeschlossen ist.")
        print("  Evtl. mit 'sudo python3 pi_scanner.py' starten.")
        sys.exit(1)

    for dev in devices:
        name_lower = dev.name.lower()
        if any(kw in name_lower for kw in ["scanner", "barcode", "hid"]):
            return dev
    # Fallback: erstes Keyboard-Geraet
    for dev in devices:
        caps = dev.capabilities(verbose=True)
        if ("EV_KEY", 1) in caps:
            return dev

    print("FEHLER: Kein Scanner / Tastaturgeraet gefunden.")
    sys.exit(1)


def main():
    print("=" * 52)
    print("  Jarvis Pi Scanner")
    print("=" * 52)
    print(f"  Sende an: {MAC_HOSTNAME}:{MAC_PORT}")

    # IP aufloesen und anzeigen
    ip = resolve_mac()
    if ip:
        print(f"  Mac-IP  : {ip} (aufgeloest via mDNS)")
    else:
        print(f"  WARNUNG : {MAC_HOSTNAME} konnte nicht aufgeloest werden!")
        print(f"  -> Pruefe ob der Mac im gleichen WLAN ist")
        print(f"  -> Pruefe ob der Mac-Name korrekt ist:")
        print(f"     Mac -> Systemeinstellungen -> Allgemein -> Teilen -> 'Lokaler Hostname'")
        print(f"  -> Aktuell konfiguriert: MAC_HOSTNAME = '{MAC_HOSTNAME}'")
        antwort = input("\n  Trotzdem weitermachen? (j/n): ").strip().lower()
        if antwort != 'j':
            sys.exit(1)

    # Verbindungstest
    print("\n  Teste Verbindung zum Mac ...")
    ok, info = test_connection()
    if ok:
        print(f"  Verbindung OK: {info}")
    else:
        print(f"  FEHLER: Verbindung fehlgeschlagen!")
        print(f"  Grund: {info}")
        print(f"\n  Checkliste:")
        print(f"  1. Ist 'Scanner_Netzwerk.command' auf dem Mac gestartet?")
        print(f"  2. Sind Mac und Pi im gleichen WLAN?")
        print(f"  3. Stimmt der Hostname '{MAC_HOSTNAME}'?")
        print(f"     Richtigen Hostname auf dem Mac ermitteln:")
        print(f"     Terminal auf Mac: scutil --get LocalHostName")
        print(f"     Dann in dieser Datei anpassen: MAC_HOSTNAME = 'NeuerName.local'")
        antwort = input("\n  Trotzdem weitermachen? (j/n): ").strip().lower()
        if antwort != 'j':
            sys.exit(1)

    # Scanner suchen
    scanner = find_scanner()
    print(f"\n  Scanner erkannt: {scanner.name}")
    print("  Bereit - Barcode scannen ...\n")

    import evdev
    current_barcode = ""

    for event in scanner.read_loop():
        if event.type != evdev.ecodes.EV_KEY:
            continue
        if event.value != 1:
            continue

        char = KEY_MAP.get(event.code)
        if char is None:
            continue

        if char == "\n":
            if current_barcode:
                print(f"  Sende: {current_barcode} ... ", end="", flush=True)
                ok = send_barcode(current_barcode)
                print("OK" if ok else "FEHLER")
                current_barcode = ""
        else:
            current_barcode += char


if __name__ == "__main__":
    main()
