# python-mtga-helper

CLI application to parse log files from MTGA and analyse them using [17lands](http://17lands.com) data.
The card grading is implemented according to [limited-grades](https://github.com/youssefm/limited-grades).

Currently, only sealed pool analysis and bot draft is implemented.

## Installation

### PyPI
Install the [PyPI package](https://pypi.org/project/mtga-helper/).
```commandline
pip install mtga-helper
```

### Arch Linux User Repository
Install the [AUR package](https://aur.archlinux.org/packages/python-mtga-helper-git).
```commandline
yay -S python-mtga-helper-git
```

### From source
```commandline
git clone https://github.com/lubosz/python-mtga-helper.git
cd python-mtga-helper
virtualenv .env
. .env/bin/activate
pip install .
```

## Usage
```commandline
usage: mtga-helper [-h] [-l LOG_PATH] [--land-count LAND_COUNT]
                   [--print-top-pairs PRINT_TOP_PAIRS] [-v]
                   [-d {PremierDraft,TradDraft,Sealed,TradSealed}]

Analyse MTGA log for sealed pools with 17lands data.

options:
  -h, --help            show this help message and exit
  -l, --log-path LOG_PATH
                        Custom Player.log path (default: None)
  --land-count LAND_COUNT
                        Target Land count (default: 17)
  --print-top-pairs PRINT_TOP_PAIRS
                        Top color pairs to print (default: 3)
  -v, --verbose         Log some intermediate steps (default: False)
  -d, --data-set {PremierDraft,TradDraft,Sealed,TradSealed}
                        Use specific 17lands format data set (default: PremierDraft)
```

Detailed game logs need to be enabled in
`Options -> Account -> Detailed Logs (Plugin Support)`.

## Screenshots

![screenshot color pair pool](https://raw.githubusercontent.com/lubosz/python-mtga-helper/main/doc/screenshot_color_pair_pool.png)
![screenshot color pair ranks](https://raw.githubusercontent.com/lubosz/python-mtga-helper/main/doc/screenshot_color_pair_ranks.png)
![screenshot draft pick](https://raw.githubusercontent.com/lubosz/python-mtga-helper/main/doc/screenshot_draft_pick.png)