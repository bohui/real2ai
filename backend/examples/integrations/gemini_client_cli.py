"""
GeminiClient integration CLI

Run ad-hoc calls against the Google Gemini client used in this repo.

Examples:
  - Text generation:
      python backend/examples/integrations/gemini_client_cli.py generate \
        --prompt "Write a haiku about property valuations" \
        --temperature 0.3 --max-tokens 256

  - Image/PDF OCR (extract text):
      python backend/examples/integrations/gemini_client_cli.py extract-text \
        --file ./test_files/1691023415-16178-55Roseville-RA.pdf

  - Document analysis:
      python backend/examples/integrations/gemini_client_cli.py analyze-document \
        --file ./test_files/1690959428-7812-ContractforSale.pdf

  - Image semantics (vision reasoning):
      python backend/examples/integrations/gemini_client_cli.py image-semantics \
        --file ./some_image.png --prompt "Describe the scene"

Environment/auth:
  - Uses Application Default Credentials (ADC). Ensure one of:
      * GOOGLE_APPLICATION_CREDENTIALS points to a service account JSON, or
      * You ran: gcloud auth application-default login
  - Optional envs (see app.clients.gemini.config.GeminiSettings):
      * GOOGLE_CLOUD_PROJECT or GEMINI_PROJECT_ID
      * GOOGLE_CLOUD_LOCATION or GEMINI_LOCATION (default: global)

Note: This script imports from the `app` package. Run it from the repo root so
Python finds `backend/app` on PYTHONPATH, e.g.:
  PYTHONPATH=backend python backend/examples/integrations/gemini_client_cli.py generate --prompt "Hello"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import mimetypes
import os
import sys
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional
from google import genai
from google.genai.types import GenerateContentConfig, SafetySetting, Part, Content

# Ensure `app` package is importable when running from repo root
REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.clients import get_gemini_client  # noqa: E402
from app.clients.base.exceptions import ClientError  # noqa: E402

from pydantic import BaseModel
from enum import Enum


class DiagramType(str, Enum):
    SITE_PLAN = "site_plan"
    SEWER_DIAGRAM = "sewer_diagram"
    SERVICE_LOCATION_DIAGRAM = "service_location_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    TITLE_PLAN = "title_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    UNKNOWN = "unknown"


class Diagram(BaseModel):
    type: DiagramType
    page: int


class DocumentSummary(BaseModel):
    content_html: str
    diagram: list[Diagram]


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


def read_file_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def guess_mime_type(file_path: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        return mime
    # Fallbacks by extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".pdf"}:
        return "application/pdf"
    if ext in {".png"}:
        return "image/png"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext in {".webp"}:
        return "image/webp"
    if ext in {".gif"}:
        return "image/gif"
    if ext in {".bmp"}:
        return "image/bmp"
    if ext in {".tiff", ".tif"}:
        return "image/tiff"
    return "application/octet-stream"


def to_jsonable(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    # Graceful fallback
    return str(obj)


PROMPT = """
# PDF to HTML Conversion with Citation Structure and Diagram Detection

## Primary Task
Convert the provided PDF document to a complete HTML format with proper semantic structure, unique identifiers for citation linking, and extract all diagrams/visual elements.

## HTML Structure Requirements

### 1. Document Structure
- Use proper HTML5 semantic elements (`<header>`, `<main>`, `<section>`, `<article>`)
- Maintain hierarchical heading structure (h1, h2, h3, h4, h5, h6)
- Preserve paragraph breaks and text formatting
- Include a table of contents with anchor links

### 2. Unique ID Generation
- Assign unique IDs to every structural element:
  - **Headings**: `heading-{sequential-number}` (e.g., `heading-001`, `heading-002`)
  - **Paragraphs**: `para-{sequential-number}` (e.g., `para-001`, `para-002`)
  - **Lists**: `list-{sequential-number}` and `list-item-{sequential-number}`
  - **Tables**: `table-{sequential-number}`
  - **Figures/Images**: `figure-{sequential-number}`
  - **Sections**: `section-{sequential-number}`

### 3. Citation-Ready Format
- Each paragraph should be wrapped in `<p id="para-XXX">` tags
- Each heading should have `<h# id="heading-XXX">` format
- Include page number references as data attributes: `data-page="X"`
- Add source paragraph numbering: `data-source-para="X"`

