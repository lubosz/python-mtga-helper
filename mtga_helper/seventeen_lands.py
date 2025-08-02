# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from tabulate import tabulate
from xdg_base_dirs import xdg_cache_home

from mtga_helper.grading import get_normal_distribution, score_to_grade_string
from mtga_helper.mtg import land_string_to_colors, format_color_id_emoji, rarity_to_emoji

APP_NAME = "python-mtga-helper"
CACHE_DIR = xdg_cache_home() / APP_NAME
CACHE_DIR_17LANDS = CACHE_DIR / "17lands"
CACHE_DIR_17LANDS.mkdir(parents=True, exist_ok=True)

def query_17lands(expansion: str, format_name: str, start: str, end: str):
    params = {
        "expansion": expansion,
        "format": format_name,
        "start_date": start,
        "end_date": end,
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

def get_graded_rankings(set_handle: str, start_date: str, args):
    end_date: str = datetime.now(timezone.utc).date().isoformat()
    eoe_rankings = query_17lands(set_handle,
                                "PremierDraft",
                                 start_date,
                                 end_date)
    rankings_by_arena_id = {}

    for card in eoe_rankings:
        rankings_by_arena_id[card["mtga_id"]] = card

    if args.verbose:
        print_rankings_key_histogram(eoe_rankings)

    normal_distribution = get_normal_distribution(eoe_rankings, "ever_drawn_win_rate")

    for arena_id, rankings in rankings_by_arena_id.items():
        rankings["ever_drawn_score"] = None
        if not rankings["color"] and has_card_type(rankings, "Land"):
            for card_type in rankings["types"]:
                rankings["color"] = land_string_to_colors(card_type)

        if rankings["ever_drawn_win_rate"]:
            rankings["ever_drawn_score"] = normal_distribution.cdf(rankings["ever_drawn_win_rate"]) * 100

    return rankings_by_arena_id

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
            if i == insert_space_at_line:
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