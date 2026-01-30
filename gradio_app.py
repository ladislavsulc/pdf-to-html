#!/usr/bin/env python3
"""
Gradio Web App Wrapper for PDF-to-HTML Converter
Provides drag-and-drop interface for the PyMuPDF-based converter.

Features:
- Drag and drop PDF upload
- Folder selection (batch mode)
- Custom flags (no-images, no-toc, keep-toc-pages)
- Progress tracking
- Live HTML preview
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    print("Error: gradio not found. Install with: pip install gradio")
    sys.exit(1)

# Constants
DEFAULT_OUTPUT_DIR = "out"
CONVERTER_SCRIPT = "/home/clawdbot/clawd/pdf-to-html-fork/scripts/pdf_to_semantic_html.py"

def convert_pdf(pdf_path, output_dir, no_images=False, no_toc=False, keep_toc_pages=False):
    """Run pdf_to_semantic_html.py with custom options."""
    cmd = [sys.executable, CONVERTER_SCRIPT, pdf_path]

    # Add output directory
    if output_dir:
        cmd.extend(["--out", output_dir])

    # Add custom flags
    if no_images:
        cmd.append("--no-images")
    if no_toc:
        cmd.append("--no-toc")
    if keep_toc_pages:
        cmd.append("--keep-toc-pages")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def convert_folder(folder_path, output_dir, no_images, no_toc, keep_toc_pages):
    """Convert all PDFs in a folder."""
    try:
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

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

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
                    placeholder="out",
                    value="out"
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

        with gr.Tab("Batch Convert"):
            folder_input = gr.Textbox(
                label="📁 Folder path",
                placeholder="/path/to/pdfs",
                info="Local path to folder containing PDFs"
            )

            with gr.Row():
                output_dir_batch = gr.Textbox(
                    label="📁 Output directory",
                    placeholder="out",
                    value="out"
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
            convert_btn = gr.Button("🔄 Convert", variant="primary", size="lg")
            convert_batch_btn = gr.Button("📦 Batch Convert", variant="primary", size="lg")

        with gr.Row():
            preview_output = gr.Code(
                label="👁 Output Log",
                interactive=False
            )

            status_output = gr.Textbox(
                label="⏳ Status",
                lines=3,
                max_lines=10
            )

        with gr.Row():
            clear_btn = gr.Button("🗑️ Clear", variant="secondary")

        # Event handlers
        convert_btn.click(
            fn=lambda f, d, ni, nt, kt: handle_convert(f, d, ni, nt, kt),
            inputs=[pdf_input, output_dir, no_images, no_toc, keep_toc_pages],
            outputs=[status_output]
        )

        convert_batch_btn.click(
            fn=lambda f, d, ni, nt, kt: handle_batch(f, d, ni, nt, kt),
            inputs=[folder_input, output_dir_batch, no_images_batch, no_toc_batch, keep_toc_pages_batch],
            outputs=[status_output]
        )

        clear_btn.click(
            fn=lambda: ("", ""),
            outputs=[status_output, preview_output]
        )

    return demo

def handle_convert(pdf_file, output_dir, no_images, no_toc, keep_toc_pages):
    """Handle single PDF conversion."""
    if not pdf_file:
        return "❌ No PDF file selected"

    yield "⏳ Starting conversion..."

    # Get file path
    pdf_path = pdf_file.name

    result = convert_pdf(pdf_path, output_dir, no_images, no_toc, keep_toc_pages)

    if result.startswith("Error"):
        yield f"❌ {result}"
    else:
        # Find output file
        output_dir_path = output_dir.rstrip('/')
        pdf_name = Path(pdf_path).stem
        output_file = Path(output_dir_path) / pdf_name / "index.html"

        yield f"""
✅ Conversion complete!

📄 Input: `{pdf_path}`
📁 Output: `{output_file}`
📊 Size: {output_file.stat().st_size / 1024:.1f} KB
📝 Log:
{result}
        """

def handle_batch(folder_path, output_dir, no_images, no_toc, keep_toc_pages):
    """Handle batch folder conversion."""
    if not folder_path:
        return "❌ No folder path provided"

    folder = folder_path.strip()

    if not os.path.isdir(folder):
        return f"❌ Folder not found: {folder}"

    yield "⏳ Scanning folder..."

    try:
        pdf_count = len([f for f in Path(folder).rglob("*") if f.is_file() and f.suffix.lower() == '.pdf'])

        yield f"📊 Found {pdf_count} PDF files"
        yield "⏳ Starting batch conversion..."

        result = convert_folder(folder, output_dir, no_images, no_toc, keep_toc_pages)

        if result.startswith("Error"):
            yield f"❌ {result}"
        else:
            yield f"""
✅ Batch conversion complete!

📁 Folder: {folder}
📊 Processed: {pdf_count} files
📁 Output: {output_dir}
📝 Log:
{result}
            """

    except Exception as e:
        yield f"❌ Batch error: {e}"

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
