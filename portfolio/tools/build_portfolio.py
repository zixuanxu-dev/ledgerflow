from __future__ import annotations

import math
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "screenshots" / "raw"
IMAGES = ROOT / "images"
PDF_OUTPUT = ROOT / "output" / "pdf"

NAVY = "#101B31"
NAVY_2 = "#192842"
LIME = "#CDFF5B"
INK = "#111A2B"
MUTED = "#697386"
PAPER = "#F5F6F1"
WHITE = "#FFFFFF"
MINT = "#A8F0D8"
AMBER = "#FFD58C"
PURPLE = "#D9CDFF"

FONT_REGULAR = Path("C:/Windows/Fonts/arial.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def hex_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def fit_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_width, target_height = size
    source_ratio = image.width / image.height
    target_ratio = target_width / target_height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        image = image.crop((left, 0, left + crop_width, image.height))
    else:
        crop_height = round(image.width / target_ratio)
        top = max(0, (image.height - crop_height) // 2)
        image = image.crop((0, top, image.width, top + crop_height))
    return image.resize(size, Image.Resampling.LANCZOS)


def rounded_paste(
    canvas_image: Image.Image,
    source: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    shadow: bool = True,
) -> None:
    x, y, width, height = box
    if shadow:
        shadow_layer = Image.new("RGBA", canvas_image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_draw.rounded_rectangle(
            (x + 8, y + 12, x + width + 8, y + height + 12),
            radius=radius,
            fill=(16, 27, 49, 55),
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(14))
        canvas_image.alpha_composite(shadow_layer)

    fitted = fit_image(source.convert("RGB"), (width, height)).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width, height), radius=radius, fill=255)
    canvas_image.paste(fitted, (x, y), mask)


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    line_gap: int = 7,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    line_height = text_font.size + line_gap
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, font=text_font, fill=fill)
    return y + len(lines) * line_height


def chip(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    fill: str,
    text_fill: str = INK,
) -> int:
    x, y = xy
    chip_font = font(17, bold=True)
    width = draw.textbbox((0, 0), label, font=chip_font)[2] + 34
    draw.rounded_rectangle((x, y, x + width, y + 36), radius=18, fill=fill)
    draw.text((x + 17, y + 8), label, font=chip_font, fill=text_fill)
    return width


def base_slide(index: str, eyebrow: str, title: str, subtitle: str) -> Image.Image:
    image = Image.new("RGBA", (1000, 750), hex_color(PAPER) + (255,))
    draw = ImageDraw.Draw(image)
    draw.text((58, 42), eyebrow.upper(), font=font(15, bold=True), fill=hex_color(MUTED))
    draw.text((58, 72), title, font=font(38, bold=True), fill=hex_color(INK))
    draw_wrapped(draw, subtitle, (58, 126), 760, font(18), MUTED, 5)
    draw.rounded_rectangle((890, 44, 942, 78), radius=17, fill=hex_color(NAVY))
    draw.text((907, 53), index, font=font(14, bold=True), fill=hex_color(WHITE))
    return image


