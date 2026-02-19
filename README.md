# Radio Scripts

Console application to compile [Radio Music](https://musicthing.co.uk/pages/radio.html) eurorack module compatible "stations" from online sound catalogs.

Currently supported catalogs are

  * [UbuWeb Sound](https://www.ubu.com/sound/index.html)

## Installation

1. Install [Python 3](https://www.python.org/downloads/)
2. Install [SoX](http://sox.sourceforge.net/)
3. Download [latest release](https://github.com/ivofrolov/radio-scripts/releases/latest/download/radioscripts)

## Usage

Command `python3 radioscripts <path to output directory>` will write a bank of 12 stations at least 30 minutes long each to the output directory.

See `python3 radioscripts --help` for options.
