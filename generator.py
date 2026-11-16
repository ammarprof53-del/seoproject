"""Build a static comparison site from a UTF-8 CSV using only Python's standard library."""

import argparse
import csv
import html
import re
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
REQUIRED_COLUMNS = ("Target Tool", "Competitor", "Use Case")
TOKEN = re.compile(r"{{([A-Za-z][A-Za-z0-9_]*)}}")
TAILWIND = "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"


def slugify(value):
    """Normalize names to lowercase ASCII URL segments."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def load_rows(path):
    """Validate the CSV and fail before touching the current build."""
    pages = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        headers = reader.fieldnames or []
        if not set(REQUIRED_COLUMNS).issubset(headers) or len(headers) != len(set(headers)):
            raise ValueError(f"{path.name} needs unique headers including {', '.join(REQUIRED_COLUMNS)}")
        for row in reader:
            if None in row or None in row.values():
                raise ValueError(f"CSV line {reader.line_num} has the wrong number of columns.")
            row = {key: value.strip() for key, value in row.items()}
            parts = [slugify(row[name]) for name in REQUIRED_COLUMNS]
            if not all(parts):
                raise ValueError(f"CSV line {reader.line_num} has an empty or non-sluggable required field.")
            tool, competitor, use_case = parts
            slug = f"{tool}-vs-{competitor}-for-{use_case}"
            if len(slug) > 180 or slug in pages:
                raise ValueError(f"CSV line {reader.line_num} has a duplicate or overly long slug: {slug}")
            pages[slug] = row
    if not pages:
        raise ValueError("The dataset has no rows.")
    return pages


def comparison_content(row):
    """Turn editorial inputs into a practical trial without inventing product claims."""
    tool, competitor, use_case = (row[name] for name in REQUIRED_COLUMNS)
    scenario = row.get("Workflow Scenario") or (
        f"Choose a real task from your {use_case.lower()} workflow and repeat it with the same inputs."
    )
    checks = [
        item.strip()
        for item in row.get("Evaluation Checklist", "").split("|")
        if item.strip()
    ] or [
        "Time the task from setup to completion",
        "Test what a teammate with limited access can do",
        "Check how to export the finished work",
    ]
    trial = (
        f"Use the same starting materials and participants in {tool} and {competitor}. "
        "Record setup time, where someone needs help, and any manual steps the team would repeat."
    )
    checklist = "".join(f"<li>{html.escape(item)}</li>" for item in checks)
    return (
        f"<p>{html.escape(scenario)}</p>\n"
        f"<p>{html.escape(trial)}</p>\n"
        f'<ul class="list-disc space-y-2 pl-5">{checklist}</ul>'
    )


def canonical_tag(url):
    if url:
        return f'<link rel="canonical" href="{html.escape(url)}">'
    return ""


def render_page(template, row, url):
    tool, competitor, use_case = (row[name] for name in REQUIRED_COLUMNS)
    values = {
        "ToolName": html.escape(tool),
        "Competitor": html.escape(competitor),
        "UseCases": html.escape(use_case),
        "PageTitle": html.escape(f"{tool} vs {competitor} for {use_case}"),
        "Description": html.escape(
            f"Compare {tool} and {competitor} for {use_case.lower()} "
            "with a practical side-by-side trial and evaluation checklist."
        ),
        "Canonical": canonical_tag(url),
        "AIGeneratedContent": comparison_content(row),
    }
    # Substitute in a single pass so CSV text is never interpreted as template syntax.
    return TOKEN.sub(lambda match: values[match.group(1)], template)


def render_home(pages, base_url):
    links = []
    for slug, row in sorted(pages.items()):
        tool, competitor, use_case = (row[name] for name in REQUIRED_COLUMNS)
        links.append(
            '<li class="rounded-xl border border-slate-700 bg-slate-900 p-5">'
            f'<a class="font-semibold text-teal-300 underline underline-offset-4" href="{slug}/">'
            f"{html.escape(f'{tool} vs {competitor}')}</a>"
            f'<p class="mt-2 text-sm text-slate-300">{html.escape(use_case)}</p></li>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Software comparison guides</title>
  <meta name="description" content="Practical trial plans for comparing productivity tools.">
  {canonical_tag(base_url)}
  <script src="{TAILWIND}"></script>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100 antialiased">
  <main class="mx-auto max-w-4xl px-5 py-10 sm:px-8 sm:py-16">
    <h1 class="text-4xl font-bold tracking-tight sm:text-6xl">Software comparison guides</h1>
    <p class="mt-4 text-lg text-slate-300">Choose a workflow and run a side-by-side trial.</p>
    <ul class="mt-10 grid gap-4 sm:grid-cols-2">{''.join(links)}</ul>
  </main>
</body>
</html>
"""


def write_sitemap(output, base_url, slugs):
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in ["", *(f"{slug}/" for slug in sorted(slugs))]:
        ET.SubElement(ET.SubElement(root, "url"), "loc").text = base_url + path
    ET.indent(root)
    ET.ElementTree(root).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def build(dataset, base_url):
    if base_url:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.query
            or parsed.fragment
            or any(char.isspace() for char in base_url)
        ):
            raise ValueError("--base-url must be an absolute HTTP(S) URL with no query or fragment.")
        base_url = base_url.rstrip("/") + "/"

    pages = load_rows(dataset)
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    missing = {"ToolName", "Competitor", "UseCases", "AIGeneratedContent"} - set(TOKEN.findall(template))
    if missing:
        raise ValueError(f"Missing template placeholders: {', '.join(sorted(missing))}")
    destination = ROOT / "dist"
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError("dist must be a regular directory.")
    # Render everything first. A fresh output tree also removes deleted CSV rows.
    with tempfile.TemporaryDirectory(prefix=".pseo-", dir=ROOT) as temporary:
        staging = Path(temporary) / "site"
        staging.mkdir()
        for slug, row in pages.items():
            page = staging / slug
            page.mkdir()
            url = base_url + slug + "/" if base_url else ""
            (page / "index.html").write_text(render_page(template, row, url), encoding="utf-8")
        (staging / "index.html").write_text(render_home(pages, base_url), encoding="utf-8")
        if base_url:
            write_sitemap(staging, base_url, pages)
        backup = Path(temporary) / "previous"
        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
    return len(pages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset.csv")
    parser.add_argument("--base-url", default="", help="Public URL including the repository path")
    args = parser.parse_args()
    try:
        count = build(args.dataset, args.base_url)
    except (OSError, UnicodeError, ValueError, csv.Error, KeyError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(f"Built {count} comparison pages and a directory index in {ROOT / 'dist'}")


if __name__ == "__main__":
    main()
