import argparse
from concurrent.futures import FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait
import itertools
import logging
from pathlib import Path
import shutil
import sys
import time
from typing import Iterable

from radioscripts.audio import calculate_required_space
from radioscripts.catalogs import UbuSoundCatalog
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


def wait_progress(
    futures: Iterable[Future],
    *,
    spinner_symbols: tuple[str, ...] = ('⠏', '⠛', '⠹', '⢸', '⣰', '⣤', '⣆', '⡇'),
    pending_progress_symbol: str = '░',
    finished_progress_symbol: str = '█',
):
    """Displays progress bar while waiting for futures to complete."""
    done: set[Future] = set()
    not_done = set(futures)
    total = len(not_done)

    # try to represent the future as a single block if the bar fits terminal width
    # first two characters are reserved for spinner and space + space at the end
    max_chars = min(total, shutil.get_terminal_size().columns - 3)
    spinner = itertools.cycle(spinner_symbols)

    while not_done:
        running = 0
        for future in not_done:
            if future.done():
                if exc := future.exception():
                    sys.stdout.write('\n')  # to not interfere with an error message
                    raise exc
                done.add(future)
            elif future.running():
                running += 1
        not_done -= done

        pending_progress = int(max_chars * running / total)
        finished_progress = int(max_chars * len(done) / total)
        sys.stdout.write(
            '\r'
            + next(spinner)
            + ' '
            + finished_progress_symbol * finished_progress
            + pending_progress_symbol * pending_progress
        )
        sys.stdout.flush()

        time.sleep(0.25)

    # erase progress bar
    sys.stdout.write('\r' + ' ' * (max_chars + 2))
    sys.stdout.write('\rProcess completed\n')


def pretty_size(bytes_: int) -> tuple[float, str]:
    """Returns scaled to gigabytes or megabytes number and the corresponding unit."""
    if bytes_ > 1024**3:
        label = 'Gb'
        value = bytes_ / 1024**3
    else:
        label = 'Mb'
        value = bytes_ / 1024**2
    return value, label


def entrypoint():
    """Compiles Radio Music module compatible stations
    from online catalog of sounds.

    Program main function.
    """
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(threadName)s %(name)s %(message)s',
        )
    else:
        logging.basicConfig(level=logging.CRITICAL, format='%(message)s')
        sys.excepthook = log_uncaught_exception

    target_path = args.path.resolve(strict=True)  # make sure the path exists

    total_size = calculate_required_space(args.banks, args.files, args.minutes)
    print('Space required on SD card is {0:.3f} {1}'.format(*pretty_size(total_size)))

    free_space = shutil.disk_usage(target_path).free
    if free_space < total_size:
        prompt = (
            f'There is not enough free disk space on {target_path.anchor}. '
            'Do you want to continue? (y/N) '
        )
        if input(prompt) != 'y':
            sys.exit(2)

    worker = Worker(
        target=target_path,
        catalog=catalogs[args.catalog](),
        banks=args.banks,
        files=args.files,
        minutes=args.minutes,
    )
    executor = ThreadPoolExecutor(thread_name_prefix='Composer')
    try:
        futures = worker.start(executor)
        if args.debug:
            done, _ = wait(futures, return_when=FIRST_EXCEPTION)
            for future in done:
                future.result()  # resolve done futures to find exception occured
        else:
            wait_progress(futures)
    except Exception as exc:
        executor.shutdown(wait=True, cancel_futures=True)
        raise exc
