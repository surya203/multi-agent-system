"""Classroom crew: a designer and two developers build one static page."""

import os
import re
import sys
from pathlib import Path

# Skip CrewAI's end-of-run trace prompt so a class demo does not wait on it.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task

load_dotenv()

OUTPUT_DIR = Path("output")
DEFAULT_BRIEF = "A one-page site for a student photography portfolio"

# Faster classroom default. Swap to groq/openai/gpt-oss-120b for a larger model.
# max_tokens keeps a full HTML document from being cut off mid-file.
llm = LLM(model="groq/openai/gpt-oss-20b", temperature=0.4, max_tokens=8192)


def build_crew() -> Crew:
    designer = Agent(
        role="Website Designer",
        goal="Turn a short website brief into a clear visual and content plan a developer can build.",
        backstory=(
            "You design simple one-page websites for students. "
            "You choose a small palette, readable type, and a short list of sections. "
            "You write the words that will appear on the page."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    frontend_developer = Agent(
        role="Frontend Developer",
        goal="Build one self-contained HTML page from the design plan.",
        backstory=(
            "You write clean HTML and CSS for single-file pages. "
            "You put all styles in one style element and do not use external files, fonts, or images."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    review_developer = Agent(
        role="Review Developer",
        goal="Check the draft page and return a polished version that is easy to read on a phone.",
        backstory=(
            "You review student websites for a clear heading, readable contrast, "
            "and a layout that stacks on a narrow screen. You fix the page instead of only commenting on it."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    design_task = Task(
        description=(
            "Design a one-page website for this brief: {brief}\n"
            "Include the page goal, a section list with the exact copy for each section, "
            "colors as hex values, font choices available in a browser, "
            "and layout notes for a wide screen and a phone."
        ),
        expected_output=(
            "A markdown design handoff with sections, copy, colors, and layout notes."
        ),
        agent=designer,
        output_file="output/design.md",
    )

    build_task = Task(
        description=(
            "Using the design handoff, build one short HTML document for this brief: {brief}\n"
            "Include only a header, an about section, three text-only project cards, and a contact line. "
            "Rules: start with <!DOCTYPE html>, end with </html>, put CSS only in a single <style> block, "
            "use system fonts, and do not use external stylesheets, scripts, fonts, images, URLs, "
            "or background images. The main heading must be a real h1 on a solid background. "
            "Use the copy from the design. Return only the HTML document, with no markdown fences."
        ),
        expected_output=(
            "A full HTML document that starts with <!DOCTYPE html> and contains one style block."
        ),
        agent=frontend_developer,
        context=[design_task],
        output_file="output/draft.html",
    )

    review_task = Task(
        description=(
            "Review the draft HTML for this brief: {brief}\n"
            "Confirm there is one clear main heading, text contrast is readable, "
            "and sections stack on a phone-width screen. Fix anything that fails. "
            "Keep it one short page with system fonts, no images, and no external URLs. "
            "The main heading must stay a real h1 on a solid background. "
            "Return only the final HTML document, starting with <!DOCTYPE html> "
            "and ending with </html>, with no markdown fences."
        ),
        expected_output=(
            "A full HTML document that starts with <!DOCTYPE html>, with no markdown fences."
        ),
        agent=review_developer,
        context=[design_task, build_task],
        output_file="output/index.html",
    )

    return Crew(
        agents=[designer, frontend_developer, review_developer],
        tasks=[design_task, build_task, review_task],
        process=Process.sequential,
        verbose=True,
    )


def strip_html_fence(path: Path) -> None:
    """Keep the document a browser can open if the model wraps it in a code fence."""
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"<!DOCTYPE html>.*</html>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        path.write_text(match.group(0).strip() + "\n", encoding="utf-8")


def run_brief(brief: str) -> None:
    """Run the designer and both developers for one website brief."""
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY in .env (see .env.example).")

    brief = brief.strip() or DEFAULT_BRIEF
    OUTPUT_DIR.mkdir(exist_ok=True)
    crew = build_crew()
    crew.kickoff(inputs={"brief": brief})
    strip_html_fence(OUTPUT_DIR / "draft.html")
    strip_html_fence(OUTPUT_DIR / "index.html")
    page = (OUTPUT_DIR / "index.html").read_text(encoding="utf-8")
    if "</html>" not in page.lower():
        raise RuntimeError("output/index.html is incomplete. Run the crew again.")
    print(f"Design: {OUTPUT_DIR / 'design.md'}")
    print(f"Draft:  {OUTPUT_DIR / 'draft.html'}")
    print(f"Page:   {OUTPUT_DIR / 'index.html'}")


def main() -> None:
    brief = " ".join(sys.argv[1:]).strip() or DEFAULT_BRIEF
    try:
        run_brief(brief)
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
