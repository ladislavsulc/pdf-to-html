#!/usr/bin/env python3
"""Gradio Web App Wrapper for PDF-to-HTML Converter
Provides drag-and-drop interface for PyMuPDF-based converter.

Features:
- Drag and drop PDF upload
- Folder selection (batch mode)
- Custom flags (no-images, no-toc, keep-toc-pages)
- Progress tracking
- Live HTML preview
- Download converted files
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

try:
    import gradio as gr
    print(f"Gradio version: {gradio.__version__}")
except ImportError:
    print("Error: gradio not found. Install with: pip install gradio")
    sys.exit(1)

# Constants
DEFAULT_OUTPUT_DIR = "/home/clawdbot/clawd/pdf-to-html/out"
CONVERTER_SCRIPT = "/home/clawdbot/clawd/pdf-to-html-fork/scripts/pdf_to_semantic_html.py"

# Set up environment with user's site-packages
ENV = os.environ.copy()
USER_SITE = os.path.expanduser('~/.local/lib/python3.12/site-packages')
if 'PYTHONPATH' in ENV:
    ENV['PYTHONPATH'] = USER_SITE + ':' + ENV['PYTHONPATH']
else:
    ENV['PYTHONPATH'] = USER_SITE

# Global to track last converted file
LAST_CONVERTED_FILE = None

def convert_pdf(pdf_path, output_dir, no_images=False, no_toc=False, keep_toc_pages=False):
    """Run pdf_to_semantic_html.py with custom options."""
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    cmd = [sys.executable, CONVERTER_SCRIPT, pdf_path, "--out", output_dir]

    if no_images:
        cmd.append("--no-images")
    if no_toc:
        cmd.append("--no-toc")
    if keep_toc_pages:
        cmd.append("--keep-toc-pages")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=ENV)
        return result.stdout, result.stderr, 0
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode

def convert_folder(folder_path, output_dir, no_images, no_toc, keep_toc_pages):
    """Convert all PDFs in a folder."""
    output_dir = os.path.abspath(output_dir)

    cmd = [
        sys.executable, CONVERTER_SCRIPT, folder_path,
        "--out", output_dir,
        "--batch",
        "--recursive"
    ]

    if no_images:
        cmd.append("--no-images")
    if no_toc:
        cmd.append("--no-toc")
    if keep_toc_pages:
        cmd.append("--keep-toc-pages")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=ENV)
        return result.stdout, result.stderr, 0
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode

def create_ui():
    """Create Gradio interface."""
    with gr.Blocks() as demo:
        gr.Markdown(
            """
## 📄 PDF to Semantic HTML Converter

