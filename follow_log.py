#!/usr/bin/env python3

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog='follow-log', description='Follow MTGA log.')

    parser.add_argument('log_path', type=Path)
    args = parser.parse_args()

    print(args.log_path)


if __name__ == "__main__":
    main()