# PDF to Semantic HTML

CLI script to convert PDFs (including scientific studies) into semantic HTML suitable for SEO and AI search references. The output is a clean HTML document with headings, TOC, figures, and schema.org JSON-LD.

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

**New!** Drag-and-drop web interface with live preview!

### Launch the App

```bash
# Make sure Gradio is installed
pip install gradio

# Launch the app
python gradio_app.py
```

The app will open at: **http://localhost:7860**

### Features

- 📤 **Drag and drop** - Upload PDF files directly
- 📁 **Batch processing** - Select a folder containing multiple PDFs
- 🎯 **Custom options** - Body-only, skip TOC, multiple themes
- 👁 **Live preview** - See results instantly in browser
- 📋 **Copy CLI** - Get the command for automation
- 🚀 **Deploy to Vercel** - One-click deployment instructions

### Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed Gradio setup and deployment instructions.

## Output

- `out/<pdf-name>/index.html` (batch mode)
- `out/<pdf-name>/images/` for extracted figures

## Notes

- The script uses PyMuPDF for text + image extraction and applies heuristics to infer headings and lists.
- If a PDF includes clear numbered headings (e.g., `1.`, `1.1`), those are mapped to structured HTML headings for better SEO.
- Image captions are recognized when a paragraph immediately follows a figure and starts with `Obr.`, `Fig.`, or `Figure`.
- For maximum semantic quality, provide metadata overrides or a JSON metadata file.
