#!/usr/bin/env python3

import argparse
import os
import time
from datetime import timezone, datetime
from enum import StrEnum
from io import TextIOWrapper
from pathlib import Path
import json
from typing import Iterator

from tabulate import tabulate
import requests
from urllib.parse import urlencode
import numpy as np
from termcolor import colored
from normal_distribution import NormalDistribution

CACHE_DIR = Path("cache")
CACHE_DIR_17LANDS = CACHE_DIR / "17lands"
CACHE_DIR_17LANDS.mkdir(parents=True, exist_ok=True)

MTGA_STEAM_APP_ID = 2141910

class Grade(StrEnum):
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D_PLUS = "D+"
    D = "D"
    D_MINUS = "D-"
    F = "F"

GRADE_THRESHOLDS = {
    Grade.A_PLUS: 99,
    Grade.A: 95,
    Grade.A_MINUS: 90,
    Grade.B_PLUS: 85,
    Grade.B: 76,
    Grade.B_MINUS: 68,
    Grade.C_PLUS: 57,
    Grade.C: 45,
    Grade.C_MINUS: 36,
    Grade.D_PLUS: 27,
    Grade.D: 17,
    Grade.D_MINUS: 5,
    Grade.F: 0,
}

def grade_to_colored(grade: Grade):
    threshold: int = GRADE_THRESHOLDS[grade]
    green = int(255.0 * ( threshold / 100.0))
    red = 255 - green
    blue = 0
    return red, green, blue

def color_id_to_emoji(color_id: str):
    match color_id:
        case "W":
            return "⚪"
        case "B":
            return "⚫"
        case "U":
            return "🔵"
        case "R":
            return "🔴"
        case "G":
            return "🟢"
        case _:
            return ""

def rarity_to_emoji(rarity: str):
    match rarity:
        case "common":
            return "⬛"
        case "uncommon":
            return "⬜"
        case "rare":
            return "🟨"
        case "mythic":
            return "🟥"
        case _:
            return ""

def grade_color_string(grade: Grade) -> str:
    if not grade:
        return ""
    color = grade_to_colored(grade)
    return colored(str(grade), color=color)

def format_color_id_emoji(colors: list[str]):
    colored_colors = []
    colors.sort()
    for color in colors:
        colored_colors.append(color_id_to_emoji(color))
    return " ".join(colored_colors)

def get_grade_for_score(score: float):
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return Grade.F

def land_string_to_colors(land_type_str: str):
    found_colors = set()
    for chunk in land_type_str.split():
        match chunk:
            case "Plains":
                found_colors.add("W")
            case "Island":
                found_colors.add("U")
            case "Swamp":
                found_colors.add("B")
            case "Mountain":
                found_colors.add("R")
            case "Forest":
                found_colors.add("G")

    if found_colors:
        return "".join(list(found_colors))

    return None

def get_color_pairs() -> set[tuple]:
    all_colors = "WUBRG"
    color_tuples = set()

    for color_a in list(all_colors):
        for color_b in list(all_colors):
            if color_a == color_b:
                continue
            color_tuple = [color_a, color_b]
            color_tuple.sort()
            color_tuples.add(tuple(color_tuple))

    return color_tuples

def split_pool_by_color_pair(set_rankings_by_arena_id: dict, pool: list) -> dict:
    pool_rankings_by_color_pair = {}
    for color_pair in get_color_pairs():
        color_a, color_b = color_pair
        pool_rankings_by_color_pair[color_pair] = []

        for arena_id in pool:
            ranking = set_rankings_by_arena_id[arena_id]
            colors = list(ranking["color"])

            if len(colors) > 1:
                if color_a not in colors:
                    continue
                if color_b not in colors:
                    continue
            elif len(colors) == 1:
                relevant = False
                if color_a in colors:
                    relevant = True
                if color_b in colors:
                    relevant = True
                if not relevant:
                    continue

            pool_rankings_by_color_pair[color_pair].append(ranking)

    return pool_rankings_by_color_pair

def get_top_mean_score(rankings: list, score_key: str, card_count: int) -> float:
    scores = []
    for ranking in rankings:
        if ranking[score_key]:
            scores.append(ranking[score_key])

    sorted_scores = sorted(scores, reverse=True)
    top_scores = sorted_scores[:card_count]
    return float(np.mean(top_scores))

