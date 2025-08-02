#!/usr/bin/env python3

import argparse
from enum import StrEnum
from pathlib import Path
import json
import pprint
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


MIN_GAMES_DRAWN_FOR_INFERENCE = 100
MIN_GAMES_DRAWN = 500

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

def color_id_to_colored(color_id: str):
    match color_id:
        case "W":
            return "light_yellow"
        case "U":
            return "light_blue"
        case "B":
            return "light_grey"
        case "R":
            return "light_red"
        case "G":
            return "light_green"
        case _:
            return "white"


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


def format_color_id_string(colors: list[str]) -> str:
    colored_colors = []
    colors.sort()
    for color in colors:
        colored_colors.append(colored(color, color_id_to_colored(color)))
    return " ".join(colored_colors)

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

def print_sealed_course_info(rankings_by_arena_id, course: dict):
    pool = course["CardPool"]

    assert len(pool) > 0

    pool_id_by_count = {}
    for pool_id in pool:
        if pool_id not in pool_id_by_count:
            pool_id_by_count[pool_id] = 1
        else:
            pool_id_by_count[pool_id] += 1

    # pprint.pprint(pool_id_by_count)

    table = []
    for arena_id, count in pool_id_by_count.items():
        rankings = rankings_by_arena_id[arena_id]

        win_rate = 0
        if rankings["ever_drawn_win_rate"]:
            win_rate = rankings["ever_drawn_win_rate"] * 100

        table.append((
            # arena_id,
            rankings["name"],
            rarity_to_emoji(rankings["rarity"]),
            format_color_id_emoji(list(rankings["color"])),
            " ".join(rankings["types"]),
            # rankings["grade"],
            # rankings["score"],
            # rankings["win_rate"],
            grade_color_string(rankings["ever_drawn_grade"]),
            # rankings["ever_drawn_score"],
            f"{win_rate:.2f}"
        ))

        # pprint.pprint(rankings)

    table_sorted = sorted(table, key=lambda item: item[-1], reverse=True)
    print(tabulate(table_sorted))

    # by color
    ALL_COLORS = "WUBRG"
    color_tuples = set()

    for color_a in list(ALL_COLORS):
        for color_b in list(ALL_COLORS):
            if color_a == color_b:
                continue
            color_tuple = [color_a, color_b]
            color_tuple.sort()
            color_tuples.add(tuple(color_tuple))

    print(f"We have {len(color_tuples)} tuples")

    tuples_by_score = {}

    for color_a, color_b in color_tuples:
        color_tuple_scores = []

        table = []
        for arena_id, count in pool_id_by_count.items():
            rankings = rankings_by_arena_id[arena_id]

            colors = list(rankings["color"])

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

            win_rate = 0
            if rankings["ever_drawn_win_rate"]:
                win_rate = rankings["ever_drawn_win_rate"] * 100

            if rankings["ever_drawn_score"]:
                color_tuple_scores.append(rankings["ever_drawn_score"])

            table.append((
                # arena_id,
                rankings["name"],
                rarity_to_emoji(rankings["rarity"]),
                format_color_id_emoji(list(rankings["color"])),
                " ".join(rankings["types"]),
                # rankings["grade"],
                # rankings["score"],
                # rankings["win_rate"],
                grade_color_string(rankings["ever_drawn_grade"]),
                # rankings["ever_drawn_score"],
                f"{win_rate:.2f}"
            ))

        sorted_color_tuple_scores = sorted(color_tuple_scores, reverse=True)
        best_23_scores = sorted_color_tuple_scores[:23]
        top23_mean_color_tuple_scores = np.mean(best_23_scores)
        pool_mean_color_tuple_scores = np.mean(color_tuple_scores)
        print(color_id_to_emoji(color_a), color_id_to_emoji(color_b), len(table), "/", 40 - 17, top23_mean_color_tuple_scores, pool_mean_color_tuple_scores)
        table_sorted = sorted(table, key=lambda item: item[-1], reverse=True)
        # print(tabulate(table_sorted))

        tuples_by_score[(color_a, color_b)] = float(top23_mean_color_tuple_scores)

        table_spaced = []
        for i, row in enumerate(table_sorted):
            table_spaced.append(row)
            if i == 23:
                table_spaced.append(())
        print(tabulate(table_spaced))

        # pprint.pprint(tuples_by_score)

    tuples_by_score_sorted = sorted(tuples_by_score.items(), key=lambda item: item[-1], reverse=True)

    # pprint.pprint(tuples_by_score_sorted)

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


def get_player_log_lines() -> list[str]:
    player_log_path = get_log_path()
    with player_log_path.open("r") as f:
        all_lines = f.readlines()
    return all_lines

