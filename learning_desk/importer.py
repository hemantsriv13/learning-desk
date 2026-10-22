"""Bounded public-web importer. Connections pin a checked IP, including redirects."""

import http.client
import ipaddress
import socket
import ssl
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin

MAX_BYTES = 2_000_000


def destination(url):
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("Use a public HTTP or HTTPS URL without credentials.")
    if p.port not in (None, 80, 443):
        raise ValueError("Only standard web ports are supported.")
    # DNS resolution is separately bounded by the caller using a daemon worker.
    from concurrent.futures import Future
    import threading

    result = Future()

    def resolve():
        try:
            result.set_result(
                socket.getaddrinfo(
                    p.hostname,
                    p.port or (443 if p.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            )
        except Exception as exc:
            result.set_exception(exc)

    threading.Thread(target=resolve, daemon=True).start()
    addresses = result.result(timeout=5)
    if not addresses or any(
        (
            not ipaddress.ip_address(a[4][0]).is_global
            or ipaddress.ip_address(a[4][0]).is_multicast
            or ipaddress.ip_address(a[4][0]).is_reserved
        )
        for a in addresses
    ):
        raise ValueError(
            "Local, private, and reserved network destinations are blocked."
        )
    return p, addresses[0][4][0]


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.links = []
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag in (
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "header",
            "svg",
            "form",
        ):
            self.skip += 1
        if not self.skip:
            if tag in (
                "p",
                "div",
                "section",
                "article",
                "main",
                "h1",
                "h2",
                "h3",
                "li",
                "pre",
                "br",
            ):
                self.parts.append("\n")
            if tag == "a":
                self.href = dict(attrs).get("href")
                if self.href:
                    self.links.append(self.href)

    def handle_endtag(self, tag):
        if (
            tag
            in ("script", "style", "noscript", "nav", "footer", "header", "svg", "form")
            and self.skip
        ):
            self.skip -= 1
        if not self.skip and tag in ("p", "div", "section", "article", "li", "pre"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def import_url(url):
    started = time.monotonic()
    for _ in range(6):
        p, address = destination(url)
        if time.monotonic() - started > 25:
            raise ValueError("Import timed out. Paste the text instead.")
        port = p.port or (443 if p.scheme == "https" else 80)
        conn = http.client.HTTPConnection(p.hostname, port, timeout=8)
        try:
            sock = socket.create_connection((address, port), timeout=8)
            if p.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(
                    sock, server_hostname=p.hostname
                )
            conn.sock = sock
            path = p.path or "/"
            if p.query:
                path += "?" + p.query
            conn.request(
                "GET",
                path,
                headers={
                    "Host": p.netloc,
                    "User-Agent": "LearningDesk/1.0",
                    "Accept": "text/html,text/plain",
                    "Accept-Encoding": "identity",
                },
            )
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Redirect has no destination.")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(
                    f"Page returned HTTP {response.status}; no login or paywall bypass is attempted."
                )
            mime = (
                (response.getheader("Content-Type") or "").split(";")[0].strip().lower()
            )
            if mime not in ("text/html", "text/plain", "application/xhtml+xml"):
                raise ValueError(
                    "Only HTML and plain-text pages are supported. Paste text instead."
                )
            if response.getheader("Content-Encoding", "identity").lower() not in (
                "identity",
                "",
            ):
                raise ValueError(
                    "Compressed responses are not supported. Paste text instead."
                )
            size = response.getheader("Content-Length")
            if size and int(size) > MAX_BYTES:
                raise ValueError("Page is too large. Paste a shorter passage instead.")
            chunks = []
            total = 0
            while True:
                if time.monotonic() - started > 30:
                    raise ValueError("Import timed out. Paste text instead.")
                chunk = response.read(min(16384, MAX_BYTES + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError(
                        "Page is too large. Paste a shorter passage instead."
                    )
            raw = b"".join(chunks).decode("utf-8", errors="replace")
        finally:
            conn.close()
        links = []
        if mime != "text/plain":
            parser = Extractor()
            parser.feed(raw)
            raw = "\n\n".join(
                line.strip()
                for line in "".join(parser.parts).splitlines()
                if line.strip()
            )
            links = list(
                dict.fromkeys(
                    urljoin(url, link)
                    for link in parser.links
                    if urlsplit(urljoin(url, link)).scheme in ("http", "https")
                )
            )[:100]
        if len(raw) < 200:
            raise ValueError(
                "Too little readable content; the page may need login or JavaScript. Paste text instead."
            )
        if len(raw) > 100000:
            raise ValueError(
                "Extracted content is too long. Paste a selected passage instead."
            )
        warning = "Extracted public page text; completeness is not guaranteed. Compare with the source. If incomplete, paste the intended text."
        return {"text": raw, "url": url, "links": links, "note": warning}
    raise ValueError("Too many redirects. Paste text instead.")