def print_sealed_course_info(set_rankings_by_arena_id: dict, pool: list):
    # all colors
    pool_rankings = []
    for arena_id in pool:
        pool_rankings.append(set_rankings_by_arena_id[arena_id])
    print_rankings(pool_rankings)

    # by color
    pool_rankings_by_color_pair = split_pool_by_color_pair(set_rankings_by_arena_id, pool)
    mean_scores_by_color_pair = {}
    for color_pair, rankings in pool_rankings_by_color_pair.items():
        mean_scores_by_color_pair[color_pair] = get_top_mean_score(rankings,
                                                                   "ever_drawn_score",
                                                                   23)

        print(color_id_to_emoji(color_pair[0]),
              color_id_to_emoji(color_pair[1]),
              len(rankings), "/", 40 - 17,
              mean_scores_by_color_pair[color_pair])

        print_rankings(rankings, insert_space_at_line=23)

    tuples_by_score_sorted = sorted(mean_scores_by_color_pair.items(), key=lambda item: item[-1], reverse=True)

    for color_tuple, score in tuples_by_score_sorted:
        color_a, color_b = color_tuple
        print(color_id_to_emoji(color_a), color_id_to_emoji(color_b), score)

def pull_17lands(expansion: str, format_name: str, start: str, end: str):
    params = {
        "expansion": expansion,
        "format": format_name,
        "start_date": start,
        "end_date": end,
    }
    params_str = urlencode(params)
    cache_file = CACHE_DIR_17LANDS / f"{params_str}.json"

    if not cache_file.is_file():
        res = requests.get("https://www.17lands.com/card_ratings/data", params=params)
        res.raise_for_status()
        with cache_file.open("w") as f:
            f.write(res.text)
        return res.json()
    else:
        print("Using cache")
        with cache_file.open("r") as f:
            return json.loads(f.read())

def get_log_path() -> Path:
    steam_path = Path.home() / ".local/share/Steam"
    if not steam_path.exists():
        raise RuntimeError("Could not find user steam path.")

    mtga_compatibility_data_path = steam_path / f"steamapps/compatdata/{MTGA_STEAM_APP_ID}"
    if not mtga_compatibility_data_path.exists():
        raise RuntimeError("Could not find MTGA compat data path.")

    prefix_c_path = mtga_compatibility_data_path / "pfx/drive_c"
    if not prefix_c_path.exists():
        raise RuntimeError("Could not find proton prefix C path.")

    PREFIX_USER_NAME = "steamuser"
    mtga_app_data_path = prefix_c_path / f"users/{PREFIX_USER_NAME}/AppData/LocalLow/Wizards Of The Coast/MTGA"
    if not mtga_app_data_path.exists():
        raise RuntimeError("Could not find MTGA user data path.")

    player_log_path = mtga_app_data_path / "Player.log"
    if not player_log_path.exists():
        raise RuntimeError("Could not find player log.")

    print(f"Found MTGA log at {player_log_path}")

    return player_log_path

def get_player_log_lines(player_log_path: Path) -> list[str]:
    with player_log_path.open("r") as f:
        all_lines = f.readlines()
    return all_lines

def get_latest_event_courses(log_lines: list[str]) -> list:
    event_courses = {}
    latest_event_courses_id = ""

    for i, line in enumerate(log_lines):
        if "<== EventGetCoursesV2" in line:
            course_id = line.strip().replace("<== EventGetCoursesV2(", "")
            course_id = course_id.replace(")", "")
            course_json = log_lines[i+1]
            event_courses[course_id] = json.loads(course_json)
            courses = event_courses[course_id]["Courses"]
            print(f"Got EventGetCoursesV2 {course_id} with {len(courses)} courses")
            latest_event_courses_id = course_id

    if not event_courses:
        print("Did not find any event courses.")
        return []

    return event_courses[latest_event_courses_id]["Courses"]

def print_courses(courses: list):
    table = []

    for course in courses:
        wins = "N/A"
        if "CurrentWins" in course:
            wins = course["CurrentWins"]

        losses = "N/A"
        if "CurrentLosses" in course:
            losses = course["CurrentLosses"]

        summary = course["CourseDeckSummary"]

        deck_name = "N/A"
        if "Name" in summary:
            deck_name = summary["Name"]

        attribs = {}
        for attrib in summary["Attributes"]:
            k = attrib["name"]
            v = attrib["value"]
            attribs[k] = v

        event_format = "N/A"
        if attribs:
            event_format = attribs["Format"]

        row = (
            deck_name,
            course["InternalEventName"],
            event_format,
            len(course["CardPool"]),
            wins, losses,
        )
        table.append(row)

    print(tabulate(table, headers=(
        "Deck Name",
        "Event",
        "Format",
        "Pool Size",
        "Wins",
        "Losses",
    )))

