"""Local page where a student types a website brief."""

import html
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

os.chdir(Path(__file__).resolve().parent)

import website_crew

HOST = "127.0.0.1"
PORT = 8000
OUTPUT_DIR = Path("output")
SITE_FILES = {"index.html": "text/html; charset=utf-8", "draft.html": "text/html; charset=utf-8"}
BUILD_LOCK = threading.Lock()

FORM = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Website crew</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; background: #f4f1ea; color: #1c1915; }}
  main {{ max-width: 40rem; margin: 0 auto; padding: 2.5rem 1.25rem 3rem; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 0.4rem; }}
  p {{ line-height: 1.5; }}
  label {{ display: block; font-weight: 650; margin: 1.25rem 0 0.4rem; }}
  textarea {{ width: 100%; min-height: 8rem; box-sizing: border-box; padding: 0.75rem; font: inherit; border: 1px solid #c9c2b4; border-radius: 8px; background: #fff; }}
  button {{ margin-top: 1rem; font: inherit; font-weight: 650; background: #1c1915; color: #fff; border: 0; border-radius: 8px; padding: 0.7rem 1.1rem; cursor: pointer; }}
  button:disabled {{ opacity: 0.6; cursor: wait; }}
  .note {{ color: #5c564c; }}
  .error {{ background: #fff; border-left: 4px solid #9b2c2c; padding: 0.75rem 1rem; }}
  iframe {{ width: 100%; height: 75vh; border: 1px solid #c9c2b4; border-radius: 8px; background: #fff; }}
  a {{ color: #0f5c4c; }}
</style>
</head>
<body>
<main>
  <h1>Website crew</h1>
  <p class="note">A designer, a frontend developer, and a review developer build one page. This usually takes about a minute.</p>
  {message}
  <form method="post" action="/build">
    <label for="brief">What website do you want?</label>
    <textarea id="brief" name="brief" required>{brief}</textarea>
    <button type="submit">Build website</button>
  </form>
  {result}
</main>
<script>
  const form = document.querySelector("form");
  form.addEventListener("submit", () => {{
    const button = form.querySelector("button");
    button.disabled = true;
    button.textContent = "The crew is building your page…";
  }});
</script>
</body>
</html>
"""


def page(message: str = "", brief: str = "", result: str = "") -> bytes:
    html_page = FORM.format(
        message=message,
        brief=html.escape(brief),
        result=result,
    )
    return html_page.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index"):
            self._send(200, page())
            return
        if path.startswith("/site/"):
            self._send_site(path.removeprefix("/site/"))
            return
        self._send(404, page("<p class='error'>That page was not found.</p>"))

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/build":
            self._send(404, page("<p class='error'>That page was not found.</p>"))
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(min(length, 8000)).decode("utf-8", errors="replace")
        brief = parse_qs(raw).get("brief", [""])[0].strip()
        if not brief:
            self._send(400, page("<p class='error'>Type a website request first.</p>"))
            return
        if not BUILD_LOCK.acquire(blocking=False):
            self._send(
                409,
                page("<p class='error'>A website is already being built. Wait for it to finish.</p>", brief),
            )
            return
        try:
            website_crew.run_brief(brief)
        except Exception as exc:
            self._send(500, page(f"<p class='error'>{html.escape(str(exc))}</p>", brief))
            return
        finally:
            BUILD_LOCK.release()

        result = """
        <h2>Your page</h2>
        <p><a href="/site/index.html" target="_blank">Open the page</a>
        · <a href="/site/design.md">Read the design notes</a></p>
        <iframe title="Generated website" src="/site/index.html"></iframe>
        """
        self._send(200, page(brief=brief, result=result))

    def _send_site(self, name: str) -> None:
        if name == "design.md":
            path = OUTPUT_DIR / "design.md"
            if not path.is_file():
                self._send(404, page("<p class='error'>No design notes yet.</p>"))
                return
            notes = html.escape(path.read_text(encoding="utf-8"))
            body = page(result=f"<h2>Design notes</h2><pre>{notes}</pre><p><a href='/'>Back</a></p>")
            self._send(200, body)
            return
        content_type = SITE_FILES.get(name)
        path = OUTPUT_DIR / name
        if content_type is None or not path.is_file():
            self._send(404, page("<p class='error'>That file was not found.</p>"))
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Open http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
