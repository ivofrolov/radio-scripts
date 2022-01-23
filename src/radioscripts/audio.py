from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Iterable, Union


RADIOMUSIC_SAMPLE_RATE: int = 44100
RADIOMUSIC_BIT_DEPTH: int = 16
RADIOMUSIC_CHANNELS: int = 1


class SoxNotFoundError(Exception):
    def __str__(self) -> str:
        return 'sox application not found'


class SoxError(Exception):
    def __init__(self, returncode: int, message: str):
        self.returncode = returncode
        self.message = message

    def __str__(self) -> str:
        return f'{self.message} (exit code {self.returncode})'


def run_sox(*args: Union[str, Path]) -> str:
    """Executes sox application with provided arguments."""
    sox_path = shutil.which('sox')
    if sox_path is None:
        raise SoxNotFoundError()

    cmd = [sox_path, *args]
    try:
        completed_process = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        return completed_process.stdout
    except subprocess.CalledProcessError as exc:
        raise SoxError(exc.returncode, exc.stderr) from exc


def measure_durations(*paths: Path) -> list[float]:
    """Returns durations of sound files in seconds."""
    sox_output = run_sox('--info', '-D', *paths)
    return [float(line) for line in sox_output.strip().splitlines()]


def convert(
    input_path: Path, output_path: Path, channels: int, sample_rate: int, bit_depth: int
):
    """Converts sound file sample rate, bit depth and channels number to provided values.
    And also removes silence from the beggining and end of the audio.
    """
    # fmt: off
    run_sox(
        input_path,
        '-G',
        '-b', f'{bit_depth}',
        output_path,
        'channels', f'{channels}',
        'rate', '-s', '-a', f'{sample_rate}',
        'reverse',
        'silence', '1', '5', '0',
        'reverse',
        'silence', '1', '5', '0',
    )
    # fmt: on


def join(input_paths: list[Path], output_path: Path, crossfade_duration: float):
    """Splices sounds together."""
    if not input_paths:
        return

    excess = crossfade_duration / 2
    splices = measure_durations(*input_paths)[:-1]
    for index in range(1, len(splices)):
        splices[index] = splices[index - 1] + splices[index] - excess * index
    # fmt: off
    run_sox(
        *input_paths,
        output_path,
        'splice', '-q', *[f'{position},{excess}' for position in splices],
        'norm',
        'dither', '-s',
    )
    # fmt: on


def make_radio_program(
    input_paths: Iterable[Path],
    output_path: Path,
    *,
    crossfade_duration: int = 2,
    channels: int = RADIOMUSIC_CHANNELS,
    sample_rate: int = RADIOMUSIC_SAMPLE_RATE,
    bit_depth: int = RADIOMUSIC_BIT_DEPTH,
):
    """Concatenates sounds together into a wav file, creating a kind of radio station."""
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_paths: list[Path] = []
        for index, input_path in enumerate(input_paths, start=1):
            staging_path = (
                Path(tmpdir).joinpath(f'{index}_{input_path.name}').with_suffix('.wav')
            )
            convert(input_path, staging_path, channels, sample_rate, bit_depth)
            staging_paths.append(staging_path)
        join(staging_paths, output_path, crossfade_duration)


def calculate_required_space(
    banks: int,
    files: int,
    minutes: int,
    *,
    sample_rate: int = RADIOMUSIC_SAMPLE_RATE,
    bit_depth: int = RADIOMUSIC_BIT_DEPTH,
) -> float:
    """Returns the size in bytes of N banks of M wav files K minutes each."""
    return banks * files * minutes * 60 * sample_rate * bit_depth / 8
