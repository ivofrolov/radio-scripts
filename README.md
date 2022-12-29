# Radio Scripts

Console application to compile [Radio Music](https://musicthing.co.uk/pages/radio.html)
eurorack module compatible "stations" from online sound catalogs.

Currently supported catalogs are

  * [UbuWeb Sound](https://www.ubu.com/sound/index.html)
  * [Irdial](http://irdial.hyperreal.org/)

## Installation

1. Install [Python 3](https://www.python.org/downloads/)
2. Install [SoX](http://sox.sourceforge.net/)
3. Download [latest release](https://github.com/ivofrolov/radio-scripts/releases/latest/download/radioscripts.pyz)

## Usage

Command `python3 radioscripts.pyz <path to SD card>` will write 16
banks of 12 stations 30 minutes long each to the SD card. Samples are
randomly selected, but each station contains sounds from 5 catalog
sections.

See `python3 radioscripts.pyz` for options.

# To Do

- [ ] some kind of sounds categorization (speech, music, etc.) by
      similarity degree in order to make stations sound more like
      radio
