from collections import deque
from concurrent.futures import Future, Executor
from contextlib import suppress
from itertools import count, zip_longest
import logging
from pathlib import Path
import random
import shutil
import tempfile
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


class Worker:
    """Compiles Radio Music module compatible stations from online catalog of sounds."""

    def __init__(
        self,
        *,
        target: Path,
        catalog: Catalog,
        banks: int,
        files: int,
        minutes: int,
        diversity: int = 5,
    ):
        self._sections: deque[str] = deque()

        self.target = target
        self.catalog = catalog
        self.banks = banks
        self.files = files
        self.minutes = minutes
        self.diversity = diversity

    def start(self, executor: Executor) -> Iterator[Future]:
        """Schedules cooperative radio stations compilation processes."""
        logger.debug(
            (
                'Starting to fill %(target)s with %(banks)d banks of %(files)d files '
                '%(minutes)d minutes each from %(catalog)s'
            ),
            vars(self),
        )

        self.enqueue_sections()
        logger.debug('%d catalog sections enqueued', len(self._sections))

        for bank in range(self.banks):
            for file in range(self.files):
                yield executor.submit(self.compose_station, bank, file, self.minutes)
        logger.debug('%d jobs pending', self.banks * self.files)

    def compose_station(self, bank: int, file: int, minutes: int):
        """Compiles radio station from samples and saves it to the target storage."""
        logger.debug(
            'Starting to compose radio station: bank %d file %d %d minutes long',
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
            logger.debug('Compiled radio station %s', program_path.name)

            stored_path = self.copy_file_safely(
                program_path, self.target / f'{bank:02}'
            )
            logger.debug('Audio saved to %s', stored_path)

    def enqueue_sections(self):
        """Loads catalog section urls to queue."""
        sections = self.catalog.sections()
        self._sections.extend(random.sample(sections, len(sections)))

    def collect_catalogs_sounds(self) -> Iterator[list[str]]:
        """Provides randomly ordered lists of sound urls from N catalog sections."""
        with suppress(IndexError):  # no sections left - no more sounds yielded
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

    def copy_file_safely(self, src: Path, dir_: Path) -> Path:
        """Copies file to a directory without overwriting an existing
        file. Stores the provided file under a new name in case of
        conflict.
        """
        dir_.mkdir(exist_ok=True)
        dst = dir_ / src.name
        for num in count(1):
            if not dst.exists():
                break
            # append something like a version to the filename
            dst = dst.with_stem(src.stem + '-' + str(num))
        shutil.copyfile(src, dst)
        return dst
