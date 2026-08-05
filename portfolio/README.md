# LedgerFlow Portfolio Package

This folder contains the materials prepared for an Upwork portfolio item and a public GitHub repository.

## Ready-to-upload files

- `images/01-cover.jpg` - portfolio cover
- `images/02-dashboard.jpg` - operations overview
- `images/03-collections.jpg` - recurring requirement tracking
- `images/04-human-review.jpg` - confidence-based review
- `images/05-audit.jpg` - audit trail
- `images/06-architecture.jpg` - system architecture
- `output/pdf/ledgerflow-case-study.pdf` - three-page case study
- `UPWORK_COPY.md` - portfolio fields, captions, and proposal reference
- `GITHUB_COPY.md` - repository listing copy and publishing checklist
- `DEMO_VIDEO_SCRIPT.md` - 60-second walkthrough script

## Upload order

1. Create the portfolio item using `UPWORK_COPY.md`.
2. Upload the six JPG files in numbered order. Each is exactly 1000 x 750 pixels.
3. Add the case study PDF if the portfolio editor offers a document upload.
4. Publish the GitHub repository only after correcting the local Git identity.
5. Add a live demo URL later, after choosing a hosting setup.

## Positioning rule

Describe LedgerFlow as an independent portfolio project. Do not describe it as paid client work or claim business outcomes that have not been measured. All demo data is synthetic.

## Rebuild

Run the builder from the repository root with the bundled Python runtime or any Python environment that provides Pillow and ReportLab:

```powershell
python portfolio\tools\build_portfolio.py
```
