from html.parser import HTMLParser
import logging
import re
from typing import Optional
import urllib.parse
import urllib.request

from radioscripts.worker import Catalog


logger = logging.getLogger(__name__)


class ResourceParser(HTMLParser):
    """Simple HTML parser wrapper to extract URLs from web pages."""

    def parse(self, url: str) -> list[str]:
        """Returns list of URLs found on the web page.

        Use this method as an entrypoint.
        """
        self.reset()
        self.url = url
        self.data: list[str] = []
        with urllib.request.urlopen(url) as response:
            self.feed(response.read().decode())
        self.close()
        logger.debug('Found %d URLs on %s page', len(self.data), url)
        return self.data

    def quote(self, url: str) -> str:
        """Replaces special characters in sections of the URL using the %xx escape."""
        scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
        return urllib.parse.urlunsplit(
            (
                scheme,
                netloc,
                urllib.parse.quote(path),
                urllib.parse.quote(query, safe='='),
                urllib.parse.quote(fragment),
            )
        )


class LinksExtractor(ResourceParser):
    """Extracts URLs from hyperlinks (HTML `<a>` elements with `href` attribute)."""

    def __init__(self, pattern: str):
        super().__init__()
        self._pattern = re.compile(pattern)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        if tag == 'a':
            if href := next((value for attr, value in attrs if attr == 'href'), None):
                target_url = urllib.parse.urljoin(self.url, href)
                if self._pattern.match(target_url):
                    self.data.append(self.quote(target_url))


class UbuSoundCatalog(Catalog):
    """Represents UbuWeb Sound Catalog."""

    START_URL = 'https://www.ubu.com/sound/index.html'

    def sections(self) -> list[str]:
        """Returns list of section pages URLs which contain sounds."""
        sections_parser = LinksExtractor(r'^https://www\.ubu\.com/sound/.+')
        return sections_parser.parse(self.START_URL)

    def sounds(self, url: str) -> list[str]:
        """Returns list of sound URLs from provided page."""
        sounds_parser = LinksExtractor(r'^https://www\.ubu\.com/.+\.mp3$')
        return sounds_parser.parse(url)

    def __str__(self):
        return f'UbuWeb Sound Catalog {self.START_URL}'
