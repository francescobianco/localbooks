#!/usr/bin/env python3
"""localbooks - minimal HTML-only HTTP server for downloading ebooks on a Kobo.

Serves ~/Books (or LOCALBOOKS_DIR) as plain HTML pages and, when avahi-utils
is installed, publishes an mDNS name (default books.local) pointing to this
machine's current LAN IP.
"""

import html
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BOOKS_DIR = os.path.realpath(os.path.expanduser(os.environ.get("LOCALBOOKS_DIR", "~/Books")))
PORT = int(os.environ.get("LOCALBOOKS_PORT", "80"))
MDNS_NAME = os.environ.get("LOCALBOOKS_NAME", "books.local")

BOOK_TYPES = {
    ".epub": "application/epub+zip",
    ".kepub": "application/epub+zip",
    ".pdf": "application/pdf",
    ".mobi": "application/x-mobipocket-ebook",
    ".cbz": "application/vnd.comicbook+zip",
    ".cbr": "application/vnd.comicbook-rar",
    ".txt": "text/plain; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".rtf": "application/rtf",
}

PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ font-family: sans-serif; font-size: 1.3em; margin: 1em; }}
h1 {{ font-size: 1.4em; }}
ul {{ list-style: none; padding: 0; }}
li {{ border-bottom: 1px solid #000; }}
a {{ display: block; padding: 0.7em 0.2em; color: #000; text-decoration: none; }}
.size {{ font-size: 0.7em; }}
</style></head>
<body><h1>{title}</h1><ul>
{items}
</ul></body></html>
"""


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class Handler(BaseHTTPRequestHandler):
    server_version = "localbooks"

    def resolve(self):
        """Map the request path to a filesystem path inside BOOKS_DIR, or None."""
        rel = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip("/")
        path = os.path.realpath(os.path.join(BOOKS_DIR, rel))
        if path != BOOKS_DIR and not path.startswith(BOOKS_DIR + os.sep):
            return None
        return path

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, head=False):
        path = self.resolve()
        if path is None or not os.path.exists(path):
            self.send_error(404)
        elif os.path.isdir(path):
            if not self.path.split("?")[0].endswith("/"):
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
            else:
                self.send_listing(path, head)
        else:
            self.send_file(path, head)

    def send_listing(self, path, head):
        entries = []
        for name in sorted(os.listdir(path), key=str.lower):
            if name.startswith("."):
                continue
            full = os.path.join(path, name)
            quoted = urllib.parse.quote(name)
            if os.path.isdir(full):
                entries.append(f'<li><a href="{quoted}/">&#128193; {html.escape(name)}/</a></li>')
            elif os.path.isfile(full):
                size = human_size(os.path.getsize(full))
                entries.append(
                    f'<li><a href="{quoted}">{html.escape(name)} '
                    f'<span class="size">({size})</span></a></li>'
                )
        if path != BOOKS_DIR:
            entries.insert(0, '<li><a href="../">&larr; ..</a></li>')
        if not entries:
            entries.append("<li>No books found.</li>")

        rel = os.path.relpath(path, BOOKS_DIR)
        title = "Books" if rel == "." else "Books / " + rel.replace(os.sep, " / ")
        body = PAGE.format(title=html.escape(title), items="\n".join(entries)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def send_file(self, path, head):
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        ctype = BOOK_TYPES.get(ext) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(os.path.getsize(path)))
        self.send_header(
            "Content-Disposition",
            "attachment; filename*=UTF-8''" + urllib.parse.quote(name),
        )
        self.end_headers()
        if not head:
            with open(path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)


def local_ip():
    """Return the LAN IP used for outgoing traffic (no packet is actually sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))
            return s.getsockname()[0]
        except OSError:
            return None


def publish_mdns():
    """Keep `avahi-publish -a -R NAME IP` running, restarting it when the IP changes."""
    if not shutil.which("avahi-publish"):
        print("avahi-publish not found: mDNS name disabled (apt install avahi-utils)", flush=True)
        return
    proc, ip = None, None
    while True:
        current = local_ip()
        if current != ip or (proc and proc.poll() is not None):
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait()
            ip, proc = current, None
            if ip:
                print(f"Publishing {MDNS_NAME} -> {ip}", flush=True)
                proc = subprocess.Popen(["avahi-publish", "-a", "-R", MDNS_NAME, ip])
        time.sleep(30)


def main():
    if not os.path.isdir(BOOKS_DIR):
        os.makedirs(BOOKS_DIR, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as e:
        sys.exit(f"Cannot listen on port {PORT}: {e.strerror}")
    threading.Thread(target=publish_mdns, daemon=True).start()
    port = "" if PORT == 80 else f":{PORT}"
    print(f"Serving {BOOKS_DIR}", flush=True)
    print(f"  http://{MDNS_NAME}{port}/", flush=True)
    print(f"  http://{local_ip()}{port}/", flush=True)
    print(f"  http://{socket.gethostname()}{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
