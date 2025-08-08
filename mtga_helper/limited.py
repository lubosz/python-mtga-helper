# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

import argparse
import json
import logging

from tabulate import tabulate
import numpy as np

from mtga_helper.grading import score_to_grade_string
from mtga_helper.mtg import COLOR_PAIRS, LIMITED_DECK_SIZE, are_card_colors_in_pair, format_color_id_emoji
from mtga_helper.seventeen_lands import has_card_type, count_creatures, get_graded_rankings, print_rankings

logger = logging.getLogger(__name__)

def split_pool_by_color_pair(set_rankings_by_arena_id: dict, pool: list, include_lands=False) -> dict:
    pool_rankings_by_color_pair = {}
    for color_pair in COLOR_PAIRS.keys():
        pool_rankings_by_color_pair[color_pair] = []
        for arena_id in pool:
            if arena_id in set_rankings_by_arena_id:
                ranking = set_rankings_by_arena_id[arena_id]
            else:
                logger.debug(f"Could not find card with arena ID {arena_id}! Hopefully it's a basic land?")
                logger.debug(f"Check scryfall: https://api.scryfall.com/cards/arena/{arena_id}")
                continue

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

def print_limited_course_info(course: dict, args: argparse.Namespace):
    pool: list = course["CardPool"]
    event_name = course["InternalEventName"]
    logger.info(f"Found limited event {event_name}")

    event_name_split = event_name.split("_")
    assert len(event_name_split) == 3

    set_handle = event_name_split[1].lower()
    logger.info(f"Found event for set handle `{set_handle}`")

    set_rankings_by_arena_id = get_graded_rankings(set_handle, args.data_set, args)

    if args.verbose:
        print(f"== All Rankings for {set_handle.upper()} ==")
        print_rankings(list(set_rankings_by_arena_id.values()))

    target_non_land_count = LIMITED_DECK_SIZE - args.land_count

    # all colors
    pool_rankings = []
    for arena_id in pool:
        if arena_id in set_rankings_by_arena_id:
            pool_rankings.append(set_rankings_by_arena_id[arena_id])
        else:
            logger.debug(f"Could not find card with arena ID {arena_id}! Hopefully it's a basic land?")
            logger.debug(f"Check scryfall: https://api.scryfall.com/cards/arena/{arena_id}")

    print()
    print(f"== {event_name_split[0]} Pool ==")
    print()
    print_rankings(pool_rankings)

    # by color
    pool_rankings_by_color_pair = split_pool_by_color_pair(set_rankings_by_arena_id, pool)
    scores_by_color_pair = {}
    for color_pair, rankings in pool_rankings_by_color_pair.items():
        scores_by_color_pair[color_pair] = get_top_scores(rankings, "ever_drawn_score", target_non_land_count)

    score_by_color_pair_sorted = sorted(scores_by_color_pair.items(), key=lambda item: item[-1], reverse=True)

    # Only print top 1 color pair for draft pools
    if event_name_split[0] == "Sealed":
        print_top_pairs = args.print_top_pairs
    else:
        print_top_pairs = 1

    print()
    print(f"== Top {print_top_pairs} color pairs ==")

    for i, (color_pair, score_triple) in enumerate(score_by_color_pair_sorted):
        if i < print_top_pairs:
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

    if event_name_split[0] == "Sealed":
        print(f"== Color pair ranking ==")
        print()

        print(tabulate(table, headers=("", "Pair", "Mean", "Score", "Range", "Creatures", "Non Creatures", "Non Lands")))

def premier_draft_pick_cb(draft_status: dict, args):
    event_name = draft_status["EventId"]

    event_name_split = event_name.split("_")
    assert len(event_name_split) == 3
    set_handle = event_name_split[1].lower()

    rankings_by_arena_id = get_graded_rankings(set_handle, args.data_set, args)

    print()
    print(f"== Pack #{draft_status['PackNumber']} Pick #{draft_status['PickNumber']} ==")
    print()

    pack_rankings = []
    for arena_id_str in draft_status["CardsInPack"]:
        arena_id = int(arena_id_str)
        if arena_id in rankings_by_arena_id:
            pack_rankings.append(rankings_by_arena_id[arena_id])
        else:
            logger.debug(f"Could not find card with arena ID {arena_id}! Hopefully it's a basic land?")
            logger.debug(f"Check scryfall: https://api.scryfall.com/cards/arena/{arena_id}")

    if pack_rankings:
        print_rankings(pack_rankings)
    else:
        logger.warning("No known cards in this pack... Is it only a land basic left?")


def bot_draft_pick_cb(event: dict, args):
    target_non_land_count = LIMITED_DECK_SIZE - args.land_count

    draft_status = json.loads(event["Payload"])
    event_name = draft_status["EventName"]

    event_name_split = event_name.split("_")
    assert len(event_name_split) == 3
    set_handle = event_name_split[1].lower()

    rankings_by_arena_id = get_graded_rankings(set_handle, args.data_set, args)

    if args.verbose:
        print(f"== All Rankings for {set_handle.upper()} ==")
        print_rankings(list(rankings_by_arena_id.values()))

    print()
    print(f"== Pack #{draft_status['PackNumber'] + 1} Pick #{draft_status['PickNumber'] + 1} ==")
    print()

    pack_rankings = []
    for arena_id_str in draft_status["DraftPack"]:
        arena_id = int(arena_id_str)
        if arena_id in rankings_by_arena_id:
            pack_rankings.append(rankings_by_arena_id[arena_id])
        else:
            logger.debug(f"Could not find card with arena ID {arena_id}! Hopefully it's a basic land?")
            logger.debug(f"Check scryfall: https://api.scryfall.com/cards/arena/{arena_id}")

    if pack_rankings:
        print_rankings(pack_rankings)
    else:
        logger.warning("No known cards in this pack... Is it only a land basic left?")

    if draft_status["PickedCards"]:
        print()
        print(f"== Pool ==")
        print()

        pool_rankings = []
        for arena_id_str in draft_status["PickedCards"]:
            arena_id = int(arena_id_str)
            if arena_id in rankings_by_arena_id:
                pool_rankings.append(rankings_by_arena_id[arena_id])
            else:
                logger.debug(f"Could not find card with arena ID {arena_id}! Hopefully it's a basic land?")
                logger.debug(f"Check scryfall: https://api.scryfall.com/cards/arena/{arena_id}")

        creature_count, non_creature_count = count_creatures(pool_rankings)
        mean, best, worst = get_top_scores(pool_rankings, "ever_drawn_score", target_non_land_count)

        table = {
            f"Top {target_non_land_count} Mean Grade": score_to_grade_string(mean),
            f"Top {target_non_land_count} Mean Score": f"{mean:.2f}%",
            f"Top {target_non_land_count} Grade Range": f"{score_to_grade_string(best)} - {score_to_grade_string(worst)}",
            "Total Creatures": creature_count,
            "Total Non Creatures": non_creature_count,
            "Total Cards": len(draft_status["PickedCards"]),
        }
        print()
        print(tabulate(table.items()))
        print()

        if pool_rankings:
            print_rankings(pool_rankings, insert_space_at_line=target_non_land_count)
        else:
            logger.warning("Nothing to see here??")