import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.shl.com/products/product-catalog/"
INDIVIDUAL_TEST_SOLUTIONS_TYPE = 1
PAGE_SIZE = 12
REQUEST_DELAY_SECONDS = 0.5
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "catalog" / "catalog.json"

TEST_TYPE_LEGEND = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}


def fetch_page(start: int) -> BeautifulSoup:
    params = {"start": start, "type": INDIVIDUAL_TEST_SOLUTIONS_TYPE}
    response = requests.get(BASE_URL, params=params, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def find_catalog_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        header = table.find("tr")
        if header and "Individual Test Solutions" in header.get_text():
            return table
    return None


def parse_table(table) -> list[dict]:
    entries = []
    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        link = cells[0].find("a")
        if not link:
            continue
        name = link.get_text(strip=True)
        url = link["href"]
        if not url.startswith("http"):
            url = f"https://www.shl.com{url}"
        type_codes = cells[3].get_text(strip=True).split()
        entries.append({"name": name, "url": url, "test_type": type_codes})
    return entries


def total_pages(soup: BeautifulSoup) -> int:
    page_links = soup.select("a[href*='start=']")
    starts = []
    for link in page_links:
        href = link["href"]
        if "type=1" not in href:
            continue
        try:
            start_val = int(href.split("start=")[1].split("&")[0])
            starts.append(start_val)
        except (IndexError, ValueError):
            continue
    return (max(starts) // PAGE_SIZE + 1) if starts else 1


def scrape_all() -> list[dict]:
    first_page = fetch_page(0)
    pages = total_pages(first_page)
    print(f"Detected {pages} pages of Individual Test Solutions")

    all_entries: list[dict] = []
    seen_urls: set[str] = set()

    table = find_catalog_table(first_page)
    if table:
        all_entries.extend(parse_table(table))

    for page_index in range(1, pages):
        start = page_index * PAGE_SIZE
        time.sleep(REQUEST_DELAY_SECONDS)
        soup = fetch_page(start)
        table = find_catalog_table(soup)
        if not table:
            print(f"Warning: no catalog table found at start={start}")
            continue
        entries = parse_table(table)
        print(f"start={start}: {len(entries)} entries")
        all_entries.extend(entries)

    deduped = []
    for entry in all_entries:
        if entry["url"] not in seen_urls:
            seen_urls.add(entry["url"])
            deduped.append(entry)

    return deduped


def main() -> None:
    entries = scrape_all()
    output = {"test_type_legend": TEST_TYPE_LEGEND, "assessments": entries}
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(entries)} assessments to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
