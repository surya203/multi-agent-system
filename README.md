# Website crew

Three CrewAI agents turn a one-line website brief into a static page:

1. Designer writes `output/design.md`.
2. Frontend developer writes `output/draft.html`.
3. Review developer writes `output/index.html`.

Requires Python 3.10, 3.11, 3.12, or 3.13, and a [Groq API key](https://console.groq.com/keys).

## Run (Windows)

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-local.txt
copy .env.example .env
```

Put your key in `.env`:

```
GROQ_API_KEY=your_key_here
```

Then open the form:

```powershell
python app.py
```

Go to [http://127.0.0.1:8000](http://127.0.0.1:8000), type the website you want, and choose **Build website**. The finished page appears on the same screen. Design notes are linked above it.

The command line still works:

```powershell
python website_crew.py "A one-page site for a student photography portfolio"
```

Open `output/index.html` in a browser. Compare it with `output/design.md`.

Keep the real key in `.env` only. Do not commit it.

## Deploy on Vercel

Vercel installs `requirements.txt` only. CrewAI is left out of that file because the library is about 900 MB and a Python function on Vercel can be at most 500 MB. The hosted site still runs the designer, frontend developer, and review developer, in that order, by calling Groq directly.

In the Vercel project settings, add `GROQ_API_KEY` for Production (the same key as `.env`). Then push `main`. A build takes about a minute to finish a page, which fits the 300 second function limit in `vercel.json`.
