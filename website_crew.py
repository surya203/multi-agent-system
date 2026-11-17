"""Classroom crew: a designer and two developers build one static page.

Local installs can use CrewAI. Vercel cannot: that library and its data
dependencies are about 900 MB, over the 500 MB function limit. When CrewAI
is not installed, the same three roles call Groq's API directly.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Skip CrewAI's end-of-run trace prompt so a class demo does not wait on it.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("output")
DEFAULT_BRIEF = "A one-page site for a student photography portfolio"
GROQ_MODEL = "openai/gpt-oss-20b"
# CrewAI's provider prefix. The HTTPS API uses GROQ_MODEL on its own.
CREWAI_MODEL = f"groq/{GROQ_MODEL}"

DESIGNER_BACKSTORY = (
    "You design simple one-page websites for students. "
    "You choose a small palette, readable type, and a short list of sections. "
    "You write the words that will appear on the page."
)
FRONTEND_BACKSTORY = (
    "You write clean HTML and CSS for single-file pages. "
    "You put all styles in one style element and do not use external files, fonts, or images."
)
REVIEW_BACKSTORY = (
    "You review student websites for a clear heading, readable contrast, "
    "and a layout that stacks on a narrow screen. You fix the page instead of only commenting on it."
)


def design_request(brief: str) -> str:
    return (
        f"Design a one-page website for this brief: {brief}\n"
        "Include the page goal, a section list with the exact copy for each section, "
        "colors as hex values, font choices available in a browser, "
        "and layout notes for a wide screen and a phone."
    )


def build_request(brief: str, design: str) -> str:
    return (
        f"Using the design handoff, build one short HTML document for this brief: {brief}\n"
        "Include only a header, an about section, three text-only project cards, and a contact line. "
        "Rules: start with <!DOCTYPE html>, end with </html>, put CSS only in a single <style> block, "
        "use system fonts, and do not use external stylesheets, scripts, fonts, images, URLs, "
        "or background images. The main heading must be a real h1 on a solid background. "
        "Use the copy from the design. Return only the HTML document, with no markdown fences.\n\n"
        f"Design handoff:\n{design}"
    )


def review_request(brief: str, design: str, draft: str) -> str:
    return (
        f"Review the draft HTML for this brief: {brief}\n"
        "Confirm there is one clear main heading, text contrast is readable, "
        "and sections stack on a phone-width screen. Fix anything that fails. "
        "Keep it one short page with system fonts, no images, and no external URLs. "
        "The main heading must stay a real h1 on a solid background. "
        "Return only the final HTML document, starting with <!DOCTYPE html> "
        "and ending with </html>, with no markdown fences.\n\n"
        f"Design handoff:\n{design}\n\nDraft HTML:\n{draft}"
    )


def extract_html(text: str) -> str:
    """Keep the document a browser can open if the model wraps it in a code fence."""
    match = re.search(
        r"<!DOCTYPE html>.*</html>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(0).strip() + "\n"
    return text


def _run_with_crewai(brief: str) -> dict[str, str]:
    from crewai import Agent, Crew, LLM, Process, Task

    # Faster classroom default. Swap CREWAI_MODEL to groq/openai/gpt-oss-120b
    # for a larger model. max_tokens keeps a full HTML document from being cut off.
    llm = LLM(model=CREWAI_MODEL, temperature=0.4, max_tokens=8192)

    designer = Agent(
        role="Website Designer",
        goal="Turn a short website brief into a clear visual and content plan a developer can build.",
        backstory=DESIGNER_BACKSTORY,
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )
    frontend_developer = Agent(
        role="Frontend Developer",
        goal="Build one self-contained HTML page from the design plan.",
        backstory=FRONTEND_BACKSTORY,
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )
    review_developer = Agent(
        role="Review Developer",
        goal="Check the draft page and return a polished version that is easy to read on a phone.",
        backstory=REVIEW_BACKSTORY,
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    design_task = Task(
        description=design_request(brief),
        expected_output="A markdown design handoff with sections, copy, colors, and layout notes.",
        agent=designer,
        output_file="output/design.md",
    )
    build_task = Task(
        description=(
            "Using the design handoff in your context, build one short HTML document "
            f"for this brief: {brief}\n"
            "Include only a header, an about section, three text-only project cards, and a contact line. "
            "Rules: start with <!DOCTYPE html>, end with </html>, put CSS only in a single <style> block, "
            "use system fonts, and do not use external stylesheets, scripts, fonts, images, URLs, "
            "or background images. The main heading must be a real h1 on a solid background. "
            "Use the copy from the design. Return only the HTML document, with no markdown fences."
        ),
        expected_output="A full HTML document that starts with <!DOCTYPE html> and contains one style block.",
        agent=frontend_developer,
        context=[design_task],
        output_file="output/draft.html",
    )
    review_task = Task(
        description=(
            f"Review the draft HTML in your context for this brief: {brief}\n"
            "Confirm there is one clear main heading, text contrast is readable, "
            "and sections stack on a phone-width screen. Fix anything that fails. "
            "Keep it one short page with system fonts, no images, and no external URLs. "
            "The main heading must stay a real h1 on a solid background. "
            "Return only the final HTML document, starting with <!DOCTYPE html> "
            "and ending with </html>, with no markdown fences."
        ),
        expected_output="A full HTML document that starts with <!DOCTYPE html>, with no markdown fences.",
        agent=review_developer,
        context=[design_task, build_task],
        output_file="output/index.html",
    )

    crew = Crew(
        agents=[designer, frontend_developer, review_developer],
        tasks=[design_task, build_task, review_task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()
    return {
        "design": Path("output/design.md").read_text(encoding="utf-8"),
        "draft": extract_html(Path("output/draft.html").read_text(encoding="utf-8")),
        "page": extract_html(Path("output/index.html").read_text(encoding="utf-8")),
    }


def _groq_chat(system: str, user: str) -> str:
    body = json.dumps(
        {
            "model": GROQ_MODEL,
            "temperature": 0.4,
            "max_tokens": 8192,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise RuntimeError(f"Groq request failed ({exc.code}). {detail}") from exc

    text = (payload.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    if not text.strip():
        raise RuntimeError("The model returned an empty answer. Run it again.")
    return text


def _run_with_groq(brief: str) -> dict[str, str]:
    design = _groq_chat(
        "You are a website designer. " + DESIGNER_BACKSTORY,
        design_request(brief),
    )
    draft = extract_html(
        _groq_chat(
            "You are a frontend developer. " + FRONTEND_BACKSTORY,
            build_request(brief, design),
        )
    )
    page = extract_html(
        _groq_chat(
            "You are a review developer. " + REVIEW_BACKSTORY,
            review_request(brief, design, draft),
        )
    )
    return {"design": design, "draft": draft, "page": page}


def _write_outputs(result: dict[str, str]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "design.md").write_text(result["design"], encoding="utf-8")
    (OUTPUT_DIR / "draft.html").write_text(result["draft"], encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text(result["page"], encoding="utf-8")
    print(f"Design: {OUTPUT_DIR / 'design.md'}")
    print(f"Draft:  {OUTPUT_DIR / 'draft.html'}")
    print(f"Page:   {OUTPUT_DIR / 'index.html'}")


def run_brief(brief: str) -> dict[str, str]:
    """Run the designer and both developers for one website brief."""
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY in .env (see .env.example).")

    brief = brief.strip() or DEFAULT_BRIEF
    try:
        import crewai  # noqa: F401
    except ImportError:
        result = _run_with_groq(brief)
    else:
        result = _run_with_crewai(brief)

    page = result["page"]
    if "</html>" not in page.lower():
        raise RuntimeError("The page HTML is incomplete. Run it again.")
    try:
        _write_outputs(result)
    except OSError:
        # Vercel can only write under /tmp, and the response already carries the page.
        pass
    return result


def main() -> None:
    brief = " ".join(sys.argv[1:]).strip() or DEFAULT_BRIEF
    try:
        run_brief(brief)
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
