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
pip install -r requirements.txt
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
