"""Extract an email (.eml) message and save its content as a Markdown document."""

from __future__ import annotations

import argparse
import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify


def _strip_layout_tables(html: str) -> str:
    """Unwrap table markup so markdownify emits flowing text instead of layout-table noise."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["table", "tbody", "thead", "tfoot", "tr", "td", "th"]):
        tag.unwrap()
    return str(soup)


def _clean_markdown(text: str) -> str:
    """Collapse excess blank lines left behind after stripping layout markup."""
    return re.sub(r"\n{3,}", "\n\n", text)


def _decode_body(msg: EmailMessage) -> tuple[str, str]:
    """Return (body_markdown, content_type) preferring plain text, falling back to HTML."""
    plain_part = msg.get_body(preferencelist=("plain",))
    if plain_part is not None:
        return plain_part.get_content().strip(), "text/plain"

    html_part = msg.get_body(preferencelist=("html",))
    if html_part is not None:
        html = _strip_layout_tables(html_part.get_content())
        markdown = markdownify(html, heading_style="ATX").strip()
        return _clean_markdown(markdown), "text/html"

    return "", "text/plain"


def _extract_attachment_names(msg: EmailMessage) -> list[str]:
    return [
        part.get_filename() or "unnamed-attachment"
        for part in msg.iter_attachments()
    ]


def eml_to_markdown(eml_path: str | Path) -> str:
    """Parse an .eml file and render its headers and body as a Markdown string."""
    eml_path = Path(eml_path)
    with eml_path.open("rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    subject = msg.get("Subject", "(no subject)")
    sender = msg.get("From", "(unknown sender)")
    to = msg.get("To", "")
    cc = msg.get("Cc", "")
    date_header = msg.get("Date", "")
    try:
        date_str = parsedate_to_datetime(date_header).isoformat() if date_header else ""
    except (TypeError, ValueError):
        date_str = date_header

    body, _ = _decode_body(msg)
    attachments = _extract_attachment_names(msg)

    lines = [f"# {subject}", ""]
    lines.append(f"- **From:** {sender}")
    lines.append(f"- **To:** {to}")
    if cc:
        lines.append(f"- **Cc:** {cc}")
    lines.append(f"- **Date:** {date_str}")
    if attachments:
        lines.append(f"- **Attachments:** {', '.join(attachments)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(body)

    return "\n".join(lines) + "\n"


def convert_file(eml_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Convert an .eml file to a .md file and return the output path."""
    eml_path = Path(eml_path)
    if output_path is None:
        output_path = eml_path.with_suffix(".md")
    output_path = Path(output_path)

    markdown = eml_to_markdown(eml_path)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eml_file", help="Path to the .eml file to convert")
    parser.add_argument(
        "-o", "--output", help="Path to the output .md file (defaults to same name with .md extension)"
    )
    args = parser.parse_args()

    output_path = convert_file(args.eml_file, args.output)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