def make_cover() -> None:
    image = Image.new("RGBA", (1000, 750), hex_color(NAVY) + (255,))
    draw = ImageDraw.Draw(image)
    draw.ellipse((720, -160, 1080, 200), fill=hex_color(NAVY_2))
    draw.ellipse((790, -90, 1010, 130), outline=hex_color(LIME), width=2)

    draw.rounded_rectangle((60, 52, 116, 108), radius=15, fill=hex_color(LIME))
    draw.rounded_rectangle((76, 67, 101, 73), radius=3, fill=hex_color(NAVY))
    draw.rounded_rectangle((73, 78, 96, 84), radius=3, fill=hex_color(NAVY))
    draw.rounded_rectangle((70, 89, 91, 95), radius=3, fill=hex_color(NAVY))
    draw.text((134, 58), "LedgerFlow", font=font(31, bold=True), fill=hex_color(WHITE))
    draw.text((136, 94), "DOCUMENT OPERATIONS", font=font(13, bold=True), fill=(164, 176, 198))

    draw.text((60, 146), "Human-controlled", font=font(45, bold=True), fill=hex_color(WHITE))
    draw.text((60, 197), "document workflows.", font=font(45, bold=True), fill=hex_color(LIME))
    draw_wrapped(
        draw,
        "A full-stack SaaS MVP for recurring document collection, confidence-based review, and auditable operations.",
        (62, 255),
        840,
        font(19),
        "#C7CFDD",
        6,
    )

    chip_x = 62
    for label, fill in [
        ("Vue 3", MINT),
        ("TypeScript", PURPLE),
        ("FastAPI", LIME),
        ("SQLAlchemy", AMBER),
    ]:
        chip_x += chip(draw, (chip_x, 324), label, fill) + 10

    screenshot = Image.open(RAW / "01-overview.jpg")
    rounded_paste(image, screenshot, (80, 396, 840, 300), radius=18, shadow=True)
    draw.rounded_rectangle((80, 396, 920, 696), radius=18, outline=(255, 255, 255, 65), width=2)
    image.convert("RGB").save(IMAGES / "01-cover.jpg", quality=96, subsampling=0)


def make_screenshot_slide(
    filename: str,
    index: str,
    eyebrow: str,
    title: str,
    subtitle: str,
    source: str,
    footer: str,
) -> None:
    image = base_slide(index, eyebrow, title, subtitle)
    screenshot = Image.open(RAW / source)
    rounded_paste(image, screenshot, (55, 190, 890, 500), radius=18, shadow=True)
    draw = ImageDraw.Draw(image)
    draw.ellipse((58, 715, 68, 725), fill=hex_color(LIME))
    draw.text((78, 708), footer, font=font(15, bold=True), fill=hex_color(MUTED))
    image.convert("RGB").save(IMAGES / filename, quality=96, subsampling=0)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if not length:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head_length = 15
    head_half_width = 9
    base_x = ex - ux * head_length
    base_y = ey - uy * head_length
    points = [
        (ex, ey),
        (base_x + px * head_half_width, base_y + py * head_half_width),
        (base_x - px * head_half_width, base_y - py * head_half_width),
    ]
    draw.line((sx, sy, ex, ey), fill=hex_color("#93A0B4"), width=4)
    draw.polygon(points, fill=hex_color("#93A0B4"))


def architecture_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    eyebrow: str,
    title: str,
    detail: str,
    accent: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=hex_color(WHITE), outline=hex_color("#E0E3DC"), width=2)
    draw.rounded_rectangle((x1 + 18, y1 + 18, x1 + 54, y1 + 54), radius=10, fill=hex_color(accent))
    draw.text((x1 + 29, y1 + 25), "•", font=font(21, bold=True), fill=hex_color(NAVY))
    draw.text((x1 + 68, y1 + 20), eyebrow.upper(), font=font(12, bold=True), fill=hex_color(MUTED))
    draw.text((x1 + 20, y1 + 67), title, font=font(21, bold=True), fill=hex_color(INK))
    draw_wrapped(draw, detail, (x1 + 20, y1 + 100), x2 - x1 - 40, font(14), MUTED, 4)


