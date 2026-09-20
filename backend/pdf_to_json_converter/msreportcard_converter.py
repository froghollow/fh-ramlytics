"""Convert E*TRADE ``*.msReportCard.pdf`` files into ``*.msReportCard.json``.

Text is extracted locally from each PDF with ``pypdf``, then handed to an
Amazon Bedrock model (via the OpenAI Agents SDK's ``LitellmModel``) which
maps the free-form report-card text onto the JSON schema demonstrated by
``IDMO.msReportCard.json`` in this same folder.

Usage:
    uv run python pdf_to_json_converter/msreportcard_converter.py \
        /home/richa/projects/scratchpad/ingest/2026-08-28
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv(override=True)
import boto3

from ramlytics_yfinance import yf_search

def enhance_top10(top10_list):
    enhanced_top10 = []

    for holding in top10_list:
        quote = yf_search(holding['name'])
        if quote:
            holding['symbol'] = quote['symbol']
            holding['sector'] = quote['sector']
            holding['industry'] = quote['industry']
        else:
            #retry with first word in the holding's name
            first_word = holding['name'].split()[0]
            quote = yf_search(first_word)
            if quote:
                holding['symbol'] = quote['symbol']
                holding['sector'] = quote['sector']
                holding['industry'] = quote['industry']
        enhanced_top10.append(holding)
        #print(holding)
    return enhanced_top10


# ---------------------------------------------------------------------------
# Bedrock / LiteLLM configuration
# ---------------------------------------------------------------------------
REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
os.environ["AWS_REGION_NAME"] = REGION  # LiteLLM's preferred variable
os.environ["AWS_REGION"] = REGION  # Boto3 standard
os.environ["AWS_DEFAULT_REGION"] = REGION  # Fallback

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
MODEL = f"bedrock/{BEDROCK_MODEL_ID}"

THIS_DIR = Path(__file__).resolve().parent
SCHEMA_EXAMPLE_PATH = THIS_DIR / "IDMO.msReportCard.json"

INSTRUCTIONS = """You convert E*TRADE Exchange Traded Fund Report Card text into structured JSON.

You will be given the raw text extracted from a *.msReportCard.pdf file. Produce a JSON object
that follows EXACTLY the same keys, nesting, and structure as this example (the example's values
belong to a different fund and must not be reused):

{example_json}

Rules:
- Use the ticker symbol found in the source text for "symbol".
- "asof_dt" is the "Average Annual Return & Tax Analysis as of" date in MM/DD/YY format
  (this is usually a month-end date, e.g. 07/31/26), NOT the "Report created on" date and NOT the
  "Close on" date.
- Morningstar star ratings (e.g. "morningstar_star_rating" and "rating" fields) must use the
  literal capital letter "H" repeated once per star (e.g. 5 stars = "HHHHH"), not the "\u2605" star
  glyph.
- Numbers must be plain JSON numbers (no "%", "$", or "," characters); percentages are represented
  as their numeric value (e.g. 23.91 for 23.91%).
- If a value is not present in the source text, use null.
- Respond with ONLY the JSON object, no markdown fences, no commentary.
"""


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract concatenated text from every page of a PDF."""
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model response: {text[:200]!r}")
    return json.loads(cleaned[start : end + 1])

async def convert_pdf_text_to_json(pdf_text: str) -> dict:
    """Send extracted PDF text to Bedrock (via LitellmModel) and return parsed JSON."""
    from agents import Agent, ModelSettings, Runner
    from agents.extensions.models.litellm_model import LitellmModel

    example_json = SCHEMA_EXAMPLE_PATH.read_text()
    agent = Agent(
        name="msReportCard Converter",
        instructions=INSTRUCTIONS.format(example_json=example_json),
        model=LitellmModel(model=MODEL),
        model_settings=ModelSettings(max_tokens=4096),
    )
    result = await Runner.run(agent, input=pdf_text)
    return _parse_json_response(result.final_output)


async def convert_file(pdf_path: Path, json_path: Path) -> None:
    pdf_text = extract_pdf_text(pdf_path)
    data = await convert_pdf_text_to_json(pdf_text)

    if "top_10_holdings" in data:
        data["top_10_holdings"] = enhance_top10(data["top_10_holdings"])

    # The PDF header ticker carries an exchange suffix (e.g. "QQQUSQ"); the filename is authoritative.
    data["symbol"] = pdf_path.name.split(".")[0]
    json_path.write_text(json.dumps(data, indent=4) + "\n")
    print(f"Wrote {json_path}")
    # upload .json to S3 to be processed by ObjectCreated-initiated Lambda
    s3_bucket = os.getenv("S3_BUCKET", "fh-danelfin-289755104220")
    s3_inbound_folder = "inbound/"
    s3_client = boto3.client("s3")
    s3_key = f"{s3_inbound_folder}{json_path.name}"
    s3_client.upload_file(str(json_path), s3_bucket, s3_key)

    # move .pdf to subfolder with the current date
    subfolder = pdf_path.parent / datetime.now().strftime("%Y-%m-%d")
    subfolder.mkdir(exist_ok=True)
    new_pdf_path = subfolder / pdf_path.name
    pdf_path.rename(new_pdf_path)


async def convert_folder(
    input_folder: Path, output_folder: Path, overwrite: bool = False
) -> None:
    pdf_files = sorted(input_folder.glob("*.msReportCard.pdf"))
    if not pdf_files:
        print(f"No *.msReportCard.pdf files found in {input_folder}")
        return

    for pdf_path in pdf_files:
        json_name = pdf_path.with_suffix("").with_suffix(".msReportCard.json").name
        json_path = output_folder / json_name
        if json_path.exists() and not overwrite:
            print(f"Skipping (exists): {json_path}")
            continue
        try:
            await convert_file(pdf_path, json_path)
        except Exception as exc:  # noqa: BLE001 - report and continue with next file
            print(f"Error converting {pdf_path}: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_folder",
        nargs="?",
        default="../pdf",
        help="Input folder containing *.msReportCard.pdf files",
    )
    parser.add_argument(
        "output_folder",
        nargs="?",
        default=f"../inbound/{datetime.now().strftime('%Y-%m-%d')}",
        help="Output folder for *.msReportCard.json files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing *.msReportCard.json files",
    )
    args = parser.parse_args()

    input_folder = Path(args.input_folder)
    if not input_folder.is_dir():
        parser.error(f"Not a directory: {input_folder}")

    output_folder = Path(args.output_folder)
    if not output_folder.is_dir():
        output_folder.mkdir(exist_ok=True)
        print(f"Created {output_folder}")
        # parser.error(f"Not a directory: {output_folder}")

    asyncio.run(
        convert_folder(input_folder, output_folder, overwrite=args.overwrite)
    )


if __name__ == "__main__":
    main()
