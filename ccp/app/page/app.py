from flask import Flask, render_template
import socket
import psutil

app = Flask(__name__)


def get_internal_ip():
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip_address = addr.address
                if "Ethernet" in interface and not ip_address.startswith("169"):
                    return ip_address
    return None


@app.route("/")
def index():
    internal_ip_address = get_internal_ip()
    return render_template("index.html", ip_address=internal_ip_address)


if __name__ == "__main__":
    app.run()