def make_architecture() -> None:
    image = base_slide(
        "06",
        "System design",
        "A production-minded MVP architecture",
        "Clear boundaries make the local demo easy to run while leaving practical paths to PostgreSQL, S3, OCR, and background workers.",
    )
    draw = ImageDraw.Draw(image)

    architecture_card(draw, (55, 210, 295, 370), "Frontend", "Vue 3 dashboard", "Typed UI, responsive views, and review actions.", MINT)
    architecture_card(draw, (380, 210, 620, 370), "Application", "FastAPI REST API", "Validation, workflow orchestration, and exports.", LIME)
    architecture_card(draw, (705, 210, 945, 370), "State", "SQLAlchemy layer", "Requirements, documents, reminders, and clients.", AMBER)
    arrow(draw, (305, 290), (368, 290))
    arrow(draw, (630, 290), (693, 290))

    architecture_card(draw, (80, 455, 330, 620), "Intake", "Document parser", "PDF, DOCX, structured text, hashing, and confidence scoring.", PURPLE)
    architecture_card(draw, (375, 455, 625, 620), "Control", "Review and audit", "Human approval gates and actor-stamped workflow events.", LIME)
    architecture_card(draw, (670, 455, 920, 620), "Persistence", "SQLite + files", "Portable demo storage with PostgreSQL and S3-ready boundaries.", MINT)
    arrow(draw, (455, 370), (205, 450))
    arrow(draw, (500, 370), (500, 450))
    arrow(draw, (820, 370), (795, 450))

    x = 158
    for label in ["Duplicate detection", "24h reminder guard", "CSV export", "Automated tests"]:
        width = chip(draw, (x, 674), label, "#E8EBE4", MUTED)
        x += width + 9
    image.convert("RGB").save(IMAGES / "06-architecture.jpg", quality=96, subsampling=0)


def register_pdf_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Arial", str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_BOLD)))


def pdf_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    size: float,
    color: str,
    bold: bool = False,
    leading: float | None = None,
) -> float:
    font_name = "Arial-Bold" if bold else "Arial"
    leading = leading or size * 1.35
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(candidate, font_name, size) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    pdf.setFont(font_name, size)
    pdf.setFillColor(HexColor(color))
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def pdf_footer(pdf: canvas.Canvas, page: int) -> None:
    pdf.setStrokeColor(HexColor("#DDE1D9"))
    pdf.line(42, 34, 553, 34)
    pdf.setFont("Arial", 8)
    pdf.setFillColor(HexColor(MUTED))
    pdf.drawString(42, 20, "LedgerFlow - Independent portfolio project - Synthetic demo data")
    pdf.drawRightString(553, 20, f"{page} / 3")


def pdf_card(pdf: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, body: str, accent: str) -> None:
    pdf.setFillColor(HexColor(WHITE))
    pdf.setStrokeColor(HexColor("#DFE3DA"))
    pdf.roundRect(x, y, w, h, 10, fill=1, stroke=1)
    pdf.setFillColor(HexColor(accent))
    pdf.roundRect(x + 16, y + h - 35, 22, 22, 6, fill=1, stroke=0)
    pdf.setFillColor(HexColor(INK))
    pdf.setFont("Arial-Bold", 12)
    pdf.drawString(x + 48, y + h - 30, title)
    pdf_wrapped(pdf, body, x + 16, y + h - 58, w - 32, 9, MUTED, leading=13)


