#!/usr/bin/env python3
"""
make_image_fixtures.py — Regenerate the image-mode eval fixtures in evals/files/.

Writes two documents that have no text layer, so classify.py must send them to Jev as images:
  * scanned_eob.jpg          a photographed insurance EOB (JPEG)
  * scanned_auto_renewal.pdf a scanned auto-insurance letter (PDF holding only a page image)

Placeholder household only (Alex, Sam, Household); no real personal data.

Usage: python make_image_fixtures.py
Output: {"written": [paths]} on stdout. Exit 0 on success.
"""

import json
import os

import pymupdf

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

EOB = """AETNA
Health insurance plans  |  PO Box 981106, El Paso TX 79998

EXPLANATION OF BENEFITS                        Statement Date: May 2, 2025
THIS IS NOT A BILL

Member: Sam Example            Member ID: W123456789
Date of birth: 01/01/1980       Group: EXAMPLE CORP

Sam Example
42 Placeholder Lane
Springfield, IL 62701

Claim 0001   Provider: Springfield Family Clinic
Service date: 04/14/2025
Amount billed      $240.00
Plan discount      -$96.00
Plan paid          $120.00
You may owe        $24.00

Questions? Call 1-800-555-0100 or visit aetna.com"""

AUTO = """PROGRESSIVE
Progressive Casualty Insurance Company

June 10, 2025

Alex Example
42 Placeholder Lane
Springfield, IL 62701

Re: Your auto policy renewal       Policy number 99887766

Dear Alex Example,

Your auto policy renews on July 15, 2025. Your new six-month premium
is $612.40, due by July 1, 2025. Vehicle: 2019 Example Sedan.

No action is needed if you are paying by automatic withdrawal.

Thank you for choosing Progressive."""


def page_image(text: str, dpi: int) -> pymupdf.Pixmap:
    """Typeset text on a letter page and rasterize it, the way a scanner would."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(pymupdf.Rect(54, 54, 558, 760), text, fontsize=11, fontname="cour")
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    doc.close()
    return pix


def main() -> None:
    written = []
    eob = os.path.join(FILES_DIR, "scanned_eob.jpg")
    with open(eob, "wb") as f:
        f.write(page_image(EOB, 120).tobytes("jpeg", jpg_quality=80))
    written.append(eob)

    auto = os.path.join(FILES_DIR, "scanned_auto_renewal.pdf")
    pix = page_image(AUTO, 150)
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=pix.tobytes("jpeg", jpg_quality=80))
    doc.save(auto, garbage=4, deflate=True)
    doc.close()
    written.append(auto)

    json.dump({"written": written}, __import__("sys").stdout)
    print()


if __name__ == "__main__":
    main()
