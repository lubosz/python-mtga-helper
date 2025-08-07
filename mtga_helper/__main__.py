# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
from pathlib import Path

from mtga_helper.limited import print_sealed_course_info, bot_draft_cb
from mtga_helper.mtga_log import get_log_path, get_sealed_courses, follow_player_log

def got_courses_cb(event: dict, args: argparse.Namespace):
    courses = event["Courses"]
    sealed_courses = get_sealed_courses(courses)
    print(f"Found {len(sealed_courses)} ongoing sealed games.")
    for course in sealed_courses:
        print_sealed_course_info(course, args)

def main():
    parser = argparse.ArgumentParser(prog='mtga-helper',
                                     description='Analyse MTGA log for sealed pools with 17lands data.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-l','--log-path', type=Path, help="Custom Player.log path")
    parser.add_argument('--land-count', type=int, help="Target Land count", default=17)
    parser.add_argument('--print-top-pairs', type=int, help="Top color pairs to print", default=3)
    parser.add_argument('-v', '--verbose', help="Log some intermediate steps", action="store_true")
    parser.add_argument('-d', '--data-set', choices=['PremierDraft', 'TradDraft', 'Sealed', 'TradSealed'],
                        help="Use specific 17lands format data set", default="PremierDraft")
    args = parser.parse_args()

    if args.log_path:
        player_log_path = args.log_path
        if not player_log_path.exists():
            print(f"Can't find log file at {player_log_path}")
            return
    else:
        try:
            player_log_path = get_log_path()
        except RuntimeError:
            print("Could not find MTGA log file")
            return

    try:
        log_callbacks = {
            "EventGetCoursesV2": got_courses_cb,
            "BotDraftDraftStatus": bot_draft_cb,
            "BotDraftDraftPick": bot_draft_cb,
        }
        follow_player_log(player_log_path, args, log_callbacks)
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()