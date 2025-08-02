# python-mtga-helper

CLI application to parse log files from MTGA and analyse them using [17lands](http://17lands.com) data.
The card grading is implemented according to [limited-grades](https://github.com/youssefm/limited-grades).

Currently, only sealed pool analysis is implemented.

## Installation
```commandline
git clone git clone https://github.com/lubosz/python-mtga-helper.git
cd python-mtga-helper
virtualenv .env
. .env/bin/activate
pip install -r requirements.txt
python -m mtga_helper
```

## Usage
```commandline
usage: mtga-helper [-h] [-l LOG_PATH] [--land-count LAND_COUNT] [--print-top-pairs PRINT_TOP_PAIRS] [-v]
                   [-d {PremierDraft,TradDraft,Sealed,TradSealed}]

Follow MTGA log.

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

![screenshot_color_pair_pool.png](doc/screenshot_color_pair_pool.png)
![screenshot_color_pair_ranks.png](doc/screenshot_color_pair_ranks.png)