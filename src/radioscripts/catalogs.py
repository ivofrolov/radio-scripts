import contextlib
from html.parser import HTMLParser
import logging
import re
from typing import Generic, Optional, TypeVar
import urllib.parse
import urllib.request

from radioscripts.worker import Catalog


logger = logging.getLogger(__name__)


ScrapedItem = TypeVar('ScrapedItem')


class HTMLResourceParser(HTMLParser, Generic[ScrapedItem]):
    """Simple HTML parser wrapper to extract data from web pages online."""

    _data: list[ScrapedItem]

    def add_item(self, item: ScrapedItem):
        self._data.append(item)

    def parse(self, url: str) -> list[ScrapedItem]:
        """Returns some data found on a web page.

        Use this method as an entrypoint.
        """
        self.reset()
        self.url = url
        self._data = []
        with contextlib.closing(self):
            with urllib.request.urlopen(url) as response:
                self.feed(response.read().decode())
        logger.debug('Found %d items on %s page', len(self._data), url)
        return self._data


class LinksExtractor(HTMLResourceParser[str]):
    """Extracts URLs from hyperlinks (HTML `<a>` elements with `href` attribute)."""

    def __init__(self, pattern: str):
        super().__init__()
        self._pattern = re.compile(pattern)

    @staticmethod
    def quote(url: str) -> str:
        """Replaces special characters in the URL using the %xx escape sequence."""
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        if tag == 'a':
            if href := next((value for attr, value in attrs if attr == 'href'), None):
                target_url = urllib.parse.unquote(urllib.parse.urljoin(self.url, href))
                if self._pattern.match(target_url):
                    self.add_item(self.quote(target_url))


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


class IrdialCatalog(Catalog):
    """Represents Irdial (A212 version 2) Catalog."""

    START_URL = 'http://irdial.hyperreal.org/'

    def sections(self) -> list[str]:
        """Returns list of section pages URLs which contain sounds."""
        sections_parser = LinksExtractor(r'^http://irdial\.hyperreal\.org/.+/$')
        return sections_parser.parse(self.START_URL)

    def sounds(self, url: str) -> list[str]:
        """Returns list of sound URLs from provided page."""
        sounds_parser = LinksExtractor(r'^http://irdial\.hyperreal\.org/.+.mp3$')
        return sounds_parser.parse(url)

    def __str__(self):
        return f'Irdial Catalog {self.START_URL}'
