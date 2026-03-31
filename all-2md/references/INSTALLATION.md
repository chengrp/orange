# Installation Guide for All-2-MD

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Quick Install

```bash
pip install markitdown
```

This single command installs all dependencies automatically.

## What Gets Installed

MarkItDown includes all necessary dependencies:

| Feature | Library |
|---------|---------|
| OCR | azure-ai-documentintelligence |
| PDF | pdfminer-six |
| Word (DOCX) | mammoth |
| PowerPoint (PPTX) | python-pptx |
| Excel (XLSX/XLS) | openpyxl, xlrd |
| HTML | beautifulsoup4, markdownify |
| Audio | speechrecognition, pydub |
| Images | puremagic, numpy |

## Verify Installation

```bash
# Test command line tool
markitdown --help

# Test Python module
python -c "from markitdown import MarkItDown; print('OK')"
```

## Usage Methods

### Method 1: Command Line

```bash
markitdown document.pdf -o output.md
```

### Method 2: Python Module

```bash
python -m markitdown document.pdf
```

### Method 3: Bundled Script

```bash
# Convert to stdout
python scripts/convert.py document.pdf

# Convert to file
python scripts/convert.py document.pdf output.md
```

## Optional: Install from Requirements

If you prefer to see all dependencies first:

```bash
pip install -r requirements.txt
```

Note: `requirements.txt` is provided for transparency. Installing markitdown directly is recommended as it automatically handles dependency versions.
