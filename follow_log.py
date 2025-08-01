#!/usr/bin/env python3

import argparse
from pathlib import Path
import json
import pprint
from tabulate import tabulate


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

def main():
    # parser = argparse.ArgumentParser(prog='follow-log', description='Follow MTGA log.')

    # parser.add_argument('log_path', type=Path)
    # args = parser.parse_args()

    # print(args.log_path)

    steam_path = Path.home() / ".local/share/Steam"

    if not steam_path.exists():
        print("Could not find user steam path.")

    mtga_path = steam_path / "steamapps/compatdata/2141910"

    if not mtga_path.exists():
        print("Could not find MTGA compat data path.")

    mtga_user_data_path = mtga_path / "pfx/drive_c/users/steamuser/AppData/LocalLow/Wizards Of The Coast/MTGA"

    if not mtga_user_data_path.exists():
        print("Could not find MTGA user data path.")

    player_log_path = mtga_user_data_path / "Player.log"

    if not mtga_user_data_path.exists():
        print("Could not find player log.")

    print(player_log_path)

    # "InventoryInfo"

    with player_log_path.open("r") as f:
        all_lines = f.readlines()

    event_courses = {}
    latest_event_courses_id = ""

    for i, line in enumerate(all_lines):
        # if "InventoryInfo" in line:
        #     data = json.loads(line)
        #     with Path("InventoryInfo.json").open("w") as f:
        #         f.write(line)

        if "<== EventGetCoursesV2" in line:
            course_id = line.strip().replace("<== EventGetCoursesV2(", "")
            course_id = course_id.replace(")", "")
            course_json = all_lines[i+1]
            event_courses[course_id] = json.loads(course_json)
            courses = event_courses[course_id]["Courses"]
            print(f"Got EventGetCoursesV2 {course_id} with {len(courses)} courses")

            latest_event_courses_id = course_id

        # if "Sealed_EOE_20250729" in line:

        #     # print(line)

        #     data = json.loads(line)

        #     pprint.pprint(data)
        #     return

        #     print("yep")

    # deck_id = "bbb4e823-ca07-43ca-af60-588496474819"

    # with Path("CoursesV2.json").open("w") as f:
    #     f.write(json.dumps(event_courses))

    table = []

    courses = event_courses[latest_event_courses_id]["Courses"]
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

        if event_format == "Sealed":
            print_sealed_course_info(course)

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
    # print(data["DeckSummariesV2"])

    # for summary in data["DeckSummariesV2"]:
    #     if summary["DeckId"] == deck_id:
    #         pprint.pprint(summary)

    # pprint.pprint(data["Decks"][deck_id])

if __name__ == "__main__":
    main()