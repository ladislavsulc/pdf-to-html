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
import zipfile
from pathlib import Path
from datetime import datetime

import gradio as gr

print(f"Gradio version: {gr.__version__}")

# Constants
REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = str(REPO_ROOT / "out")
CONVERTER_SCRIPT = str(REPO_ROOT / "scripts" / "pdf_to_semantic_html.py")

# Set up environment with user's site-packages
ENV = os.environ.copy()
USER_SITE = os.path.expanduser('~/.local/lib/python3.12/site-packages')
if 'PYTHONPATH' in ENV:
    ENV['PYTHONPATH'] = USER_SITE + ':' + ENV['PYTHONPATH']
else:
    ENV['PYTHONPATH'] = USER_SITE

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

**Quick steps**
1. Upload a PDF (or provide a folder for batch conversion).
2. Choose an output folder (defaults to `./out`).
3. Click **Convert** and download the resulting HTML.
            """
        )

        with gr.Tab("Convert"):
            with gr.Row():
                pdf_input = gr.File(
                    label="📄 Upload PDF",
                    file_types=[".pdf"],
                    file_count="single"
                )

                with gr.Column():
                    output_dir = gr.Textbox(
                        label="📁 Output directory",
                        placeholder=DEFAULT_OUTPUT_DIR,
                        value=DEFAULT_OUTPUT_DIR
                    )
                    gr.Markdown("Converted HTML will be saved here and exposed for download below.")

            with gr.Accordion("Advanced options", open=False):
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
                    placeholder=DEFAULT_OUTPUT_DIR,
                    value=DEFAULT_OUTPUT_DIR
                )

            with gr.Accordion("Advanced options", open=False):
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
                max_lines=20,
                elem_id="status-box"
            )

            clear_btn = gr.Button("🗑️ Clear", variant="secondary")

        with gr.Row():
            download_file = gr.File(
                label="📥 Download Converted HTML File",
                visible=False
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
            fn=lambda: ("", gr.update(value=None, visible=False)),
            outputs=[status_output, download_file]
        )

    return demo

def create_zip_with_images(html_file, output_dir_path):
    """Create a ZIP file containing HTML and images folder if it exists."""
    pdf_name = html_file.stem
    images_dir = html_file.parent / "images"

    # Check if images directory exists and has content
    if not images_dir.exists() or not list(images_dir.glob("*")):
        return html_file  # No images to include

    # Create ZIP file
    zip_path = html_file.parent / f"{pdf_name}_with_images.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add HTML file (put it in the root of ZIP)
        zipf.write(html_file, html_file.name)

        # Add images folder with all images
        for img_file in images_dir.glob("*"):
            if img_file.is_file():
                # Add with relative path: images/filename.ext
                zipf.write(img_file, f"images/{img_file.name}")

    return zip_path

def handle_convert(pdf_file, output_dir, no_images, no_toc, keep_toc_pages):
    """Handle single PDF conversion."""
    if not pdf_file:
        return "❌ No PDF file selected", gr.update(value=None, visible=False)

    pdf_path = pdf_file.name
    stdout, stderr, returncode = convert_pdf(pdf_path, output_dir, no_images, no_toc, keep_toc_pages)

    if returncode != 0:
        return (
            "❌ Conversion failed!\n"
            f"📄 Input: `{pdf_path}`\n"
            f"📁 Output dir: `{output_dir}`\n"
            f"🔴 Exit code: {returncode}\n"
            f"❓ Error output:\n{stderr}\n"
            f"📝 Standard output:\n{stdout}"
        ), gr.update(value=None, visible=False)

    output_dir_path = Path(output_dir)
    pdf_name = Path(pdf_path).stem
    output_files = sorted(
        output_dir_path.glob(f"{pdf_name}*.html"),
        key=lambda item: item.stat().st_mtime,
        reverse=True
    )
    output_file = output_files[0] if output_files else None

    if output_file:
        file_size = output_file.stat().st_size / 1024

        # Create ZIP with images if they exist
        download_file = create_zip_with_images(output_file, output_dir_path)

        # If we created a ZIP, use that for download
        if download_file != output_file:
            file_size_zip = download_file.stat().st_size / 1024
            status_text = (
                "✅ Conversion complete!\n\n"
                f"📄 Input: `{pdf_path}`\n"
                f"📁 Output: `{output_file.name}`\n"
                f"📦 Download: `{download_file.name}` (HTML + images)\n"
                f"📊 Size: {file_size:.1f} KB (HTML), {file_size_zip:.1f} KB (ZIP)\n\n"
                f"📝 Log:\n{stdout}\n\n"
                "📥 File ready for download below! (ZIP contains HTML + images folder)"
            )
        else:
            status_text = (
                "✅ Conversion complete!\n\n"
                f"📄 Input: `{pdf_path}`\n"
                f"📁 Output: `{output_file.name}`\n"
                f"📊 Size: {file_size:.1f} KB\n\n"
                f"📝 Log:\n{stdout}\n\n"
                "📥 File ready for download below!"
            )

        return status_text, gr.update(value=str(download_file), visible=True)
    else:
        return (
            "❌ Output file not found!\n\n"
            f"📄 Input: `{pdf_path}`\n"
            f"📁 Output directory: `{output_dir_path}`\n\n"
            f"Searched for: {pdf_name}*.html"
        ), gr.update(value=None, visible=False)

def handle_batch(folder_path, output_dir, no_images, no_toc, keep_toc_pages):
    """Handle batch folder conversion."""
    if not folder_path:
        return "❌ No folder path provided", gr.update(value=None, visible=False)

    folder = folder_path.strip()

    if not os.path.isdir(folder):
        return f"❌ Folder not found: {folder}", gr.update(value=None, visible=False)

    stdout, stderr, returncode = convert_folder(folder_path, output_dir, no_images, no_toc, keep_toc_pages)

    if returncode != 0:
        return (
            "❌ Batch conversion failed!\n\n"
            f"📁 Input folder: `{folder}`\n"
            f"📁 Output dir: `{output_dir}`\n"
            f"🔴 Exit code: {returncode}\n"
            f"❓ Error output:\n{stderr}\n"
            f"📝 Standard output:\n{stdout}"
        ), gr.update(value=None, visible=False)

    output_dir_path = Path(output_dir)
    html_files = list(output_dir_path.glob("**/index.html"))

    if html_files:
        return (
            "✅ Batch conversion complete!\n\n"
            f"📁 Folder: {folder}\n"
            f"📁 Output: {output_dir}\n"
            f"📊 Generated: {len(html_files)} HTML files\n\n"
            f"📝 Log:\n{stdout}\n\n"
            "📥 Browse output directory for individual files"
        ), gr.update(value=None, visible=False)
    else:
        return (
            "❌ No HTML files found in output directory!\n\n"
            f"📁 Input folder: {folder}\n"
            f"📁 Output directory: `{output_dir_path}`\n"
            f"📝 Log:\n{stdout}\n"
            f"❓ Error output:\n{stderr}"
        ), gr.update(value=None, visible=False)

if __name__ == "__main__":
    print(f"✅ Converter found: {CONVERTER_SCRIPT}")
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(),
        css="""
        #status-box textarea {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;}
        """
    )