Convert PDFs to clean, SEO-optimized HTML with headings, TOC, figures, and schema.org metadata.
            """
        )

        with gr.Tab("Convert"):
            with gr.Row():
                pdf_input = gr.File(
                    label="📄 Upload PDF",
                    file_types=[".pdf"],
                    file_count="single"
                )

                output_dir = gr.Textbox(
                    label="📁 Output directory",
                    placeholder="/home/clawdbot/clawd/pdf-to-html/out",
                    value="/home/clawdbot/clawd/pdf-to-html/out"
                )

            with gr.Row():
                no_images = gr.Checkbox(
                    label="🚫 Skip images",
                    value=False,
                    info="Don't extract images from PDF"
                )

                no_toc = gr.Checkbox(
                    label="🚫 Skip Table of Contents",
                    value=False,
                    info="Don't generate TOC"
                )

                keep_toc_pages = gr.Checkbox(
                    label="📄 Keep original TOC pages",
                    value=False,
                    info="Include PDF TOC pages in output"
                )

            with gr.Row():
                convert_btn = gr.Button("🔄 Convert", variant="primary", size="lg")

        with gr.Tab("Batch Convert"):
            folder_input = gr.Textbox(
                label="📁 Folder path",
                placeholder="/path/to/pdfs",
                info="Local path to folder containing PDFs"
            )

            with gr.Row():
                output_dir_batch = gr.Textbox(
                    label="📁 Output directory",
                    placeholder="/home/clawdbot/clawd/pdf-to-html/out",
                    value="/home/clawdbot/clawd/pdf-to-html/out"
                )

            with gr.Row():
                no_images_batch = gr.Checkbox(label="🚫 Skip images", value=False)
                no_toc_batch = gr.Checkbox(label="🚫 Skip Table of Contents", value=False)
                keep_toc_pages_batch = gr.Checkbox(label="📄 Keep original TOC pages", value=False)

            with gr.Row():
                convert_batch_btn = gr.Button("📦 Batch Convert", variant="primary", size="lg")

        with gr.Row():
            status_output = gr.Textbox(
                label="⏳ Status",
                lines=10,
                max_lines=20
            )

            clear_btn = gr.Button("🗑️ Clear", variant="secondary")

        # Download file component - SEPARATE, always visible
        download_file = gr.File(
            label="📥 Download Converted HTML File",
            visible=True  # Always visible for now (testing)
        )

        # Event handlers
        convert_btn.click(
            fn=handle_convert,
            inputs=[pdf_input, output_dir, no_images, no_toc, keep_toc_pages],
            outputs=[status_output, download_file]
        )

        convert_batch_btn.click(
            fn=handle_batch,
            inputs=[folder_input, output_dir_batch, no_images_batch, no_toc_batch, keep_toc_pages_batch],
            outputs=[status_output, download_file]
        )

        clear_btn.click(
            fn=lambda: ("", gr.File(label="📥 Download Converted HTML File", visible=False)),
            outputs=[status_output, download_file]
        )

    return demo

def handle_convert(pdf_file, output_dir, no_images, no_toc, keep_toc_pages):
    """Handle single PDF conversion."""
    if not pdf_file:
        return "❌ No PDF file selected", None

    pdf_path = pdf_file.name
    stdout, stderr, returncode = convert_pdf(pdf_path, output_dir, no_images, no_toc, keep_toc_pages)

    if returncode != 0:
        return f"❌ Conversion failed!\n📄 Input: `{pdf_path}`\n📁 Output dir: `{output_dir}`\n🔴 Exit code: {returncode}\n❓ Error output:\n{stderr}\n📝 Standard output:\n{stdout}", None

    output_dir_path = Path(output_dir)
    pdf_name = Path(pdf_path).stem
    output_file = None

    for f in output_dir_path.glob(f"{pdf_name}*.html"):
        output_file = f
        break

    if output_file:
        LAST_CONVERTED_FILE = str(output_file)
        file_size = output_file.stat().st_size / 1024
        status_text = f"✅ Conversion complete!\n\n📄 Input: `{pdf_path}`\n📁 Output: `{output_file}`\n📊 Size: {file_size:.1f} KB\n\n📝 Log:\n{stdout}\n\n📥 File ready for download below!"

        # Return status and a gr.File object
        return status_text, gr.File(value=str(output_file))
    else:
        return f"❌ Output file not found!\n\n📄 Input: `{pdf_path}`\n📁 Output directory: `{output_dir_path}`\n\nSearched for: {pdf_name}*.html", None

def handle_batch(folder_path, output_dir, no_images, no_toc, keep_toc_pages):
    """Handle batch folder conversion."""
    if not folder_path:
        return "❌ No folder path provided", None

    folder = folder_path.strip()

    if not os.path.isdir(folder):
        return f"❌ Folder not found: {folder}", None

    stdout, stderr, returncode = convert_folder(folder_path, output_dir, no_images, no_toc, keep_toc_pages)

    if returncode != 0:
        return f"❌ Batch conversion failed!\n\n📁 Input folder: `{folder}`\n📁 Output dir: `{output_dir}`\n🔴 Exit code: {returncode}\n❓ Error output:\n{stderr}\n📝 Standard output:\n{stdout}", None

    output_dir_path = Path(output_dir)
    html_files = list(output_dir_path.glob("**/index.html"))

    if html_files:
        return f"✅ Batch conversion complete!\n\n📁 Folder: {folder}\n📁 Output: {output_dir}\n📊 Generated: {len(html_files)} HTML files\n\n📝 Log:\n{stdout}\n\n📥 Browse output directory for individual files", None
    else:
        return f"❌ No HTML files found in output directory!\n\n📁 Input folder: {folder}\n📁 Output directory: `{output_dir_path}`\n📝 Log:\n{stdout}\n❓ Error output:\n{stderr}", None

if __name__ == "__main__":
    print(f"✅ Converter found: {CONVERTER_SCRIPT}")
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
