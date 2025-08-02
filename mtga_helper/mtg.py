# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

LIMITED_DECK_SIZE = 40

COLOR_PAIRS = {
    # Allied
    "WU": "Azorius",
    "UB": "Dimir",
    "BR": "Rakdos",
    "RG": "Gruul",
    "GW": "Selesnya",
    # Enemy
    "WB": "Orzhov",
    "UR": "Izzet",
    "BG": "Golgari",
    "RW": "Boros",
    "GU": "Simic"
}

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

def format_color_id_emoji(colors: str):
    return "".join(color_id_to_emoji(c) for c in colors)

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

    return "".join(list(found_colors))

def are_card_colors_in_pair(card_colors: str, color_pair: str) -> bool:
    for card_color in card_colors:
        if card_color not in color_pair:
            return False
    return True