def get_latest_event_courses(log_lines: list[str]) -> list:
    event_courses = {}
    latest_event_courses_id = ""

    for i, line in enumerate(log_lines):
        # if "InventoryInfo" in line:
        #     data = json.loads(line)
        #     with Path("InventoryInfo.json").open("w") as f:
        #         f.write(line)

        if "<== EventGetCoursesV2" in line:
            course_id = line.strip().replace("<== EventGetCoursesV2(", "")
            course_id = course_id.replace(")", "")
            course_json = log_lines[i+1]
            event_courses[course_id] = json.loads(course_json)
            courses = event_courses[course_id]["Courses"]
            print(f"Got EventGetCoursesV2 {course_id} with {len(courses)} courses")

            latest_event_courses_id = course_id

    # with Path("CoursesV2.json").open("w") as f:
    #     f.write(json.dumps(event_courses))

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

        # pprint.pprint(attribs)

        event_format = "N/A"
        if attribs:
            event_format = attribs["Format"]

        row = (
            # course["CourseId"],
            deck_name,
            course["InternalEventName"],
            event_format,
            len(course["CardPool"]),
            wins, losses,
        )
        table.append(row)

    print(tabulate(table, headers=(
        # "ID",
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
        for attrib in course["CourseDeckSummary"]["Attributes"]:
            if attrib["name"] == "Format" and attrib["value"] == "Sealed":
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
    histogram = {
        "all": 0,
        "ever_drawn_win_rate": 0,
        "ever_drawn_game_count": 0,
        "drawn_win_rate": 0,
        "win_rate": 0,
    }
    for card in rankings:
        if card["ever_drawn_win_rate"]:
            histogram["ever_drawn_win_rate"] += 1
        if card["ever_drawn_game_count"]:
            histogram["ever_drawn_game_count"] += 1
        if card["drawn_win_rate"]:
            histogram["drawn_win_rate"] += 1
        if card["win_rate"]:
            histogram["win_rate"] += 1
        histogram["all"] += 1
    pprint.pprint(histogram)

def get_graded_rankings():
    eoe_rankings = pull_17lands("eoe",
                                "PremierDraft",
                                "2025-07-29",
                                "2025-08-01")
    rankings_by_arena_id = {}

    for card in eoe_rankings:
        rankings_by_arena_id[card["mtga_id"]] = card

    print_rankings_key_histogram(eoe_rankings)

    win_rate_normal_distribution = get_normal_distribution(eoe_rankings, "win_rate")
    ever_drawn_win_rate_normal_distribution = get_normal_distribution(eoe_rankings, "ever_drawn_win_rate")

    for arena_id, rankings in rankings_by_arena_id.items():
        rankings["score"] = None
        rankings["grade"] = None
        rankings["ever_drawn_score"] = None
        rankings["ever_drawn_grade"] = None

        if not rankings["color"]:
            for card_type in rankings["types"]:
                if "Land" in card_type:
                    found_colors = land_string_to_colors(card_type)
                    if found_colors:
                        rankings["color"] = found_colors

        if rankings["win_rate"]:
            rankings["score"] = win_rate_normal_distribution.cdf(rankings["win_rate"]) * 100
            rankings["grade"] = get_grade_for_score(rankings["score"])
        if rankings["ever_drawn_win_rate"]:
            rankings["ever_drawn_score"] = ever_drawn_win_rate_normal_distribution.cdf(rankings["ever_drawn_win_rate"]) * 100
            rankings["ever_drawn_grade"] = get_grade_for_score(rankings["ever_drawn_score"])

    return rankings_by_arena_id

def main():
    # parser = argparse.ArgumentParser(prog='follow-log', description='Follow MTGA log.')
    # parser.add_argument('log_path', type=Path)
    # args = parser.parse_args()
    # print(args.log_path)

    rankings_by_arena_id = get_graded_rankings()

    # table = []
    # for arena_id, rankings in rankings_by_arena_id.items():
    #     table.append((arena_id,
    #                   rankings["name"],
    #                   rankings["rarity"],
    #                   rankings["grade"],
    #                   rankings["score"],
    #                   rankings["win_rate"],
    #                   rankings["ever_drawn_grade"],
    #                   rankings["ever_drawn_score"],
    #                   rankings["ever_drawn_win_rate"]))
    # print(tabulate(table))
    # load_limited_grades()

    try:
        player_log = get_player_log_lines()
    except RuntimeError:
        print("Could not find MTGA log file")
        return

    courses = get_latest_event_courses(player_log)
    # print_courses(courses)
    sealed_courses = get_sealed_courses(courses)

    for course in sealed_courses:
        print_sealed_course_info(rankings_by_arena_id, course)


if __name__ == "__main__":
    main()