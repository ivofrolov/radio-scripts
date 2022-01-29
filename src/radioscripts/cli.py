import argparse
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
import logging
from pathlib import Path
import sys

from radioscripts.audio import calculate_required_space
from radioscripts.ubuweb import UbuSoundCatalog
from radioscripts.worker import Catalog, Worker


catalogs: dict[str, type[Catalog]] = {
    'ubuweb': UbuSoundCatalog,
}

parser = argparse.ArgumentParser(description='Compose radio stations broadcast')
parser.add_argument('--debug', action='store_true', help='Enable debugging output')
parser.add_argument(
    '-c',
    '--catalog',
    choices=catalogs.keys(),
    default=next(iter(catalogs.keys()), None),
    help='Catalog to download samples from (default: %(default)s)',
)
parser.add_argument(
    '-b',
    '--banks',
    type=int,
    default=16,
    help='Number of banks to fill (default: %(default)s)',
)
parser.add_argument(
    '-f',
    '--files',
    type=int,
    default=12,
    help='Number of stations per bank (default: %(default)s)',
)
parser.add_argument(
    '-m',
    '--minutes',
    type=int,
    default=30,
    help='Audio file duration (default: %(default)s)',
)
parser.add_argument('path', type=Path, help='Path to SD card')


def log_uncaught_exception(type_, value, traceback):
    logging.critical('%s\nProgram terminated', value)


def entrypoint():
    """Compiles Radio Music module compatible stations from online catalog of sounds."""
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(threadName)s %(name)s %(message)s',
        )
    else:
        logging.basicConfig(level=logging.CRITICAL, format='%(message)s')
        sys.excepthook = log_uncaught_exception

    volume = calculate_required_space(args.banks, args.files, args.minutes)
    if volume > 1024 * 1024 * 1024:
        label = 'Gb'
        volume /= 1024 * 1024 * 1024
    else:
        label = 'Mb'
        volume /= 1024 * 1024
    print('Space required on SD card is', f'{volume:.3f}', label)

    worker = Worker(
        target=args.path.resolve(strict=True),
        catalog=catalogs[args.catalog](),
        banks=args.banks,
        files=args.files,
        minutes=args.minutes,
    )
    with ThreadPoolExecutor(thread_name_prefix='Composer') as executor:
        done, _ = wait(worker.start(executor), return_when=FIRST_EXCEPTION)
        for future in done:
            # resolve future to see if exception occured
            future.result()
