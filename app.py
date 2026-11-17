"""Local page where a student types a website brief.

Vercel serves the Flask app named `app`. `python app.py` still opens it locally.
"""

import html
import json
import os
import threading
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

from flask import Flask, request

import website_crew

app = Flask(__name__)
HOST = "127.0.0.1"
PORT = 8000
OUTPUT_DIR = Path("output")
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
  pre {{ white-space: pre-wrap; background: #fff; padding: 1rem; border-radius: 8px; }}
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
  const openPage = document.getElementById("open-page");
  const pageData = document.getElementById("page-data");
  if (openPage && pageData) {{
    openPage.addEventListener("click", (event) => {{
      event.preventDefault();
      const html = JSON.parse(pageData.textContent);
      const url = URL.createObjectURL(new Blob([html], {{type: "text/html"}}));
      window.open(url, "_blank");
    }});
  }}
</script>
</body>
</html>
"""


def page(message: str = "", brief: str = "", result: str = "") -> str:
    return FORM.format(
        message=message,
        brief=html.escape(brief),
        result=result,
    )


def result_block(built: dict[str, str]) -> str:
    notes = html.escape(built["design"])
    preview = html.escape(built["page"], quote=True)
    payload = json.dumps(built["page"]).replace("<", "\\u003c")
    return f"""
    <h2>Your page</h2>
    <p><a id="open-page" href="#">Open the page</a></p>
    <iframe title="Generated website" srcdoc="{preview}"></iframe>
    <h2>Design notes</h2>
    <pre>{notes}</pre>
    <script type="application/json" id="page-data">{payload}</script>
    """


@app.get("/")
def home():
    return page(), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/build")
def build():
    brief = (request.form.get("brief") or "").strip()
    if not brief:
        body = page("<p class='error'>Type a website request first.</p>")
        return body, 400, {"Content-Type": "text/html; charset=utf-8"}
    if not BUILD_LOCK.acquire(blocking=False):
        body = page(
            "<p class='error'>A website is already being built. Wait for it to finish.</p>",
            brief,
        )
        return body, 409, {"Content-Type": "text/html; charset=utf-8"}
    try:
        built = website_crew.run_brief(brief)
    except Exception as exc:
        body = page(f"<p class='error'>{html.escape(str(exc))}</p>", brief)
        return body, 500, {"Content-Type": "text/html; charset=utf-8"}
    finally:
        BUILD_LOCK.release()
    body = page(brief=brief, result=result_block(built))
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/site/<name>")
def site_file(name: str):
    if name == "design.md":
        path = OUTPUT_DIR / "design.md"
        if not path.is_file():
            body = page("<p class='error'>No design notes yet.</p>")
            return body, 404, {"Content-Type": "text/html; charset=utf-8"}
        notes = html.escape(path.read_text(encoding="utf-8"))
        body = page(result=f"<h2>Design notes</h2><pre>{notes}</pre><p><a href='/'>Back</a></p>")
        return body, 200, {"Content-Type": "text/html; charset=utf-8"}
    if name not in {"index.html", "draft.html"}:
        body = page("<p class='error'>That file was not found.</p>")
        return body, 404, {"Content-Type": "text/html; charset=utf-8"}
    path = OUTPUT_DIR / name
    if not path.is_file():
        body = page("<p class='error'>That file was not found.</p>")
        return body, 404, {"Content-Type": "text/html; charset=utf-8"}
    return path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}


def main() -> None:
    print(f"Open http://{HOST}:{PORT}", flush=True)
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    main()
