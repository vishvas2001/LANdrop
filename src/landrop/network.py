import socket
import qrcode
import os


def get_lan_ip() -> str:
    """Detect the active local network IPv4 address (or use local Host IP)."""

    env_ip = os.getenv("HOST_IP")

    if env_ip:
        return env_ip.strip()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


def print_qr_banner(port: int = 8000) -> None:
    """Render a terminal ASCII QR code pointing to the local LANDrop server."""
    lan_ip = get_lan_ip()
    url = f"http://{lan_ip}:{port}"

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)

    print("\n" + "=" * 50)
    print(f"  LANDrop Active at : {url}")
    print("  Tip               : Use 5 GHz Hotspot for 30+ MB/s")
    print("=" * 50)
    qr.print_ascii(invert=True)
    print("=" * 50 + "\n")

if __name__ == "__main__":
    print_qr_banner()