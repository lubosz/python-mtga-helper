# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from tabulate import tabulate
from xdg_base_dirs import xdg_cache_home

from mtga_helper.grading import score_to_grade_string, calculate_grade_scores
from mtga_helper.mtg import format_color_id_emoji, rarity_to_emoji, land_string_to_colors

APP_NAME = "python-mtga-helper"
CACHE_DIR = xdg_cache_home() / APP_NAME
CACHE_DIR_17LANDS = CACHE_DIR / "17lands"
CACHE_DIR_17LANDS.mkdir(parents=True, exist_ok=True)

def query_17lands(expansion: str, format_name: str):
    params = {
        "expansion": expansion,
        "format": format_name,
        "end_date": datetime.now(timezone.utc).date().isoformat(),
    }
    params_str = urlencode(params)
    cache_file = CACHE_DIR_17LANDS / f"{params_str}.json"

    if not cache_file.is_file():
        print("Fetching 17lands data for", params_str)
        res = requests.get("https://www.17lands.com/card_ratings/data", params=params)
        res.raise_for_status()
        with cache_file.open("w") as f:
            f.write(res.text)
        return res.json()
    else:
        print("Found 17land cache file at", cache_file)
        with cache_file.open("r") as f:
            return json.loads(f.read())

def get_graded_rankings(set_handle: str, format_name: str, args):
    set_rankings = query_17lands(set_handle, format_name)
    rankings_by_arena_id = {}
    for ranking in set_rankings:

        # Annotate colors on some lands
        if not ranking["color"] and has_card_type(ranking, "Land"):
            for card_type in ranking["types"]:
                ranking["color"] = land_string_to_colors(card_type)

        rankings_by_arena_id[ranking["mtga_id"]] = ranking

    if args.verbose:
        print_rankings_key_histogram(set_rankings)

    return calculate_grade_scores(rankings_by_arena_id, set_rankings)

def has_card_type(ranking: dict, type_name: str) -> bool:
    for card_type in ranking["types"]:
        if type_name in card_type:
            return True
    return False

def count_creatures(rankings: list) -> tuple[int, int]:
    creature_count = 0
    non_creature_count = 0

    for ranking in rankings:
        if has_card_type(ranking, "Creature"):
            creature_count += 1
        else:
            non_creature_count += 1

    return creature_count, non_creature_count

def print_rankings(rankings: list, insert_space_at_line: int = 0):
    table = []
    for ranking in rankings:
        win_rate = 0
        if ranking["ever_drawn_win_rate"]:
            win_rate = ranking["ever_drawn_win_rate"] * 100

        table.append((
            format_color_id_emoji(ranking["color"]),
            rarity_to_emoji(ranking["rarity"]),
            ranking["name"],
            score_to_grade_string(ranking["ever_drawn_score"]),
            f"{win_rate:.2f}",
            " ".join(ranking["types"]),
        ))
    table = sorted(table, key=lambda item: item[-2], reverse=True)

    if insert_space_at_line:
        table_spaced = []
        for i, row in enumerate(table):
            table_spaced.append(row)
            if i == insert_space_at_line - 1:
                table_spaced.append(())
        table = table_spaced

    print(tabulate(table, headers=("", "", "Card", "", "Win %", "Type"), colalign=("right",)))

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