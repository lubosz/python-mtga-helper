# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
import json
import os
import time
import pprint
from io import TextIOWrapper
from pathlib import Path
from typing import Iterator

from tabulate import tabulate

MTGA_STEAM_APP_ID = 2141910

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

def get_sealed_courses(courses: list) -> list:
    sealed_courses = []
    for course in courses:
        if course["InternalEventName"].startswith("Sealed") and course["CardPool"]:
            sealed_courses.append(course)
    return sealed_courses

def follow_player_log(player_log_path: Path, args: argparse.Namespace, courses_cb, bot_draft_cb):
    with player_log_path.open('r') as player_log_file:
        next_line_event = ""
        for line in follow(player_log_file):
            if next_line_event:
                line_json = json.loads(line)
                match next_line_event:
                    case "EventGetCoursesV2":
                        courses = line_json["Courses"]
                        print(f"Got EventGetCoursesV2 {course_id} with {len(courses)} courses")
                        if args.verbose:
                            print_courses(courses)
                        courses_cb(courses, args)
                    case "BotDraftDraftStatus" | "BotDraftDraftPick":
                        bot_draft_status_payload = json.loads(line_json["Payload"])
                        if args.verbose:
                            pprint.pprint(bot_draft_status_payload)
                        bot_draft_cb(bot_draft_status_payload, args)
                    case _:
                        pass
                next_line_event = ""

            elif "Version:" in line and line.count("/") == 2:
                mtga_version = line.split("/")[1].strip()
                print(f"Found game version {mtga_version}")
            elif "DETAILED LOGS" in line:
                detailed_log_status = line.split(":")[1].strip()
                if detailed_log_status == "DISABLED":
                    print("Detailed logs are disabled!")
                    print("Enable `Options -> Account -> Detailed Logs (Plugin Support)`")
                else:
                    print(f"Detailed logs are {detailed_log_status}!")

            # Find json lines
            elif "<== EventGetCoursesV2" in line:
                course_id = line.strip().replace("<== EventGetCoursesV2(", "")
                course_id = course_id.replace(")", "")
                print(f"Found EventGetCoursesV2 query with id {course_id}")
                next_line_event = "EventGetCoursesV2"
            elif "<== BotDraftDraftStatus" in line:
                bot_draft_status_id = line.strip().replace("<== BotDraftDraftStatus(", "")
                bot_draft_status_id = bot_draft_status_id.replace(")", "")
                print(f"Found BotDraftDraftStatus query with id {bot_draft_status_id}")
                next_line_event = "BotDraftDraftStatus"
            elif "<== BotDraftDraftPick" in line:
                bot_draft_pick_id = line.strip().replace("<== BotDraftDraftPick(", "")
                bot_draft_pick_id = bot_draft_pick_id.replace(")", "")
                print(f"Found BotDraftDraftPick query with id {bot_draft_pick_id}")
                next_line_event = "BotDraftDraftPick"

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
