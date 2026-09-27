"""
Bible service - Business logic layer

This demonstrates how to implement your core business logic
separately from MCP/REST concerns.
"""

import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class BibleService:
    """
    Handles Bible passage operations

    This is your business logic layer - it knows nothing about
    MCP or REST APIs, just pure Bible passage functionality.
    """

    BASE_URL = "https://www.biblegateway.com/passage/"
    DEFAULT_VERSION = "ESV"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize Bible service

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def fetch_passage(
        self,
        passage: str,
        version: str = DEFAULT_VERSION,
    ) -> dict:
        """
        Fetch a Bible passage from BibleGateway.

        Args:
            passage: Bible reference(s) (e.g., "John 3:16", "Romans 8", or "John 3:16; Romans 8:28-30")
            version: Bible translation version (e.g., "ESV", "NIV", "KJV")

        Returns:
            dict: Result containing passage text or error
            {
                "success": bool,
                "passage": str,
                "version": str,
                "text": str | None,
                "error": str | None
            }

        Example:
            result = await service.fetch_passage("John 3:16", "ESV")
            if result["success"]:
                print(result["text"])

            # Multiple passages
            result = await service.fetch_passage("John 3:16; Romans 8:28", "ESV")
        """
        logger.info(
            f"Fetching Bible passage: {passage} ({version})"
        )

        try:
            # Split multiple passages on semicolon
            passages = [p.strip() for p in passage.split(";") if p.strip()]

            if len(passages) > 1:
                # Fetch multiple passages
                results = []
                for single_passage in passages:
                    html = await self._fetch_html(single_passage, version)
                    text = self._parse_passage(html)
                    if text:
                        results.append(f"{single_passage}\n{text}")
                    else:
                        results.append(f"{single_passage}\n[Could not parse passage text]")

                combined_text = "\n\n".join(results)

                logger.info(
                    f"Successfully fetched {len(passages)} passages: {passage} ({version}) - {len(combined_text)} characters"
                )

                return {
                    "success": True,
                    "passage": passage,
                    "version": version,
                    "text": combined_text,
                    "error": None,
                }
            else:
                # Single passage (existing logic)
                # Fetch the page
                html = await self._fetch_html(passage, version)

                # Parse the passage
                text = self._parse_passage(html)

                if not text:
                    return {
                        "success": False,
                        "passage": passage,
                        "version": version,
                        "text": None,
                        "error": (
                            f"Could not parse passage text for '{passage}' with version '{version}'. "
                            f"Please verify the passage reference exists and '{version}' is a valid BibleGateway version code "
                            f"(e.g., LUTH1545 for Luther 1545, HOF, SCH2000, LSG, ESV, NIV, etc.)."
                        ),
                    }

                logger.info(
                    f"Successfully fetched passage: {passage} ({version}) - {len(text)} characters"
                )

                return {
                    "success": True,
                    "passage": passage,
                    "version": version,
                    "text": text,
                    "error": None,
                }

        except Exception as e:
            logger.error(
                f"Failed to fetch passage: {passage} ({version}) - {str(e)}"
            )

            return {
                "success": False,
                "passage": passage,
                "version": version,
                "text": None,
                "error": str(e),
            }

    async def _fetch_html(self, passage: str, version: str) -> str:
        """
        Fetch HTML from BibleGateway.

        Args:
            passage: Bible reference
            version: Bible version

        Returns:
            str: HTML content

        Raises:
            httpx.HTTPError: If request fails
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        params = {"search": passage, "version": version}

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; PluggableMCPBridge/1.0)",
        }

        response = await self._client.get(
            self.BASE_URL, params=params, headers=headers
        )

        response.raise_for_status()
        return response.text

    def _parse_passage(self, html: str) -> str | None:
        """
        Parse passage text from HTML.

        Extracts the passage text, removes unwanted elements like
        footnotes, cross-references, and section headers.

        Args:
            html: HTML content from BibleGateway

        Returns:
            str | None: Cleaned passage text or None if parsing fails
        """
        soup = BeautifulSoup(html, "html.parser")

        # Find the main passage container
        passage_div = soup.find("div", class_="passage-text")
        if not passage_div:
            return None

        # Remove unwanted elements
        for unwanted in passage_div.find_all(
            ["div", "h4"], class_=["footnotes", "crossrefs", "passage-other-trans"]
        ):
            unwanted.decompose()

        # Remove section headers
        for header in passage_div.find_all("h3"):
            header.decompose()

        # Remove footnote/cross-reference links
        for tag in passage_div.find_all("a"):
            tag.decompose()

        # Remove footnote markers (sup tags)
        for sup in passage_div.find_all(
            "sup", class_=["footnote", "crossreference"]
        ):
            sup.decompose()

        # Collect verses
        verses = []

        # Handle regular paragraphs
        for p in passage_div.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                verses.append(text)

        # Handle poetry (like Psalms)
        for poetry_div in passage_div.find_all("div", class_="poetry"):
            for line in poetry_div.find_all("p", class_="line"):
                text = line.get_text(" ", strip=True)
                if text:
                    verses.append(text)

        scripture = "\n".join(verses)

        if not scripture.strip():
            return None

        return scripture