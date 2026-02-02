import os
from pathlib import Path
from dotenv import load_dotenv
import anthropic

def _extract_file_ids(response) -> list[str]:
    """Try to extract file_id(s) from Anthropic SDK response content blocks."""
    file_ids: list[str] = []
    for block in getattr(response, "content", []) or []:
        fid = getattr(block, "file_id", None)
        if fid:
            file_ids.append(fid)

        # some tool outputs nest content blocks; try one level deeper
        inner = getattr(block, "content", None)
        if isinstance(inner, list):
            for b2 in inner:
                fid2 = getattr(b2, "file_id", None)
                if fid2:
                    file_ids.append(fid2)
    # dedupe, keep order
    seen = set()
    uniq = []
    for fid in file_ids:
        if fid not in seen:
            uniq.append(fid)
            seen.add(fid)
    return uniq

def _download_file_bytes(client: anthropic.Anthropic, file_id: str) -> bytes:
    """
    Download file bytes. SDK method names may differ across versions.
    Try beta.files first, then files.
    """
    # 1) beta.files.download
    beta_files = getattr(getattr(client, "beta", None), "files", None)
    if beta_files and hasattr(beta_files, "download"):
        stream = beta_files.download(file_id)
        return stream.read() if hasattr(stream, "read") else bytes(stream)

    # 2) files.download (non-beta)
    files = getattr(client, "files", None)
    if files and hasattr(files, "download"):
        stream = files.download(file_id)
        return stream.read() if hasattr(stream, "read") else bytes(stream)

    raise RuntimeError("No files.download method found on this anthropic SDK client.")

def generate_pdf_via_code_execution(
    client: anthropic.Anthropic,
    out_path: str | Path = "invoice_template.pdf",
    *,
    company_name: str = "Your Company Name",
    invoice_no: str = "INV-2024-001",
) -> Path:
    """
    Generate a PDF invoice template using Anthropic Code Execution and save to local disk.
    Returns the local file path.
    """
    out_path = Path(out_path).resolve()

    prompt = f"""
Write and run Python code to generate a professional one-page PDF invoice template.

Requirements:
- Use reportlab (canvas) to generate the PDF.
- Output file must be exactly: /files/output/invoice_template.pdf
- Include: header with company name "{company_name}", invoice number "{invoice_no}",
  bill-to section, items table (3 sample rows), subtotal/tax/total, and footer.
- After creating the file, print the final output path and ensure the response includes the file output.
"""

    resp = client.beta.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1200,
        betas=["code-execution-2025-08-25"],  # code execution only
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    )

    file_ids = _extract_file_ids(resp)
    if not file_ids:
        # If no file_id came back, print text for debugging
        text_parts = []
        for b in resp.content:
            if getattr(b, "type", None) == "text":
                text_parts.append(b.text)
        raise RuntimeError(
            "PDF generated in sandbox but no file_id was returned in response.\n"
            + "\n".join(text_parts[:3])
        )

    # Usually the first file_id is our pdf
    pdf_bytes = _download_file_bytes(client, file_ids[0])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pdf_bytes)
    return out_path


if __name__ == "__main__":
    # ---- example usage ----
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(f"ANTHROPIC_API_KEY missing; tried {env_path}")

    client = anthropic.Anthropic(api_key=api_key)

    saved = generate_pdf_via_code_execution(client, "invoice_template.pdf")
    print("✅ Saved PDF to:", saved)
