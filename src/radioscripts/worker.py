from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import suppress
from itertools import zip_longest
import logging
from pathlib import Path
import random
import shutil
import tempfile
import threading
from typing import Iterable, Iterator, Protocol
import urllib.request

from radioscripts.audio import SoxError, make_radio_program, measure_durations


logger = logging.getLogger(__name__)


class Catalog(Protocol):
    """Represents sounds catalog."""

    def sections(self) -> list[str]:
        """Should return list of section pages urls which contain sounds."""
        ...

    def sounds(self, url: str) -> list[str]:
        """Should return list of sound urls from provided page."""
        ...


class Worker(threading.Thread):
    """Compiles Radio Music module compatible stations from online catalog of sounds."""

    def __init__(
        self,
        target: Path,
        catalog: Catalog,
        banks: int,
        files: int,
        minutes: int,
        *,
        diversity: int = 5,
    ):
        super().__init__()

        self._sections: deque[str] = deque()

        self.target = target
        self.catalog = catalog
        self.banks = banks
        self.files = files
        self.minutes = minutes
        self.diversity = diversity

    def run(self):
        """Executes cooperative samples compilation processes."""
        logger.debug(
            (
                'Starting filling %(target)s with %(banks)d banks of %(files)d files '
                '%(minutes)d minutes each from %(catalog)s'
            ),
            vars(self),
        )

        self.enqueue_sections()
        logger.debug('%d sections enqueued', len(self._sections))

        with ThreadPoolExecutor() as executor:
            futures: list[Future] = []
            for bank in range(self.banks):
                for file in range(self.files):
                    executor.submit(self.compose_station, bank, file, self.minutes)

            wait(futures)

        logger.debug('Done')

    def compose_station(self, bank: int, file: int, minutes: int):
        """Compiles radio station and saves it in target storage."""
        logger.debug(
            'Starting radio station composing: bank %d file %d %d minutes long',
            bank,
            file,
            minutes,
        )

        samples_urls = self.choose_samples_urls(self.collect_catalogs_sounds())
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = self.collect_samples(
                duration=minutes * 60, urls=samples_urls, dir_=Path(tmpdir)
            )

            program_path = Path(tmpdir) / f'{file:02}.wav'
            make_radio_program(samples, program_path)
            if not program_path.exists():
                return
            logger.debug('Compiled radio station %s', program_path.name)

            bank_path = self.target / f'{bank:02}'
            bank_path.mkdir(exist_ok=True)

            shutil.copyfile(program_path, bank_path / program_path.name)
            logger.debug('Radio station saved to %s', bank_path / program_path.name)

        logger.debug('Done')

    def enqueue_sections(self):
        """Loads catalog section urls to queue."""
        sections = self.catalog.sections()
        self._sections.extend(random.sample(sections, len(sections)))

    def collect_catalogs_sounds(self) -> Iterator[list[str]]:
        """Provides randomly ordered lists of sound urls from N catalog sections."""
        with suppress(IndexError):  # no section no sounds
            for _ in range(self.diversity):
                sounds = self.catalog.sounds(self._sections.popleft())
                yield random.sample(sounds, len(sounds))

    def choose_samples_urls(
        self, catalogs_sounds: Iterable[list[str]]
    ) -> Iterator[str]:
        """Provides randomly ordered samples from each of the catalog sections."""
        for maybe_urls in zip_longest(*catalogs_sounds):
            yield from filter(None, random.sample(maybe_urls, len(maybe_urls)))

    def collect_samples(
        self, duration: float, urls: Iterable[str], dir_: Path, *, skips_count: int = 5
    ) -> Iterator[Path]:
        """Downloads and yields samples while they all fit provided duration."""
        remaining = duration
        for url in urls:
            filename = Path(url).name
            filepath = dir_ / filename

            urllib.request.urlretrieve(url, filepath)
            logger.debug('%s downloaded', url)

            try:
                file_duration = next(iter(measure_durations(filepath)))
            except SoxError as exc:
                logger.debug('%s discarded due to the error\n%s', filename, exc)
                continue

            if remaining - file_duration <= 0:
                # try to find another file that fits remaining length
                skips_count -= 1
                if skips_count <= 0:
                    break
                logger.debug('%s skipped as too long', filename)
                continue

            remaining -= file_duration
            yield filepath
