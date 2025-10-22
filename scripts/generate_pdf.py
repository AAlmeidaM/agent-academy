#!/usr/bin/env python3
"""Generate a PDF that contains the full text content of the Agent Academy site."""

import os
import re
import textwrap
from typing import List, Sequence, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_ROOT = os.path.join(REPO_ROOT, "docs")
OUTPUT_PDF = os.path.join(REPO_ROOT, "Copilot-Studio-Agent-Academy.pdf")

NAV_STRUCTURE: Sequence[Tuple[str, Sequence[Tuple[str, str]]]] = (
    ("Home", (("Home", "index.md"),)),
    (
        "Recruit",
        (
            ("Welcome", "recruit/README.md"),
            ("Course Setup", "recruit/00-course-setup/README.md"),
            ("Introduction to Agents", "recruit/01-introduction-to-agents/README.md"),
            ("Copilot Studio Fundamentals", "recruit/02-copilot-studio-fundamentals/README.md"),
            ("Create Declarative Agent", "recruit/03-create-a-declarative-agent-for-M365Copilot/README.md"),
            ("Create a Solution", "recruit/04-creating-a-solution/README.md"),
            ("Use Prebuilt Agents", "recruit/05-using-prebuilt-agents/README.md"),
            ("Create Agent from Conversation", "recruit/06-create-agent-from-conversation/README.md"),
            ("Add New Topic with Trigger", "recruit/07-add-new-topic-with-trigger/README.md"),
            ("Add Adaptive Card", "recruit/08-add-adaptive-card/README.md"),
            ("Add Agent Flow", "recruit/09-add-an-agent-flow/README.md"),
            ("Add Event Triggers", "recruit/10-add-event-triggers/README.md"),
            ("Publish Your Agent", "recruit/11-publish-your-agent/README.md"),
            ("Understanding Licensing", "recruit/12-understanding-licensing/README.md"),
            ("Secure Your Badge", "recruit/course-completion-badges-recruit/README.md"),
        ),
    ),
    ("Operative", (("Operative (Coming Soon)", "operative/README.md"),)),
    ("Commander", (("Commander (Coming Soon)", "commander/README.md"),)),
)

HEADER_WIDTH = 90
PDF_WIDTH = 612
PDF_HEIGHT = 792
MARGIN_LEFT = 72
MARGIN_TOP = 72
FONT_SIZE = 12
LEADING = 14


def read_markdown(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()


def strip_front_matter(md: str) -> str:
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            return md[end + 4 :]
    return md


def markdown_to_text(md: str) -> str:
    text = strip_front_matter(md)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<img[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"^!!!.*", "", text, flags=re.M)
    text = re.sub(r"^\s{4}", "", text, flags=re.M)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def wrap_paragraph(text: str, width: int) -> List[str]:
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)


