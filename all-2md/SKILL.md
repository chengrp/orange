---
name: all-2-md
description: Convert various document formats to Markdown using Microsoft MarkItDown. Supports PDF, DOCX, PPTX, XLSX, HTML, images (OCR), audio (speech-to-text), and ZIP archives. Use when Claude needs to extract text/content from non-Markdown documents, process scanned documents with OCR, convert presentations/tables to readable format, or transcribe audio files.
---

# All-2-MD

Convert various document formats to Markdown using Microsoft's MarkItDown tool.

## Quick Start

Use Bash to convert documents:

```bash
markitdown "path/to/document.pdf"
markitdown "path/to/document.docx" -o output.md
```

Or use Python module:

```bash
python -m markitdown "path/to/document.pdf"
```

## Core Principle: Content Preservation

**Never discard original content without explicit user confirmation.** The goal is to preserve as much content and structure from the original document as possible.

## Supported Formats & Handling Strategies

| Format | Default Strategy | Fallback/Advanced Strategy |
|--------|------------------|---------------------------|
| `.pdf` | Text extraction with structure | OCR for scanned content; embed images for visual elements |
| `.docx` | Native parsing | Preserve formatting, tables, embedded images |
| `.pptx` | Slide-by-slide extraction | Export slide images as fallback |
| `.xlsx`, `.xls` | Convert to Markdown tables | Preserve formulas as comments if possible |
| `.html`, `.htm` | Convert to Markdown | Embed if structure too complex |
| Images | OCR text extraction | Embed image if no text found |
| Audio | Speech-to-text | Include metadata (duration, format) |
| `.zip` | Process all files recursively | List contents if extraction fails |

## Handling Scenarios

### PDF Documents

#### Scenario 1: Text-based PDF with Tables
- Extract text and convert tables to Markdown format
- Preserve table headers, merged cells if possible
- If table structure is complex, note the limitation and ask user for preferred format

#### Scenario 2: Scanned PDF / Image-based PDF
- Use OCR to extract all text content
- Preserve reading order as much as possible
- If OCR quality is poor, note this and suggest manual review

#### Scenario 3: PDF with Images/Diagrams
- Extract text content via OCR or native parsing
- For diagrams/charts: embed original images in Markdown
- For photos: embed images directly, add alt text description if possible
- Never discard visual content without user confirmation

#### Scenario 4: Photo-only PDF / Document is purely visual
- If no text can be extracted (e.g., photo album, art book)
- Embed all images into Markdown in original order
- Add descriptive comments for context

#### Scenario 5: Mixed Content PDF
- Extract text where available
- Embed images for visual elements
- Use placeholder comments: `[Image: description]` if needed
- Ask user to confirm if uncertain about specific elements

### Images (JPG/PNG/GIF/BMP)

#### Scenario 1: Text-containing Image (Screenshot, Document Scan)
- Use OCR to extract all text
- Preserve line breaks and structure
- Embed original image for reference

#### Scenario 2: Photo with No Text (Portrait, Landscape)
- No OCR applicable
- Embed image directly in Markdown
- Add descriptive alt text if context provided

#### Scenario 3: Diagram/Chart/Infographic
- Attempt OCR for any text labels
- Embed full image for visual accuracy
- Note if text extraction is incomplete

### Presentations (PPTX)

#### Scenario 1: Text-heavy Slides
- Extract all text content
- Preserve slide structure and hierarchy
- Note slide numbers for reference

#### Scenario 2: Visual Slides / Graphics-heavy
- Extract text where available
- Export slide images for visual content
- Combine text + images in output

### Spreadsheets (XLSX/XLS)

#### Scenario 1: Data Tables
- Convert to Markdown tables
- Preserve headers and alignment
- Note if merged cells were flattened

#### Scenario 2: Formulas / Calculations
- Extract cell values
- Add formulas as comments if accessible
- Note if dynamic content cannot be preserved

### Audio Files (MP3/WAV/M4A/OGG)

#### Scenario 1: Clear Speech
- Transcribe using speech-to-text
- Preserve speaker segmentation if available
- Add timestamps if supported

#### Scenario 2: Poor Audio Quality / Multiple Speakers
- Best-effort transcription
- Note quality issues in output
- Suggest manual review if confidence low

### ZIP Archives

#### Scenario 1: Mixed File Archive
- Recursively process all supported files
- Maintain directory structure in output
- List unsupported files with note

#### Scenario 2: Large Archive
- Process files in batches
- Provide progress updates
- Ask for confirmation if size is very large

## When Content Cannot Be Preserved

If MarkItDown fails to handle specific content:

1. **Note the limitation explicitly** in the output
2. **Preserve original content** by embedding images or raw text
3. **Ask user for preference** if multiple approaches are possible
4. **Provide context** about what was challenging (e.g., complex layout, corrupted data)

## Output Quality Checklist

After conversion, verify:
- [ ] No content was silently discarded
- [ ] Images/diagrams are embedded or described
- [ ] Tables preserve structure (headers, rows, columns)
- [ ] Text is readable and properly formatted
- [ ] OCR results are reasonably accurate
- [ ] Original file structure is maintained

## Installation

```bash
pip install markitdown
```

See [INSTALLATION.md](references/INSTALLATION.md) for detailed installation and usage.

See [FEATURES.md](references/FEATURES.md) for complete feature documentation and handling scenarios.

## Technical Details

- Tool: [MarkItDown](https://github.com/microsoft/markitdown) by Microsoft
- Version: 0.0.2
- All dependencies bundled: OCR, PDF, Office, HTML, Audio, Image processing
