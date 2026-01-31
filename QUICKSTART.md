# Quick Start Guide: Gradio PDF-to-HTML App

## Launch the App

### Option 1: Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
python gradio_app.py
```

The app will open at: **http://localhost:7860**

### Option 2: System-Wide Gradio

```bash
# Install Gradio globally
pip install gradio

# Launch the app
python gradio_app.py
```

---

## Features

### Drag and Drop
- Upload PDF files directly
- Convert with custom settings
- Live HTML preview

### Batch Processing
- Select a folder containing multiple PDFs
- Convert entire directory at once
- Progress tracking

### Custom Options
- **Body content only**: Skip table of contents generation
- **No Table of Contents**: Don't generate TOC
- **Themes**: Choose between "modern" (default) and "minimal"

### Output
- Live HTML preview in browser
- Download converted file
- Copy CLI command for automation

---

## Deployment (Vercel)

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Deploy

```bash
# Navigate to output directory
cd out

# Deploy to Vercel
vercel --prod
```

Your site will be live at a URL displayed by Vercel (e.g., `https://your-project.vercel.app`).

---

## Tips

1. **No local server needed** — Vercel handles hosting automatically
2. **Static HTML** — Works perfectly for SEO and AI search references
3. **Drag and drop** — Easier than command-line file paths
4. **Live preview** — See results instantly in browser
5. **Batch processing** — Convert entire folders at once

---

## Troubleshooting

### Gradio not installed
```bash
pip install gradio
```

### Port 7860 already in use
```bash
# Launch on a different port
python gradio_app.py --server-port 7861
```

### Permissions error
```bash
# Make script executable
chmod +x gradio_app.py
```

---

**Enjoy converting your PDFs!** 🚀
