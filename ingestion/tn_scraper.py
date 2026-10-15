# ingestion/tn_scraper.py
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console

from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
console = Console()


class TNAgricultureScraper:
    def __init__(self, target_url: str = settings.TN_PORTAL_URL, output_dir: Path = settings.DATA_DIR):
        self.target_url = target_url
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def _extract_scheme_detail(self, page: Page, detail_url: str, title: str) -> Dict[str, Any]:
        """Visits scheme_details.php and extracts all structured table keys."""
        logger.info(f"Extracting details: {title}")
        try:
            await page.goto(detail_url, timeout=settings.PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            extracted_fields: Dict[str, str] = {}

            # Parse all key-value rows from tables
            for row in soup.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    k = self._clean_text(cells[0].get_text()).rstrip(":")
                    v = self._clean_text(cells[1].get_text())
                    if k and v:
                        extracted_fields[k] = v

            full_text = self._clean_text(soup.get_text())

            # Map the exact portal keys discovered from inspection
            return {
                "title": extracted_fields.get("Scheme Title/Name", title),
                "url": detail_url,
                "department": extracted_fields.get("Concerned Department", "Agriculture and Farmers Welfare Department"),
                "organisation": extracted_fields.get("Organisation Name", "Not specified"),
                "sponsored_by": extracted_fields.get("Sponsered By", "State Government"),
                "funding_pattern": extracted_fields.get("Funding Pattern", "Not specified"),
                "beneficiary": extracted_fields.get("Beneficiaries", "Farmers"),
                "scheme_type": extracted_fields.get("Scheme Type", "Not specified"),
                "benefits": extracted_fields.get("Types of Benefits", "Not specified"),
                "description": extracted_fields.get("Description", "Not specified"),
                "how_to_apply": extracted_fields.get("How To avail", "Not specified"),
                "uploaded_file": extracted_fields.get("Uploaded File", ""),
                "all_raw_fields": extracted_fields,
                "full_text_snapshot": full_text[:4000]
            }

        except Exception as e:
            logger.error(f"Error fetching scheme details from {detail_url}: {e}")
            return {
                "title": title,
                "url": detail_url,
                "department": "Agriculture and Farmers Welfare Department",
                "beneficiary": "Farmers",
                "benefits": "Not specified",
                "description": "Not specified",
                "how_to_apply": "Not specified",
                "all_raw_fields": {},
                "full_text_snapshot": ""
            }

    async def scrape_all(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Discovers all real scheme URLs matching `scheme_details.php?id=`
        and scrapes each scheme's full data.
        """
        all_schemes: List[Dict[str, Any]] = []

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=settings.SCRAPE_HEADLESS,
                args=["--ignore-certificate-errors"]
            )
            context = await browser.new_context(
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            logger.info(f"Accessing scheme listing: {self.target_url}")
            await page.goto(self.target_url, timeout=settings.PAGE_TIMEOUT_MS, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            scheme_links: List[Dict[str, str]] = []

            # Only match genuine scheme detail links (scheme_details.php?id=...)
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = self._clean_text(a.get_text())

                if "scheme_details.php?id=" in href:
                    full_url = urljoin(self.target_url, href)
                    if not any(item["url"] == full_url for item in scheme_links):
                        scheme_links.append({
                            "title": text or "TN Scheme",
                            "url": full_url
                        })

            logger.info(f"Discovered {len(scheme_links)} genuine Agriculture Schemes on portal.")

            target_list = scheme_links[:limit] if limit else scheme_links

            for idx, item in enumerate(target_list, start=1):
                scheme_data = await self._extract_scheme_detail(page, item["url"], item["title"])
                scheme_data["scheme_id"] = f"TN-AGRI-{idx:03d}"
                all_schemes.append(scheme_data)

            await browser.close()

        # Save to raw JSON
        out_file = self.output_dir / "tn_agriculture_schemes.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_schemes, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(all_schemes)} genuine schemes to: {out_file}")
        return all_schemes


if __name__ == "__main__":
    scraper = TNAgricultureScraper()
    # Let's test with 5 real schemes
    asyncio.run(scraper.scrape_all(limit=5))