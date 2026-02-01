# PDF to Semantic HTML

CLI + Gradio app to convert PDFs (including scientific studies) into semantic HTML suitable for SEO and AI search references. Output includes headings, TOC, figures, and schema.org JSON-LD.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Single PDF

```bash
python scripts/pdf_to_semantic_html.py "/path/to/file.pdf" --out out
```

### Batch Directory

```bash
python scripts/pdf_to_semantic_html.py "/path/to/pdfs" --out out --batch --recursive
```

### Skip Images or TOC

```bash
python scripts/pdf_to_semantic_html.py file.pdf --out out --no-images
python scripts/pdf_to_semantic_html.py file.pdf --out out --no-toc
```

### Keep Original PDF TOC Pages

```bash
python scripts/pdf_to_semantic_html.py file.pdf --out out --keep-toc-pages
```

### Override Metadata

```bash
python scripts/pdf_to_semantic_html.py file.pdf \
  --out out \
  --title "My Study" \
  --author "Dr. Jane Doe" \
  --date "2025-11-01" \
  --lang "sk" \
  --publisher "Example Lab" \
  --description "Short abstract" \
  --keywords "EMI, electromobility"
```

### Metadata JSON (Optional)

```json
{
  "title": "My Study",
  "author": "Dr. Jane Doe",
  "date": "2025-11-01",
  "lang": "sk",
  "publisher": "Example Lab",
  "description": "Short abstract",
  "keywords": ["EMI", "electromobility"]
}
```

```bash
python scripts/pdf_to_semantic_html.py file.pdf --metadata metadata.json
```

## 🎨 Gradio Web App

Drag-and-drop web interface for single-file and batch conversion.

### Launch the App

```bash
# Make sure Gradio is installed
pip install gradio

# Launch the app
python gradio_app.py
```

The app will open at: **http://localhost:7860**

### Features

- 📤 **Single PDF upload** - Convert one uploaded PDF
- 📁 **Batch folder mode** - Convert all PDFs in a folder path
- ⚙️ **Options** - `--no-images`, `--no-toc`, `--keep-toc-pages`
- 📦 **Download support** - Returns HTML, or ZIP (HTML + images) when images exist
- 📝 **Detailed status logs** - Command output and errors shown in UI

### Quick Start

- Local app usage: [QUICKSTART.md](QUICKSTART.md)
- VPS/proxy deployment notes: [DEPLOYMENT.md](DEPLOYMENT.md)

### Production Environment Variables

The app supports reverse-proxy friendly runtime settings:

- `PUBLIC_ROOT_URL` (for public base URL, e.g. `https://pdf.zoid.bot`)
- `GRADIO_SERVER_NAME` (defaults to `0.0.0.0`)
- `GRADIO_ROOT_PATH` (optional root path)

Note: do not set `GRADIO_ROOT_PATH=/gradio_api` as app `root_path`; that path is used by Gradio internal API routes and can cause startup probe failures.

## Output

CLI output behavior:

- Single mode (default): `out/<pdf-name>.html`
- Single mode (`--out some/file.html`): writes exactly to that file
- Batch mode: `out/<pdf-name>/index.html`
- Extracted images: `<html-parent>/images/`

Gradio app behavior:

- Single upload: finds latest `<pdf-name>*.html` in output dir and exposes download
- If images exist next to HTML, download becomes `<pdf-name>_with_images.zip`
- Batch mode: reports generated files in status output (downloads are not bundled in batch tab)

## Notes

- The script uses PyMuPDF for text + image extraction and applies heuristics to infer headings and lists.
- If a PDF includes clear numbered headings (e.g., `1.`, `1.1`), those are mapped to structured HTML headings for better SEO.
- Image captions are recognized when a paragraph immediately follows a figure and starts with `Obr.`, `Fig.`, or `Figure`.
- For maximum semantic quality, provide metadata overrides or a JSON metadata file.