def wrap_lines(raw_text: str, width: int) -> List[str]:
    lines: List[str] = []
    paragraph: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            joined = " ".join(part.strip() for part in paragraph if part.strip())
            if joined:
                lines.extend(wrap_paragraph(joined, width))
                lines.append("")
            paragraph.clear()

    for raw_line in raw_text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            flush_paragraph()
            if lines and lines[-1] != "":
                lines.append("")
            elif not lines:
                lines.append("")
            continue

        bullet_match = re.match(r"^(\s*)([-*+]\s+)(.*)", raw_line)
        numbered_match = re.match(r"^(\s*)(\d+\.[\)\.]?\s+)(.*)", raw_line)
        if raw_line.startswith("    ") and not bullet_match and not numbered_match:
            flush_paragraph()
            lines.append(raw_line)
            continue

        if bullet_match:
            flush_paragraph()
            indent, prefix, body = bullet_match.groups()
            wrapped = textwrap.wrap(
                body.strip(),
                width=width,
                initial_indent=f"{indent}{prefix}",
                subsequent_indent=f"{indent}{' ' * len(prefix)}",
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.extend(wrapped)
            continue

        if numbered_match:
            flush_paragraph()
            indent, prefix, body = numbered_match.groups()
            wrapped = textwrap.wrap(
                body.strip(),
                width=width,
                initial_indent=f"{indent}{prefix}",
                subsequent_indent=f"{indent}{' ' * len(prefix)}",
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.extend(wrapped)
            continue

        paragraph.append(raw_line)

    flush_paragraph()

    while lines and lines[-1] == "":
        lines.pop()
    return lines


def sanitize_for_pdf(text: str) -> str:
    return "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in text)


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def chunk_lines(lines: Sequence[str], lines_per_page: int) -> List[List[str]]:
    pages: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if len(current) >= lines_per_page:
            pages.append(current)
            current = []
        current.append(line)
    if current:
        pages.append(current)
    return pages


def build_page_stream(lines: Sequence[str]) -> bytes:
    commands: List[str] = [
        "BT",
        f"/F1 {FONT_SIZE} Tf",
        f"{LEADING} TL",
        f"1 0 0 1 {MARGIN_LEFT} {PDF_HEIGHT - MARGIN_TOP} Tm",
    ]
    first_line = True
    for line in lines:
        safe_line = escape_pdf_text(sanitize_for_pdf(line))
        if first_line:
            commands.append(f"({safe_line}) Tj")
            first_line = False
            continue
        commands.append("T*")
        if safe_line:
            commands.append(f"({safe_line}) Tj")
    commands.append("ET")
    stream_text = "\n".join(commands) + "\n"
    content = f"<< /Length {len(stream_text.encode('utf-8'))} >>\nstream\n{stream_text}endstream"
    return content.encode("utf-8")


def assemble_pdf(pages: Sequence[Sequence[str]]) -> bytes:
    num_pages = len(pages)
    content_streams = [build_page_stream(page) for page in pages]
    objects: List[bytes] = []

    # 1: Catalog (references Pages object 2)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    # 2: Pages
    kids = " ".join(f"{3 + idx} 0 R" for idx in range(num_pages))
    pages_obj = f"<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>".encode("utf-8")
    objects.append(pages_obj)

    # Page objects
    for page_index in range(num_pages):
        content_ref = 3 + num_pages + page_index
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PDF_WIDTH} {PDF_HEIGHT}] "
            f"/Contents {content_ref} 0 R /Resources << /Font << /F1 {3 + 2 * num_pages} 0 R >> >> >>"
        ).encode("utf-8")
        objects.append(page_obj)

    # Content stream objects
    objects.extend(content_streams)

    # Font object (Helvetica)
    font_obj = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects.append(font_obj)

    # Assemble PDF
    result = bytearray()
    result.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode("utf-8"))
        result.extend(obj)
        if not obj.endswith(b"\n"):
            result.extend(b"\n")
        result.extend(b"endobj\n")
    xref_position = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    result.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    result.extend(b"trailer\n")
    result.extend(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("utf-8"))
    result.extend(f"startxref\n{xref_position}\n%%EOF".encode("utf-8"))
    return bytes(result)


def build_document_lines() -> List[str]:
    all_lines: List[str] = []
    for section_title, pages in NAV_STRUCTURE:
        section_header = section_title.strip()
        if section_header:
            all_lines.append(section_header)
            all_lines.append("=" * len(section_header))
            all_lines.append("")
        for page_title, relative_path in pages:
            markdown_path = os.path.join(DOCS_ROOT, relative_path)
            if not os.path.exists(markdown_path):
                continue
            all_lines.append(page_title.strip())
            all_lines.append("-" * len(page_title.strip()))
            all_lines.append("")
            raw_markdown = read_markdown(markdown_path)
            text_content = markdown_to_text(raw_markdown)
            if text_content:
                wrapped_lines = wrap_lines(text_content, HEADER_WIDTH)
                all_lines.extend(wrapped_lines)
                all_lines.append("")
    while all_lines and all_lines[-1] == "":
        all_lines.pop()
    return all_lines


def main() -> None:
    lines = build_document_lines()
    lines_per_page = int((PDF_HEIGHT - 2 * MARGIN_TOP) / LEADING)
    pages = chunk_lines(lines, lines_per_page)
    pdf_bytes = assemble_pdf(pages)
    with open(OUTPUT_PDF, "wb") as fp:
        fp.write(pdf_bytes)
    print(f"PDF generated at: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
