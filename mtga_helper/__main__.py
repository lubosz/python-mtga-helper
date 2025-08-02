# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
import json
from datetime import datetime
from pathlib import Path

from tabulate import tabulate
import numpy as np

from mtga_helper.grading import score_to_grade_string
from mtga_helper.mtg import COLOR_PAIRS, LIMITED_DECK_SIZE, are_card_colors_in_pair, format_color_id_emoji
from mtga_helper.mtga_log import get_log_path, follow, print_courses, get_sealed_courses
from mtga_helper.seventeen_lands import has_card_type, count_creatures, get_graded_rankings, print_rankings


def split_pool_by_color_pair(set_rankings_by_arena_id: dict, pool: list, include_lands=False) -> dict:
    pool_rankings_by_color_pair = {}
    for color_pair in COLOR_PAIRS.keys():
        pool_rankings_by_color_pair[color_pair] = []
        for arena_id in pool:
            ranking = set_rankings_by_arena_id[arena_id]

            if not include_lands and has_card_type(ranking, "Land"):
                continue

            if are_card_colors_in_pair(ranking["color"], color_pair):
                pool_rankings_by_color_pair[color_pair].append(ranking)

    return pool_rankings_by_color_pair

def get_top_scores(rankings: list, score_key: str, card_count: int) -> tuple[float, float, float]:
    scores = []
    for ranking in rankings:
        if ranking[score_key]:
            scores.append(ranking[score_key])

    sorted_scores = sorted(scores, reverse=True)
    top_scores = sorted_scores[:card_count]
    worst_of_top = top_scores[-1]
    best_of_top = top_scores[0]
    return float(np.mean(top_scores)), best_of_top, worst_of_top

def color_pair_stats_row(i: int, color_pair: str, score_triple: tuple, rankings: list) -> tuple:
    creature_count, non_creature_count = count_creatures(rankings)
    mean, best, worst = score_triple

    return (
        i + 1,
        f"{format_color_id_emoji(color_pair)} {COLOR_PAIRS[color_pair]}",
        score_to_grade_string(mean),
        mean,
        f"{score_to_grade_string(best)} - {score_to_grade_string(worst)}",
        creature_count,
        non_creature_count,
        len(rankings),
    )

def print_sealed_course_info(set_rankings_by_arena_id: dict, pool: list, args: argparse.Namespace):
    target_non_land_count = LIMITED_DECK_SIZE - args.land_count

    # all colors
    pool_rankings = []
    for arena_id in pool:
        pool_rankings.append(set_rankings_by_arena_id[arena_id])
    print_rankings(pool_rankings)

    # by color
    pool_rankings_by_color_pair = split_pool_by_color_pair(set_rankings_by_arena_id, pool)
    scores_by_color_pair = {}
    for color_pair, rankings in pool_rankings_by_color_pair.items():
        scores_by_color_pair[color_pair] = get_top_scores(rankings, "ever_drawn_score", target_non_land_count)

    score_by_color_pair_sorted = sorted(scores_by_color_pair.items(), key=lambda item: item[-1], reverse=True)

    for i, (color_pair, score_triple) in enumerate(score_by_color_pair_sorted):
        if i < args.print_top_pairs:
            rankings = pool_rankings_by_color_pair[color_pair]

            rank, pair_str, mean_grade, mean_score, grade_range, num_creatures, num_non_creatures, num_non_lands = \
                color_pair_stats_row(i, color_pair, score_triple, rankings)

            table = {
                "Rank": rank,
                f"Top {target_non_land_count} Mean Grade": mean_grade,
                f"Top {target_non_land_count} Mean Score": f"{mean_score:.2f}%",
                f"Top {target_non_land_count} Grade Range": grade_range,
                "Total Creatures": num_creatures,
                "Total Non Creatures": num_non_creatures,
                "Total Non Lands": num_non_lands,
            }
            print()
            print(tabulate(table.items(), headers=(pair_str, "")))
            print()
            print_rankings(rankings, insert_space_at_line=target_non_land_count)
            print()

    table = []
    for i, (color_pair, score_triple) in enumerate(score_by_color_pair_sorted):
        rankings = pool_rankings_by_color_pair[color_pair]
        table.append(color_pair_stats_row(i, color_pair, score_triple, rankings))
    print(tabulate(table, headers=("", "Pair", "Mean", "Score", "Range", "Creatures", "Non Creatures", "Non Lands")))

def follow_player_log(player_log_path: Path, args: argparse.Namespace):
    with player_log_path.open('r') as player_log_file:
        course_id = ""
        for line in follow(player_log_file):
            if "Version:" in line and line.count("/") == 2:
                mtga_version = line.split("/")[1].strip()
                print(f"Found game version {mtga_version}")
            elif "DETAILED LOGS" in line:
                detailed_log_status = line.split(":")[1].strip()
                if detailed_log_status == "DISABLED":
                    print("Detailed logs are disabled!")
                    print("Enable `Options -> Account -> Detailed Logs (Plugin Support)`")
                else:
                    print(f"Detailed logs are {detailed_log_status}!")
            elif "<== EventGetCoursesV2" in line:
                course_id = line.strip().replace("<== EventGetCoursesV2(", "")
                course_id = course_id.replace(")", "")
                print(f"Found EventGetCoursesV2 query with id {course_id}")
            elif course_id:
                event_courses = json.loads(line)
                courses = event_courses["Courses"]
                print(f"Got EventGetCoursesV2 {course_id} with {len(courses)} courses")

                if args.verbose:
                    print_courses(courses)

                sealed_courses = get_sealed_courses(courses)
                print(f"Found {len(sealed_courses)} ongoing sealed games.")
                for course in sealed_courses:

                    event_name = course["InternalEventName"]
                    print(f"Found sealed event {event_name}")

                    event_name_split = event_name.split("_")
                    assert len(event_name_split) == 3

                    set_handle = event_name_split[1].lower()
                    event_start_date_str = event_name_split[2]
                    event_start_date = datetime.strptime(event_start_date_str, "%Y%m%d").date()
                    print(f"Found event for set handle `{set_handle}` started {event_start_date}")

                    rankings_by_arena_id = get_graded_rankings(set_handle, event_start_date.isoformat(), args)

                    if args.verbose:
                        print(f"== All Rankings for {set_handle.upper()} ==")
                        print_rankings(list(rankings_by_arena_id.values()))
                    print_sealed_course_info(rankings_by_arena_id, course["CardPool"], args)
                course_id = ""

def main():
    parser = argparse.ArgumentParser(prog='follow-log', description='Follow MTGA log.')
    parser.add_argument('-l','--log-path', type=Path, help="Custom Player.log path (Default: auto)")
    parser.add_argument('--land-count', type=int, help="Target Land count (Default: 17)", default=17)
    parser.add_argument('--print-top-pairs', type=int, help="Top color pairs to print (Default: 3)", default=3)
    parser.add_argument('-v', '--verbose', help="Log some intermediate steps", action="store_true")
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
        follow_player_log(player_log_path, args)
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()