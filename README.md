# Radio Scripts

Console application to compile [Radio Music](https://musicthing.co.uk/pages/radio.html) module compatible stations from [UbuWeb Sound](https://www.ubu.com/sound/index.html) catalog.

## Installation

1. Install [Python 3](https://www.python.org/downloads/)
2. Install [SoX](http://sox.sourceforge.net/)
3. Run `pip3 install git+https://github.com/ivofrolov/radio-scripts.git`

## Usage

Command `radioscripts <path to SD card>` will write 16 banks of 12 stations 30 minutes length each to the SD card. Samples are randomly selected, but each station contains sounds from N=5 catalog sections.

# To Do

- [x] debug output
- [ ] progress output
- [ ] free disk space check
- [ ] package *RELEASE 1.0*
- [ ] compression to make sounds equally loud
- [ ] some kind of sounds categorization (speech, music, etc.) and similarity degree to make it sound more like radio
