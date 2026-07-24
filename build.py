import re
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

SRC_DIR = Path(".")
OUTPUT_PATH = Path("./Ediciones/Axiomas_de_una_Sociedad_Indiferente.md")

BOOK_TITLE = "Axiomas de una Sociedad Indiferente"
AUTHOR = "L.R. Heredia"

INPUT_FILES = [
    "1. En materia de poder.md",
    "2. En materia de capital.md",
    "3. En materia de sociedad.md",
    "4. En materia de devoción.md",
    "5. En materia de realidad.md",
    "6. En materia de futuro.md",
    "A. Estructura.md",
]

INCLUDE_INDEX = True

BR_COUNTS = {1: 4, 
             2: 3, 
             3: 2, 
             4: 1}

# ═══════════════════════════════════════════════════════════════════
# De aquí a abajo no se toca
# ═══════════════════════════════════════════════════════════════════

OBSIDIAN_COMMENT = re.compile(r"%%.*?%%(\s*\[(?:Pull|ToDo)[^\]]*\])?", re.DOTALL)
HEADING_LINE = re.compile(r"^(#{1,4}) (.*)$")
EPIGRAPH_LINE = re.compile(r"^##### (.*)$")
FILENAME_PATTERN = re.compile(r"^([0-9]+|[A-Za-z]+)[.\s_]+(.+?)\.md$")

ROMAN = [
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def to_roman(n: int) -> str:
    result = ""
    for value, symbol in ROMAN:
        while n >= value:
            result += symbol
            n -= value
    return result


def parse_filename(filename: str):
    """'1. En materia de poder.md' -> ('parte', 'I', 'En materia de poder')"""
    m = FILENAME_PATTERN.match(filename)
    if not m:
        raise ValueError(f"No pude interpretar el nombre de archivo: {filename!r}")
    ident, title = m.group(1), m.group(2)
    if ident.isdigit():
        return "Parte", to_roman(int(ident)), title
    return "Apéndice", ident.upper(), title


def strip_obsidian_comments(text: str) -> str:
    text = OBSIDIAN_COMMENT.sub("", text)
    return re.sub(r"\n{3,}", "\n\n\n", text)


def compute_level_map(lines):
    """Comprime los niveles de encabezado usados (sin #####) y los reubica
    empezando en 2, para que el nivel más alto del archivo quede en '##'."""
    levels = {len(m.group(1)) for ln in lines if (m := HEADING_LINE.match(ln))}
    return {orig: rank + 2 for rank, orig in enumerate(sorted(levels))}


def convert_body(raw: str) -> str:
    """Aplica: strip de comentarios, remapeo de encabezados y conversión
    de epígrafes (#####) a blockquote."""
    raw = strip_obsidian_comments(raw)
    lines = raw.split("\n")
    level_map = compute_level_map(lines)

    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]

        m_epi = EPIGRAPH_LINE.match(line)
        if m_epi:
            quote = m_epi.group(1).strip()
            attribution = None
            if i + 1 < n and lines[i + 1].startswith("- "):
                attribution = lines[i + 1][2:].strip()
                i += 1
            out.append(f"> {quote}")
            if attribution:
                out.append(">")
                out.append(f"> — {attribution}")
            i += 1
            continue

        m_h = HEADING_LINE.match(line)
        if m_h:
            new_level = level_map[len(m_h.group(1))]
            out.append("#" * new_level + " " + m_h.group(2))
            i += 1
            continue

        out.append(line)
        i += 1

    return "\n".join(out).strip("\n")


def insert_line_breaks(text: str) -> str:
    """Antepone <br> x BR_COUNTS[nivel] a cada encabezado de nivel 2-4."""
    patterns = {lvl: re.compile(rf"^{'#' * lvl}(?!#) ") for lvl in (2, 3, 4)}
    out = []
    for line in text.split("\n"):
        level = next((lvl for lvl, pat in patterns.items() if pat.match(line)), None)
        if level:
            while out and out[-1] == "":
                out.pop()
            out.append("")
            out.extend(["<br>"] * BR_COUNTS[level])
            out.append("")
        out.append(line)
    return "\n".join(out)


def build_section(filename: str) -> tuple[str, str]:
    """Devuelve (bloque_markdown, encabezado_h2_para_indice) para un archivo."""
    kind, number, title = parse_filename(filename)
    raw = (SRC_DIR / filename).read_text(encoding="utf-8")
    body = convert_body(raw)

    heading_text = f"{number}. {title}" if kind == "Parte" else f"{kind} {number}. {title}"
    top = (
        "<!-- ═══════════════════════════════════════════════════════════════\n"
        f"     {kind.upper()} {number} — {title.upper()}\n"
        f"     Fuente original: {filename}\n"
        "     ═══════════════════════════════════════════════════════════════ -->\n"
        '<div style="page-break-before: always;"></div>\n\n'
        + "<br>\n" * BR_COUNTS[1] + "\n"
        + f"# {heading_text}\n\n{body}\n\n"
        + "<!-- ═══════════════════════════════════════════════════════════════\n"
        f"     FIN {kind.upper()} {number} — {title.upper()}\n"
        "     ═══════════════════════════════════════════════════════════════ -->\n"
    )
    return insert_line_breaks(top), heading_text


def build_cover() -> str:
    return (
        "<!-- ═══════════════════════════════════════════════════════════════\n"
        f"     {BOOK_TITLE.upper()}\n"
        f"     {AUTHOR}\n"
        "     Markdown unificado para publicación (listo para exportar a PDF / EPUB)\n"
        "     ═══════════════════════════════════════════════════════════════ -->\n\n"
        '<div style="page-break-after: always;"></div>\n\n'
        '<div align="center">\n\n<br><br><br><br>\n\n'
        f"# {BOOK_TITLE.upper()}\n\n<br>\n\n### {AUTHOR}\n\n</div>\n\n"
        '<div style="page-break-after: always;"></div>\n'
    )


def build_index(entries) -> str:
    """entries: lista de (heading_text_parte, [heading_text_capitulo, ...])"""
    lines = ["# Índice", ""]
    for part_heading, chapters in entries:
        lines.append(f"- **[[#{part_heading}]]**")
        for ch in chapters:
            lines.append(f"    - [[#{ch}]]")
    body = "\n".join(lines)
    return (
        "<!-- ═══════════════════════════════════════════════════════════════\n"
        "     ÍNDICE\n"
        "     (enlaces internos de Obsidian: [[#Encabezado]] — funcionan al\n"
        "     hacer clic manteniendo Ctrl/Cmd dentro de la app)\n"
        "     ═══════════════════════════════════════════════════════════════ -->\n"
        '<div style="page-break-before: always;"></div>\n\n'
        + "<br>\n" * BR_COUNTS[1] + "\n"
        + body
        + '\n\n<div style="page-break-after: always;"></div>\n'
    )


def extract_chapter_headings(section_block: str):
    return re.findall(r"^## (.*)$", section_block, flags=re.MULTILINE)


def main():
    sections, toc_entries = [], []
    for filename in INPUT_FILES:
        block, part_heading = build_section(filename)
        sections.append(block)
        if INCLUDE_INDEX:
            toc_entries.append((part_heading, extract_chapter_headings(block)))

    parts = [build_cover()]
    if INCLUDE_INDEX:
        parts.append(build_index(toc_entries))
    parts.extend(sections)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n\n".join(p.strip("\n") for p in parts) + "\n", encoding="utf-8")
    print(f"Listo: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()