# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Iterator

from tabulate import tabulate

logger = logging.getLogger(__name__)

MTGA_STEAM_APP_ID = 2141910

def follow(file: TextIOWrapper) -> Iterator[str]:
    current_inode: int = os.fstat(file.fileno()).st_ino

    while True:
        line = file.readline()
        if not line:
            # Handle file recreation
            inode = os.stat(file.name).st_ino
            if inode != current_inode:
                logger.info("Log file recreated")
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

    logger.info(f"Found MTGA log at {player_log_path}")

    return player_log_path

SUPPORTED_LIMITED_FORMATS = {
    "QuickDraft", "PremierDraft", "Sealed"
}

def get_limited_courses(courses: list) -> list:
    limited_courses = []
    for course in courses:
        if course["CardPool"]:
            for supported_format in SUPPORTED_LIMITED_FORMATS:
                if course["InternalEventName"].startswith(supported_format):
                    limited_courses.append(course)
    return limited_courses

def follow_player_log(player_log_path: Path, args: argparse.Namespace, start_callbacks, end_callbacks):
    with player_log_path.open('r') as player_log_file:
        next_line_event = ""
        for line in follow(player_log_file):
            if next_line_event:
                if next_line_event in end_callbacks:
                    try:
                        payload = json.loads(line)
                    except json.decoder.JSONDecodeError:
                        # In case of LogBusinessEvents the payload is in the start line
                        # and the following line only returns a status string
                        payload = line
                    end_callbacks[next_line_event](payload, args)
                else:
                    logger.debug(f"Unhandled end line event {next_line_event}")
                next_line_event = ""

            elif "Version:" in line and line.count("/") == 2:
                mtga_version = line.split("/")[1].strip()
                logger.info(f"Found game version {mtga_version}")
            elif "DETAILED LOGS" in line:
                detailed_log_status = line.split(":")[1].strip()
                if detailed_log_status == "DISABLED":
                    logger.warning("Detailed logs are disabled!")
                    logger.warning("Enable `Options -> Account -> Detailed Logs (Plugin Support)`")
                else:
                    logger.info(f"Detailed logs are {detailed_log_status}!")

            # Find json lines
            elif line.startswith("<=="):
                match = re.search(r"<== (\w+)\(([a-f0-9-]+)\)", line)
                if match:
                    next_line_event = match.group(1)
                    # next_line_event_id = match.group(2)
            # GreToClientEvent has a different format...
            elif "GreToClientEvent" in line:
                next_line_event = "GreToClientEvent"

            # Find json in start line
            elif line.startswith("[UnityCrossThreadLogger]==>"):
                match = re.search(r"\[UnityCrossThreadLogger\]==> (\w+) (.*)", line)
                if match:
                    current_line_event = match.group(1)
                    outer_json = match.group(2)
                    outer_json_json_data = json.loads(outer_json)
                    inner_json_data = json.loads(outer_json_json_data["request"])
                    if current_line_event in start_callbacks:
                        start_callbacks[current_line_event](inner_json_data, args)
                    else:
                        logger.debug(f"Unhandled start line event {current_line_event}")

def time_str_to_dt(time_str: str) -> datetime:
    time_str = time_str.strip('"')
    parts = time_str.split('.')
    # shorten microseconds to 6 digits
    if len(parts[1]) > 12:
        pre_tz_str = parts[0] + '.' + parts[1][:6]
        tz_str = parts[1][7:]
        time_str = pre_tz_str + tz_str
    return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f%z")

def print_courses(courses: list):
    table = []

    print()
    print("== Courses ==")
    print()

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
        last_updated = "N/A"
        if attribs:
            event_format = attribs["Format"]
            if "LastUpdated" in attribs:
                last_updated_dt = time_str_to_dt(attribs["LastUpdated"])
                last_updated = last_updated_dt.date().isoformat()

        deck_name = deck_name.replace("?=?Loc/Decks/Precon/", "")

        row = (
            deck_name,
            course["InternalEventName"],
            event_format,
            len(course["CardPool"]),
            wins, losses,
            last_updated,
        )
        table.append(row)

    print(tabulate(table, headers=(
        "Deck Name",
        "Event",
        "Format",
        "Pool",
        "Wins",
        "Losses",
        "Updated"
    )))
