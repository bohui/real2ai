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


class DocumentSummaryMarkdown(BaseModel):
    content_md: str
    diagram: list[Diagram]


class DocumentContentMarkdown(BaseModel):
    content_md: str


class DiagramList(BaseModel):
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


PROMPT_DOTSOCR = """
Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]

2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].

3. Text Extraction & Formatting Rules:
    - Picture: For the 'Picture' category, the text field should be omitted.
    - Formula: Format its text as LaTeX.
    - Table: Format its text as HTML.
    - All Others (Text, Title, etc.): Format their text as Markdown.

4. Constraints:
    - The output text must be the original text from the image, with no translation.
    - All layout elements must be sorted according to human reading order.

5. Final Output: The entire output must be a single JSON object."""


PROMPT_HTML = """
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


PROMPT_MD = """
PDF to Markdown with layout metadata and diagram indexing

Goal
- Produce a single JSON object matching the schema {"content_md": string, "diagram": [{"type": string, "page": number}]}
- The string field must contain the full document as Markdown (content_md)
- The array must list all detected diagrams/images with their classified type and page (diagram)

Text extraction and layout rules
- Read in human reading order
- Categories and formatting:
  - Title/Section-header/Text/Caption/Footnote/List-item -> Markdown
  - Formula -> LaTeX ($...$ or $$...$$)
  - Table -> GitHub Markdown table
  - Picture -> do not OCR text
