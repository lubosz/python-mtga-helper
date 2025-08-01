#!/usr/bin/env python3

import argparse
from pathlib import Path
import json
import pprint
from tabulate import tabulate
import requests
from IPython import embed
from urllib.parse import urlencode

CACHE_DIR = Path("cache")
CACHE_DIR_17LANDS = CACHE_DIR / "17lands"
CACHE_DIR_17LANDS.mkdir(parents=True, exist_ok=True)

def print_sealed_course_info(course: dict):
    pool = course["CardPool"]

    assert len(pool) > 0

    pool_id_by_count = {}
    for pool_id in pool:
        if pool_id not in pool_id_by_count:
            pool_id_by_count[pool_id] = 1
        else:
            pool_id_by_count[pool_id] += 1

    pprint.pprint(pool_id_by_count)


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

    mtga_path = steam_path / "steamapps/compatdata/2141910"

    if not mtga_path.exists():
        raise RuntimeError("Could not find MTGA compat data path.")

    mtga_user_data_path = mtga_path / "pfx/drive_c/users/steamuser/AppData/LocalLow/Wizards Of The Coast/MTGA"

    if not mtga_user_data_path.exists():
        raise RuntimeError("Could not find MTGA user data path.")

    player_log_path = mtga_user_data_path / "Player.log"

    if not player_log_path.exists():
        raise RuntimeError("Could not find player log.")

    return player_log_path


def get_player_log_lines() -> list[str]:
    player_log_path = get_log_path()
    with player_log_path.open("r") as f:
        all_lines = f.readlines()
    return all_lines

def get_latest_event_courses(log_lines: list[str]):
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

def main():
    # parser = argparse.ArgumentParser(prog='follow-log', description='Follow MTGA log.')
    # parser.add_argument('log_path', type=Path)
    # args = parser.parse_args()
    # print(args.log_path)

    # player_log = get_player_log_lines()
    # courses = get_latest_event_courses(player_log)
    # # print_courses(courses)
    #
    # sealed_courses = get_sealed_courses(courses)
    #
    # print_sealed_course_info(sealed_courses[0])

    eoe_rankings = pull_17lands("eoe", "PremierDraft", "2025-07-29", "2025-08-01")
    rankings_by_arena_id = {}
    for card in eoe_rankings:
        rankings_by_arena_id[card["mtga_id"]] = card
    pprint.pprint(rankings_by_arena_id)

if __name__ == "__main__":
    main()