def make_pdf() -> None:
    register_pdf_fonts()
    output = PDF_OUTPUT / "ledgerflow-case-study.pdf"
    pdf = canvas.Canvas(str(output), pagesize=A4)
    pdf.setTitle("LedgerFlow - Document Workflow SaaS Case Study")
    pdf.setAuthor("LedgerFlow portfolio project")
    pdf.setSubject("Full-stack document collection and human review workflow")
    width, height = A4

    # Page 1 - product cover
    pdf.setFillColor(HexColor(NAVY))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(HexColor(LIME))
    pdf.roundRect(42, height - 92, 38, 38, 10, fill=1, stroke=0)
    pdf.setFillColor(HexColor(WHITE))
    pdf.setFont("Arial-Bold", 24)
    pdf.drawString(94, height - 78, "LedgerFlow")
    pdf.setFillColor(HexColor("#9FAEC5"))
    pdf.setFont("Arial-Bold", 8)
    pdf.drawString(95, height - 94, "DOCUMENT OPERATIONS")
    pdf.setFillColor(HexColor(WHITE))
    pdf.setFont("Arial-Bold", 36)
    pdf.drawString(42, height - 170, "Human-controlled")
    pdf.setFillColor(HexColor(LIME))
    pdf.drawString(42, height - 214, "document workflows.")
    pdf_wrapped(
        pdf,
        "A full-stack SaaS MVP for recurring document collection, confidence-based review, and auditable operations.",
        42,
        height - 250,
        500,
        13,
        "#C7CFDD",
        leading=18,
    )
    pdf.drawImage(ImageReader(str(RAW / "01-overview.jpg")), 42, 272, width=511, height=288, preserveAspectRatio=True, mask="auto")
    pdf.setFillColor(HexColor("#17253E"))
    pdf.roundRect(42, 126, 511, 104, 12, fill=1, stroke=0)
    pdf.setFillColor(HexColor(WHITE))
    pdf.setFont("Arial-Bold", 11)
    pdf.drawString(60, 202, "ROLE")
    pdf.drawString(230, 202, "CORE STACK")
    pdf.drawString(438, 202, "PROJECT TYPE")
    pdf.setFillColor(HexColor("#C7CFDD"))
    pdf.setFont("Arial", 9)
    pdf.drawString(60, 181, "Full-Stack Developer")
    pdf.drawString(60, 164, "Product Engineer")
    pdf.drawString(230, 181, "Vue 3, TypeScript")
    pdf.drawString(230, 164, "FastAPI, SQLAlchemy")
    pdf.drawString(438, 181, "Independent MVP")
    pdf.drawString(438, 164, "Synthetic data")
    pdf.setFont("Arial", 8)
    pdf.drawCentredString(width / 2, 48, "Case study prepared for freelance portfolio review")
    pdf.showPage()

    # Page 2 - problem, solution, workflow, architecture
    pdf.setFillColor(HexColor(PAPER))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(HexColor(MUTED))
    pdf.setFont("Arial-Bold", 8)
    pdf.drawString(42, height - 50, "CASE STUDY")
    pdf.setFillColor(HexColor(INK))
    pdf.setFont("Arial-Bold", 24)
    pdf.drawString(42, height - 82, "From inbox chaos to controlled workflow")
    pdf_card(
        pdf,
        42,
        height - 250,
        246,
        130,
        "The challenge",
        "Recurring client documents arrive through fragmented channels. Teams need to know what is missing, what is late, and which extracted values still require human verification.",
        AMBER,
    )
    pdf_card(
        pdf,
        307,
        height - 250,
        246,
        130,
        "The solution",
        "LedgerFlow centralizes requirements and uploads, scores extraction confidence, prevents duplicate intake, routes uncertain data to review, and records every workflow decision.",
        LIME,
    )
    pdf.setFillColor(HexColor(INK))
    pdf.setFont("Arial-Bold", 13)
    pdf.drawString(42, height - 287, "Core workflow")
    steps = [
        ("Define", "requirement"),
        ("Upload + hash",),
        ("Extract + score",),
        ("Human review",),
        ("Audit + export",),
    ]
    x = 42
    for index, label_lines in enumerate(steps, 1):
        pdf.setFillColor(HexColor(WHITE))
        pdf.setStrokeColor(HexColor("#DDE2D8"))
        pdf.roundRect(x, height - 350, 92, 42, 8, fill=1, stroke=1)
        pdf.setFillColor(HexColor(NAVY))
        pdf.circle(x + 14, height - 329, 8, fill=1, stroke=0)
        pdf.setFillColor(HexColor(WHITE))
        pdf.setFont("Arial-Bold", 7)
        pdf.drawCentredString(x + 14, height - 331, str(index))
        pdf.setFillColor(HexColor(INK))
        pdf.setFont("Arial-Bold", 7.5)
        if len(label_lines) == 1:
            pdf.drawString(x + 28, height - 332, label_lines[0])
        else:
            pdf.drawString(x + 28, height - 326, label_lines[0])
            pdf.drawString(x + 28, height - 338, label_lines[1])
        if index < len(steps):
            pdf.setStrokeColor(HexColor("#9BA6B8"))
            pdf.line(x + 92, height - 329, x + 103, height - 329)
        x += 103
    pdf.drawImage(ImageReader(str(IMAGES / "06-architecture.jpg")), 42, 67, width=511, height=383, preserveAspectRatio=True, mask="auto")
    pdf_footer(pdf, 2)
    pdf.showPage()

    # Page 3 - engineering evidence and boundaries
    pdf.setFillColor(HexColor(PAPER))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(HexColor(MUTED))
    pdf.setFont("Arial-Bold", 8)
    pdf.drawString(42, height - 50, "ENGINEERING EVIDENCE")
    pdf.setFillColor(HexColor(INK))
    pdf.setFont("Arial-Bold", 24)
    pdf.drawString(42, height - 82, "Built to be inspected, not just admired")
    pdf_wrapped(
        pdf,
        "The portfolio demonstrates a complete workflow and makes its MVP boundaries explicit. It does not claim production guarantees or real client outcomes.",
        42,
        height - 110,
        500,
        10,
        MUTED,
        leading=14,
    )

    pdf_card(pdf, 42, height - 300, 246, 140, "Workflow safeguards", "SHA-256 duplicate detection, 10 MB upload limit, file allowlist, confidence-based review routing, 24-hour reminder suppression, and auditable mutations.", MINT)
    pdf_card(pdf, 307, height - 300, 246, 140, "Verified delivery", "Ruff checks pass, four API workflow tests pass, Vue type checking and production build pass, and the main desktop and responsive interactions were browser-tested.", LIME)

    pdf.setFillColor(HexColor(NAVY))
    pdf.roundRect(42, height - 461, 511, 128, 12, fill=1, stroke=0)
    pdf.setFillColor(HexColor(WHITE))
    pdf.setFont("Arial-Bold", 12)
    pdf.drawString(60, height - 365, "MVP boundaries")
    boundaries = [
        "Images are accepted but routed to review because OCR is not bundled.",
        "Reminder delivery is simulated as a durable workflow record.",
        "SQLite and local files keep the public demo portable.",
        "Authentication and role controls are documented production steps.",
    ]
    y = height - 387
    pdf.setFont("Arial", 8.5)
    pdf.setFillColor(HexColor("#C7CFDD"))
    for item in boundaries:
        pdf.setFillColor(HexColor(LIME))
        pdf.circle(62, y + 3, 2.3, fill=1, stroke=0)
        pdf.setFillColor(HexColor("#C7CFDD"))
        pdf.drawString(72, y, item)
        y -= 18

    pdf.drawImage(ImageReader(str(IMAGES / "04-human-review.jpg")), 42, 56, width=511, height=287, preserveAspectRatio=True, mask="auto")
    pdf_footer(pdf, 3)
    pdf.save()


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    PDF_OUTPUT.mkdir(parents=True, exist_ok=True)
    make_cover()
    make_screenshot_slide(
        "02-dashboard.jpg",
        "02",
        "Operations overview",
        "Operational clarity, without blind automation",
        "A live collection cycle combines completion status, overdue work, review queues, and reminder history.",
        "01-overview.jpg",
        "Dashboard overview | Synthetic demo data",
    )
    make_screenshot_slide(
        "03-collections.jpg",
        "03",
        "Collection control",
        "Recurring requirements stay actionable",
        "Every expected document has a client, reporting period, due date, workflow state, and reminder history.",
        "02-collections.jpg",
        "Requirement tracking | Overdue and in-review states",
    )
    make_screenshot_slide(
        "04-human-review.jpg",
        "04",
        "Human-in-the-loop",
        "Low-confidence data waits for a human",
        "Extracted fields and routing metadata remain visible before a reviewer approves or rejects the document.",
        "04-human-review.jpg",
        "68% confidence | Manual confirmation required",
    )
    make_screenshot_slide(
        "05-audit.jpg",
        "05",
        "Accountability",
        "Every workflow decision is traceable",
        "Uploads, approvals, requirements, and reminders create an actor-and-timestamp audit record.",
        "05-audit.jpg",
        "Audit trail | Human and automated actions",
    )
    make_architecture()
    make_pdf()
    print(f"Created {len(list(IMAGES.glob('*.jpg')))} images and {PDF_OUTPUT / 'ledgerflow-case-study.pdf'}")


if __name__ == "__main__":
    main()