def get_sealed_courses(courses: list) -> list:
    sealed_courses = []
    for course in courses:
        if course["InternalEventName"].startswith("Sealed") and course["CardPool"]:
            sealed_courses.append(course)
    return sealed_courses

def get_normal_distribution(rankings, key):
    win_rates = []

    for card in rankings:
        if card[key]:
            win_rates.append(card[key])

    winrates_mean = np.mean(win_rates)
    winrates_std = np.std(win_rates, ddof=1)

    return NormalDistribution(float(winrates_mean), float(winrates_std))

def print_rankings_key_histogram(rankings):
    keys = [
        "ever_drawn_win_rate",
        "ever_drawn_game_count",
        "drawn_win_rate",
        "win_rate",
    ]

    histogram = {}
    for k in keys:
        histogram[k] = 0

    for card in rankings:
        for k in keys:
            if k in card and card[k]:
                histogram[k] += 1

    histogram["all"] = len(rankings)

    print(tabulate(histogram.items()))

def get_graded_rankings(set_handle: str, start_date: str):
    end_date: str = datetime.now(timezone.utc).date().isoformat()
    eoe_rankings = pull_17lands(set_handle,
                                "PremierDraft",
                                start_date,
                                end_date)
    rankings_by_arena_id = {}

    for card in eoe_rankings:
        rankings_by_arena_id[card["mtga_id"]] = card

    print_rankings_key_histogram(eoe_rankings)

    normal_distribution = get_normal_distribution(eoe_rankings, "ever_drawn_win_rate")

    for arena_id, rankings in rankings_by_arena_id.items():
        rankings["ever_drawn_score"] = None
        rankings["ever_drawn_grade"] = None

        if not rankings["color"]:
            for card_type in rankings["types"]:
                if "Land" in card_type:
                    found_colors = land_string_to_colors(card_type)
                    if found_colors:
                        rankings["color"] = found_colors

        if rankings["ever_drawn_win_rate"]:
            rankings["ever_drawn_score"] = normal_distribution.cdf(rankings["ever_drawn_win_rate"]) * 100
            rankings["ever_drawn_grade"] = get_grade_for_score(rankings["ever_drawn_score"])

    return rankings_by_arena_id

def print_rankings(rankings: list, insert_space_at_line: int = 0):
    table = []
    for ranking in rankings:
        win_rate = 0
        if ranking["ever_drawn_win_rate"]:
            win_rate = ranking["ever_drawn_win_rate"] * 100

        table.append((
            ranking["name"],
            rarity_to_emoji(ranking["rarity"]),
            format_color_id_emoji(list(ranking["color"])),
            " ".join(ranking["types"]),
            grade_color_string(ranking["ever_drawn_grade"]),
            f"{win_rate:.2f}"
        ))
    table = sorted(table, key=lambda item: item[-1], reverse=True)

    if insert_space_at_line:
        table_spaced = []
        for i, row in enumerate(table):
            table_spaced.append(row)
            if i == insert_space_at_line:
                table_spaced.append(())
        table = table_spaced

    print(tabulate(table))

def follow(file: TextIOWrapper) -> Iterator[str]:

    current_inode: int = os.fstat(file.fileno()).st_ino

    while True:
        line = file.readline()
        if not line:
            # Handle file recreation
            inode = os.stat(file.name).st_ino
            if inode != current_inode:
                print("Log file recreated")
                file.close()
                file = open(file.name, "r")
                current_inode = inode
                continue

            time.sleep(0.1)
            continue
        yield line.strip()

def follow_player_log(player_log_path: Path):
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

                # print_courses(courses)

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

                    rankings_by_arena_id = get_graded_rankings(set_handle, event_start_date.isoformat())
                    # print_rankings(list(rankings_by_arena_id.values()))
                    print_sealed_course_info(rankings_by_arena_id, course["CardPool"])
                course_id = ""

def main():
    parser = argparse.ArgumentParser(prog='follow-log', description='Follow MTGA log.')
    parser.add_argument('-l','--log-path', type=Path, help="Custom Player.log path")
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
        follow_player_log(player_log_path)
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    main()