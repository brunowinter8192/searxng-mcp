# INFRASTRUCTURE
import logging
import os
import re
import time

import requests
from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ORCHESTRATOR
def download_pdf_workflow(url: str, output_dir: str = "/tmp") -> list[TextContent]:
    logger.info("Downloading PDF: %s", url)
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.HTTPError as e:
        return [TextContent(type="text", text=f"Error downloading {url}: HTTP {e.response.status_code}")]
    except requests.RequestException as e:
        return [TextContent(type="text", text=f"Error downloading {url}: {e}")]

    content_type = response.headers.get("Content-Type", "")
    if "application/pdf" not in content_type:
        return [TextContent(type="text", text=f"Error: URL did not return a PDF (Content-Type: {content_type})")]

    filename = extract_filename(response, url)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    try:
        write_pdf(response, output_path)
    except OSError as e:
        return [TextContent(type="text", text=f"Error writing file {output_path}: {e}")]

    file_size = os.path.getsize(output_path)
    size_str = format_size(file_size)
    logger.info("PDF saved: %s (%s)", output_path, size_str)
    return [TextContent(type="text", text=f"Downloaded: {output_path} ({size_str})")]


# FUNCTIONS

# Extract filename from Content-Disposition header, URL path, or generate one
def extract_filename(response: requests.Response, url: str) -> str:
    content_disposition = response.headers.get("Content-Disposition", "")
    if content_disposition:
        match = re.search(r'filename[^;=\n]*=[\"\']?([^;\"\'\n]+)', content_disposition)
        if match:
            name = match.group(1).strip()
            if name:
                return name

    path = url.split("?")[0].rstrip("/")
    basename = path.split("/")[-1]
    if basename and basename.lower().endswith(".pdf"):
        return basename

    return f"download_{int(time.time())}.pdf"


# Write streamed response content to file
def write_pdf(response: requests.Response, output_path: str) -> None:
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


# Format byte count as human-readable KB or MB string
def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / 1024:.1f} KB"
