#!/usr/bin/env python3
"""
Gradio Web App Wrapper for PDF-to-HTML Converter
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
import shutil
from pathlib import Path
from datetime import datetime

try:
    import gradio as gr
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
    # Ensure output directory is absolute
    output_dir = os.path.abspath(output_dir)

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    cmd = [sys.executable, CONVERTER_SCRIPT, pdf_path, "--out", output_dir]

    # Add custom flags
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
    # Ensure output directory is absolute
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
                no_images_batch = gr.Checkbox(
                    label="🚫 Skip images",
                    value=False
                )

                no_toc_batch = gr.Checkbox(
                    label="🚫 Skip Table of Contents",
                    value=False
                )

                keep_toc_pages_batch = gr.Checkbox(
                    label="📄 Keep original TOC pages",
                    value=False
                )

            with gr.Row():
                convert_batch_btn = gr.Button("📦 Batch Convert", variant="primary", size="lg")

        with gr.Row():
            status_output = gr.Textbox(
                label="⏳ Status",
                lines=10,
                max_lines=20
            )

            download_btn = gr.Button("📥 Download Converted File", variant="secondary", size="lg")

        download_file = gr.File(
            label="📁 Download",
            visible=False
        )

        with gr.Row():
            clear_btn = gr.Button("🗑️ Clear", variant="secondary")

        # Event handlers
        convert_btn.click(
            fn=lambda f, d, ni, nt, kt: handle_convert(f, d, ni, nt, kt, False),
            inputs=[pdf_input, output_dir, no_images, no_toc, keep_toc_pages],
            outputs=[status_output, download_file]
        )

        convert_batch_btn.click(
            fn=lambda f, d, ni, nt, kt: handle_batch(f, d, ni, nt, kt, False),
            inputs=[folder_input, output_dir_batch, no_images_batch, no_toc_batch, keep_toc_pages_batch],
            outputs=[status_output, download_file]
        )

        download_btn.click(
            fn=lambda: None,  # No change to status, just shows download button
            outputs=[status_output]
        )

        clear_btn.click(
            fn=lambda: ("", None, ""),
            outputs=[status_output, download_file]
        )

    return demo

def handle_convert(pdf_file, output_dir, no_images, no_toc, keep_toc_pages, return_file=False):
    """Handle single PDF conversion."""
    global LAST_CONVERTED_FILE

    if not pdf_file:
        return "❌ No PDF file selected", None

    # Get file path
    pdf_path = pdf_file.name

    # Run conversion
    stdout, stderr, returncode = convert_pdf(pdf_path, output_dir, no_images, no_toc, keep_toc_pages)

    if returncode != 0:
        return f"""
❌ Conversion failed!

📄 Input: `{pdf_path}`
📁 Output dir: `{output_dir}`
🔴 Exit code: {returncode}

❓ Error output:
{stderr}

📝 Standard output:
{stdout}
        """, None

    # Find output file (search for actual output)
    output_dir_path = Path(output_dir)
    pdf_name = Path(pdf_path).stem

    # Search for output files in multiple patterns
    output_file = None

    # Try flat file structure (most common for single files)
    possible_flat = output_dir_path / f"{pdf_name}.html"
    if possible_flat.exists():
        output_file = possible_flat

    # Try directory structure (batch mode)
    possible_dir = output_dir_path / pdf_name / "index.html"
    if possible_dir.exists():
        output_file = possible_dir

    # Search for any HTML file with matching name
    if not output_file and output_dir_path.exists():
        for html_file in output_dir_path.glob("*.html"):
            if pdf_name in html_file.stem:
                output_file = html_file
                break

    if output_file:
        LAST_CONVERTED_FILE = str(output_file)
        file_size = output_file.stat().st_size / 1024

        status_text = f"""
✅ Conversion complete!

📄 Input: `{pdf_path}`
📁 Output: `{output_file}`
📊 Size: {file_size:.1f} KB

📝 Log:
{stdout}

📥 Click "Download Converted File" button below to download the result!
        """

        if return_file:
            # Create a downloadable file component
            return status_text, gr.File(value=str(output_file), visible=True, label=f"Download: {output_file.name}")
        else:
            return status_text, gr.File(value=str(output_file), visible=False)

    # File not found - show all files for debugging
    all_files = list(output_dir_path.iterdir()) if output_dir_path.exists() else []
    files_list = "\n".join(f"  - {f.name}" for f in all_files[:20])

    return f"""
❌ Output file not found!

📄 Input: `{pdf_path}`
📁 Output directory: `{output_dir_path}`

Searched for:
1. `{output_dir_path / f"{pdf_name}.html"}` (flat file)
2. `{output_dir_path / pdf_name / "index.html"}` (directory structure)
3. Any HTML file containing `{pdf_name}` in name

Files in output directory:
{files_list}

This could mean:
1. Conversion failed silently
2. Output file has different name
3. Output directory issue

📝 Command output:
{stdout}

🔴 Error output:
{stderr}
    """, None

def handle_batch(folder_path, output_dir, no_images, no_toc, keep_toc_pages, return_file=False):
    """Handle batch folder conversion."""
    global LAST_CONVERTED_FILE

    if not folder_path:
        return "❌ No folder path provided", None

    folder = folder_path.strip()

    if not os.path.isdir(folder):
        return f"❌ Folder not found: {folder}", None

    # Run conversion
    stdout, stderr, returncode = convert_folder(folder_path, output_dir, no_images, no_toc, keep_toc_pages)

    if returncode != 0:
        return f"""
❌ Batch conversion failed!

📁 Input folder: `{folder}`
📁 Output dir: `{output_dir}`
🔴 Exit code: {returncode}

❓ Error output:
{stderr}

📝 Standard output:
{stdout}
        """, None

    # Count files in output
    output_dir_path = Path(output_dir)
    html_files = list(output_dir_path.glob("**/index.html"))

    if html_files:
        LAST_CONVERTED_FILE = str(output_dir_path)

        return f"""
✅ Batch conversion complete!

📁 Folder: {folder}
📁 Output: {output_dir}
📊 Generated: {len(html_files)} HTML files

📝 Log:
{stdout}

📥 Download individual files from the output directory if needed.
        """, None
    else:
        return f"""
❌ No HTML files found in output directory!

📁 Input folder: {folder}
📁 Output directory: {output_dir}

📝 Command output:
{stdout}

🔴 Error output:
{stderr}
        """, None

def verify_converter():
    """Check if converter script exists."""
    if os.path.exists(CONVERTER_SCRIPT):
        return "✅ Converter found: " + CONVERTER_SCRIPT
    else:
        return "❌ Converter not found: " + CONVERTER_SCRIPT

if __name__ == "__main__":
    # Verify installation
    verify_result = verify_converter()
    print(verify_result)

    # Create and launch Gradio UI
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