### 4. Content Preservation
- Maintain all text content, including footnotes and references
- Preserve formatting (bold, italic, underline) using appropriate HTML tags
- Convert bullet points and numbered lists to proper `<ul>` and `<ol>` elements
- Handle tables with proper `<table>`, `<thead>`, `<tbody>` structure

## Example HTML Output Structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Document Title</title>
</head>
<body>
    <header id="document-header">
        <h1 id="heading-001">Document Title</h1>
    </header>
    
    <nav id="table-of-contents">
        <!-- Auto-generated TOC with anchor links -->
    </nav>
    
    <main id="main-content">
        <section id="section-001" data-page="1">
            <h2 id="heading-002">Chapter/Section Title</h2>
            <p id="para-001" data-page="1" data-source-para="1">First paragraph content...</p>
            <p id="para-002" data-page="1" data-source-para="2">Second paragraph content...</p>
        </section>
    </main>
</body>
</html>
```

## Diagram and Visual Element Detection

### Task: Create JSON List of All Diagrams
Analyze the PDF and create a comprehensive JSON array containing all visual elements:

### Required JSON Structure:
```json
[
    {
        "page_number": 1,
        "diagram_type": "flowchart",
    },
    {
        "page_number": 3,
        "diagram_type": "bar_chart",
    }
]
```

### Diagram Types to Identify:
- **Charts**: `bar_chart`, `line_chart`, `pie_chart`, `scatter_plot`, `histogram`
- **Diagrams**: `flowchart`, `network_diagram`, `organizational_chart`, `process_diagram`, `timeline`
- **Technical**: `schematic`, `blueprint`, `technical_drawing`, `circuit_diagram`
- **Images**: `photograph`, `illustration`, `screenshot`, `map`
- **Tables**: `data_table`, `comparison_table`, `matrix`
- **Other**: `infographic`, `mind_map`, `tree_diagram`, `venn_diagram`

### Additional Metadata to Include:
- **page_number**: Integer page number where diagram appears
- **diagram_type**: String from the categories above

## Output Requirements

### 1. Complete HTML File
- Single HTML file with all content
- Properly formatted and indented
- Valid HTML5 markup
- Responsive design considerations

### 2. JSON Diagram List
- Separate JSON file or embedded in HTML as script tag
- Complete list of all visual elements
- Accurate page numbers and classifications

### 3. Citation Reference Guide
- Include a comment section explaining the ID system
- Provide examples of how to create citation links
- Document the data attribute system

## Quality Assurance Checklist
- [ ] All text content preserved
- [ ] Proper heading hierarchy maintained
- [ ] Every element has unique ID
- [ ] Page numbers accurately mapped
- [ ] All diagrams identified and classified
- [ ] HTML validates without errors
- [ ] Citation links functional
- [ ] Table of contents generated
- [ ] Formatting preserved (bold, italic, etc.)

## Additional Instructions
- If text is unclear or corrupted, note it in HTML comments
- Preserve original document structure as much as possible
- Include any metadata about the source PDF (creation date, author, etc.)
- Handle multi-column layouts appropriately
- Ensure accessibility with proper alt text for images
"""

file_path = "../test_files/1690959428-7812-ContractforSale.pdf"


async def run_with_doc():

    with open(file_path, "rb") as f:
        file_bytes = f.read()
    # Create the document content
    document_content = Part.from_bytes(data=file_bytes, mime_type="application/pdf")
    prompt_content = Part.from_text(text=PROMPT)

    contents = [
        Content(role="user", parts=[document_content, prompt_content]),
    ]
    generate_summary_config = GenerateContentConfig(
        temperature=1,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        safety_settings=[
            SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        response_mime_type="application/json",
        response_schema=DocumentSummary,
    )

    client = await get_gemini_client()

    result_text = client.client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=generate_summary_config,
    )
    dict_result = json.loads(result_text.text)
    with open("../test_files/contract_summary.html", "w") as f:
        f.write(dict_result["content_html"])

    print(dict_result["diagram"])
    print(result_text.text)


async def run_generate(args: argparse.Namespace) -> Dict[str, Any]:
    client = await get_gemini_client()
    result_text = await client.generate_content(
        prompt=args.prompt,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        system_prompt=args.system_prompt,
        model=args.model,
    )
    return {
        "mode": "generate",
        "model": args.model,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_tokens": args.max_tokens,
        "system_prompt": bool(args.system_prompt),
        "output": result_text,
    }


async def run_extract_text(args: argparse.Namespace) -> Dict[str, Any]:
    client = await get_gemini_client()
    content = read_file_bytes(args.file)
    mime_type = guess_mime_type(args.file, args.content_type)
    result = await client.extract_text(content=content, content_type=mime_type)
    return {
        "mode": "extract-text",
        "file": args.file,
        "content_type": mime_type,
        **result,
    }


async def run_analyze_document(args: argparse.Namespace) -> Dict[str, Any]:
    client = await get_gemini_client()
    content = read_file_bytes(args.file)
    mime_type = guess_mime_type(args.file, args.content_type)
    result = await client.analyze_document(content=content, content_type=mime_type)
    return {
        "mode": "analyze-document",
        "file": args.file,
        "content_type": mime_type,
        **result,
    }


async def run_image_semantics(args: argparse.Namespace) -> Dict[str, Any]:
    client = await get_gemini_client()
    content = read_file_bytes(args.file)
    mime_type = guess_mime_type(args.file, args.content_type)
    analysis_context = {"prompt": args.prompt or "Analyze this image"}
    result = await client.analyze_image_semantics(
        content=content, content_type=mime_type, analysis_context=analysis_context
    )
    return {
        "mode": "image-semantics",
        "file": args.file,
        "content_type": mime_type,
        **result,
    }


async def run_health(args: argparse.Namespace) -> Dict[str, Any]:
    client = await get_gemini_client()
    result = await client.health_check()
    return {"mode": "health", **result}


def add_common_gen_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--prompt", required=False, default="Say hello.", help="User prompt text"
    )
    p.add_argument(
        "--system-prompt", dest="system_prompt", default=None, help="System instruction"
    )
    p.add_argument(
        "--temperature", type=float, default=0.1, help="Sampling temperature"
    )
    p.add_argument(
        "--top-p", dest="top_p", type=float, default=1.0, help="Nucleus sampling"
    )
    p.add_argument(
        "--max-tokens",
        dest="max_tokens",
        type=int,
        default=None,
        help="Max output tokens",
    )
    p.add_argument(
        "--model", default=None, help="Override model name (else uses settings)"
    )


def add_common_file_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True, help="Path to file (image or PDF)")
    p.add_argument(
        "--content-type", dest="content_type", default=None, help="MIME type override"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GeminiClient integration CLI")
    parser.add_argument(
        "mode",
        choices=[
            "generate",
            "extract-text",
            "analyze-document",
            "image-semantics",
            "health",
        ],
        help="Operation mode",
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output JSON only"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    # Sub-argument templates by mode
    # We keep one parser but add optional args based on mode at runtime
    add_common_gen_args(parser)
    add_common_file_args(parser)

    return parser


async def main_async(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    # Warn if no ADC available
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logging.getLogger(__name__).warning(
            "GOOGLE_APPLICATION_CREDENTIALS not set. Using ADC from gcloud or metadata if available."
        )

    try:
        if args.mode == "generate":
            result = await run_generate(args)
        elif args.mode == "extract-text":
            result = await run_extract_text(args)
        elif args.mode == "analyze-document":
            result = await run_analyze_document(args)
        elif args.mode == "image-semantics":
            result = await run_image_semantics(args)
        elif args.mode == "health":
            result = await run_health(args)
        else:
            parser.error(f"Unsupported mode: {args.mode}")
            return 2

        if args.as_json:
            print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))
        else:
            pretty = json.dumps(to_jsonable(result), ensure_ascii=False, indent=2)
            print(pretty)

        return 0
    except KeyboardInterrupt:
        print("Interrupted")
        return 130
    except ClientError as ce:
        logging.getLogger(__name__).error(f"ClientError: {ce}")
        return 1
    except Exception as e:
        logging.getLogger(__name__).exception("Unexpected error")
        print(f"Unexpected error: {e}")
        return 1


def main() -> None:
    # exit_code = asyncio.run(main_async(sys.argv[1:]))
    exit_code = asyncio.run(run_with_doc())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