- Preserve paragraphs, lists, headings (map Title→#, Section-header→##/###), footnotes as Markdown
- When available, include lightweight layout metadata as HTML comments on their own line immediately before the element:
  <!-- page: {page_number} bbox: [x1,y1,x2,y2] category: {Category} -->

Diagram detection and cross-referencing
- Detect and classify all visual elements that are diagrams/images
- Allowed types (must use exactly one of): site_plan, sewer_diagram, service_location_diagram, flood_map, bushfire_map, title_plan, survey_diagram, floor_plan, elevation, unknown
- For every detected diagram, insert a one-line placeholder in content_md at the correct position:
  [diagram:id=fig-XXX type=TYPE page=P]
  - Optional caption on the next line if present in the source
- For each placeholder, add one entry to the diagram array with the same TYPE and P (page)
- Ensure every diagram listed in the array has exactly one matching placeholder in content_md

Output format
- Return a single JSON object that conforms to the schema DocumentSummaryMarkdown:
  - content_md: the full Markdown with placeholders, headings, lists, tables, formulas, and layout comments
  - diagram: a list of objects {"type": TYPE, "page": P}
- Do not add any extra fields

Example (illustrative only)
{
  "content_md": "# Document Title\n\n<!-- page: 1 bbox: [10,20,590,70] category: Title -->\n\n## Section\n\n<!-- page: 1 bbox: [12,90,585,160] category: Text -->\nParagraph text...\n\n[diagram:id=fig-001 type=floor_plan page=3]\nOptional caption here.\n\n",
  "diagram": [
    {"type": "floor_plan", "page": 3}
  ]
}
"""

PROMPT_MD_LAYOUT_ONLY = """
    PDF to Markdown conversion (layout only, compact)

    Goal
    - Return ONLY a JSON object with one field: content_md (string)
    - Produce full document as Markdown in human reading order

    Formatting rules
    - Caption/Title/Section-header/Text/Caption/Footnote/List-item/Page-footer/Page-header -> Markdown
    - Formula -> LaTeX ($...$ or $$...$$)
    - Table -> GitHub Markdown table
    - Preserve paragraphs, lists, heading levels (#, ##, ###), and footnotes
    - Optionally include page numbers as HTML comments on their own line like: <!-- page: X -->
      but DO NOT include bbox

    Output schema
    - JSON with exactly one key: content_md
    - No other fields
    """
PROMPT_DIAGRAMS_ONLY = """
    Diagram detection only

    Goal
    - Return ONLY a JSON object with one key: diagram (array)
    - Each item: {"type": one of [site_plan, sewer_diagram, service_location_diagram, flood_map, bushfire_map, title_plan, survey_diagram, floor_plan, elevation, unknown], "page": integer}
    - Identify all visual elements that correspond to diagrams/images in the document
    - Do not include any other keys or textual content

    Notes
    - Use 'unknown' if unsure
    - Page numbers are 1-based
    """

PROMPT_MD_LAYOUT_ONLY_V2 = """
    PDF to Markdown conversion from PDF and provided plain text (layout-focused, compact)

    Output
    - Return ONLY the Markdown string as plain text (no JSON, no code fences, no extra commentary)

    Inputs
    - You are given: (1) the PDF content, and (2) the full plain text extracted via MuPDF
    - Use the MuPDF text as the authoritative source for textual content
    - Use the PDF to infer structure (headings, lists, tables) and reading order

    Formatting rules
    - Map headings: Title -> #, Section-header -> ##/### as appropriate
    - Preserve paragraphs and list structure in Markdown
    - Formula -> LaTeX ($...$ or $$...$$)
    - Tables -> GitHub Markdown tables
    - Footnotes, captions -> Markdown
    - You MAY include page references as HTML comments on their own line: <!-- page: X -->
    - DO NOT include any bounding boxes or coordinates
    - DO NOT include any diagram/image placeholders

    Constraints
    - Output must be a single Markdown string only
    - No JSON keys or additional fields
    """

PROMPT = PROMPT_MD
file_path = "../test_files/1690959428-7812-ContractforSale.pdf"
mime_type = "application/pdf"
full_text_path = "../test_files/contract.txt"

# file_path = "../test_files/diagram1.png"
# mime_type = "image/png"


async def run_with_doc():

    with open(file_path, "rb") as f:
        file_bytes = f.read()
    # Create the document content
    document_content = Part.from_bytes(data=file_bytes, mime_type=mime_type)
    client = await get_gemini_client()

    # 0) Generate Markdown layout-only as a raw string using MuPDF text as input context
    mupdf_text = ""
    try:
        if os.path.exists(full_text_path):
            with open(full_text_path, "r", encoding="utf-8", errors="ignore") as ft:
                mupdf_text = ft.read()
    except Exception:
        mupdf_text = ""

    ### Still truncated at the end, just ignore this logic at the moment
    if mupdf_text:
        v2_prompt = Part.from_text(text=PROMPT_MD_LAYOUT_ONLY_V2)
        v2_text_part = Part.from_text(
            text=f"MuPDF full text (use for content fidelity):\n\n{mupdf_text}"
        )
        v2_contents = [
            Content(role="user", parts=[document_content, v2_text_part, v2_prompt])
        ]
        v2_config = GenerateContentConfig(
            temperature=0.2,
            top_p=1,
            seed=0,
            max_output_tokens=65535,
            safety_settings=[
                SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                ),
                SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                ),
                SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
            response_mime_type="text/plain",
        )

        v2_result = client.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=v2_contents,
            config=v2_config,
        )
        layout_only_md = v2_result.text
        with open("../test_files/contract_layout_only.md", "w") as f:
            f.write(layout_only_md)

    # prompt = Part.from_text(text=PROMPT_MD)
    # contents = [Content(role="user", parts=[document_content, prompt])]
    # generate_summary_config = GenerateContentConfig(
    #     temperature=0.2,
    #     top_p=1,
    #     seed=0,
    #     max_output_tokens=65535,
    #     safety_settings=[
    #         SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    #         SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    #         SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    #         SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    #     ],
    #     response_mime_type="application/json",
    #     response_schema=DocumentSummaryMarkdown,
    # )
    # result_text = client.client.models.generate_content(
    #     model="gemini-2.5-flash",
    #     contents=contents,
    #     config=generate_summary_config,
    # )
    # dict_result = json.loads(result_text.text)
    # with open("../test_files/contract_summary.html", "w") as f:
    #     f.write(dict_result["content_html"])

    # print(dict_result["diagram"])
    # print(result_text.text)

    # 1) Generate Markdown content only (no bbox, no diagram placeholders)
    # PROMPT_MD_LAYOUT_ONLY = """
    # PDF to Markdown conversion (layout only, compact)

    # Goal
    # - Return ONLY a JSON object with one field: content_md (string)
    # - Produce full document as Markdown in human reading order

    # Formatting rules
    # - Caption/Title/Section-header/Text/Caption/Footnote/List-item/Page-footer/Page-header -> Markdown
    # - Formula -> LaTeX ($...$ or $$...$$)
    # - Table -> GitHub Markdown table
    # - Preserve paragraphs, lists, heading levels (#, ##, ###), and footnotes
    # - Optionally include page numbers as HTML comments on their own line like: <!-- page: X -->
    #   but DO NOT include bbox

    # Output schema
    # - JSON with exactly one key: content_md
    # - No other fields
    # """

    # md_prompt = Part.from_text(text=PROMPT_MD_LAYOUT_ONLY)
    # md_contents = [Content(role="user", parts=[document_content, md_prompt])]
    # md_config = GenerateContentConfig(
    #     temperature=0.2,
    #     top_p=1,
    #     seed=0,
    #     max_output_tokens=65535,
    #     safety_settings=[
    #         SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    #         SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    #         SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    #         SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    #     ],
    #     response_mime_type="application/json",
    #     response_schema=DocumentContentMarkdown,
    # )

    # md_result = client.client.models.generate_content(
    #     model="gemini-2.5-flash",
    #     contents=md_contents,
    #     config=md_config,
    # )
    # md_obj = json.loads(md_result.text)
    # with open("../test_files/contract_summary.md", "w") as f:
    #     f.write(md_obj["content_md"])

    # 2) Detect diagrams only
    PROMPT_DIAGRAMS_ONLY = """
    Diagram detection only

    Goal
    - Return ONLY a JSON object with one key: diagram (array)
    - Each item: {"type": one of [site_plan, sewer_diagram, service_location_diagram, flood_map, bushfire_map, title_plan, survey_diagram, floor_plan, elevation, unknown], "page": integer}
    - Identify all visual elements that correspond to diagrams/images in the document
    - Do not include any other keys or textual content

    Notes
    - Use 'unknown' if unsure
    - Page numbers are 1-based
    """

    diag_prompt = Part.from_text(text=PROMPT_DIAGRAMS_ONLY)
    diag_contents = [Content(role="user", parts=[document_content, diag_prompt])]
    diag_config = GenerateContentConfig(
        temperature=0,
        top_p=1,
        seed=0,
        max_output_tokens=8192,
        safety_settings=[
            SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        response_mime_type="application/json",
        response_schema=DiagramList,
    )

    diag_result = client.client.models.generate_content(
        model="gemini-2.5-flash",
        contents=diag_contents,
        config=diag_config,
    )
    diag_obj = json.loads(diag_result.text)

    with open("../test_files/contract_summary.diagrams.json", "w") as f:
        json.dump(diag_obj, f, ensure_ascii=False, indent=2)

    print(diag_obj.get("diagram", []))
    # For debugging
    # print(md_result.text)
    # print(diag_result.text)


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
