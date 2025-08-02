# python-mtga-helper
# Copyright 2025 Lubosz Sarnecki <lubosz@gmail.com>
# SPDX-License-Identifier: MIT

from enum import StrEnum
import colorsys

from termcolor import colored
import numpy as np

from mtga_helper.normal_distribution import NormalDistribution

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

def grade_to_color(grade: Grade) -> tuple[int, int, int]:
    threshold: int = GRADE_THRESHOLDS[grade]
    hue = threshold / (3 * 100.0)
    rgb_float = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    rgb_int = [int(c * 255) for c in rgb_float]
    return tuple[int, int, int](rgb_int)

def score_to_grade(score: float):
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return Grade.F

def score_to_grade_string(score: float) -> str:
    if not score:
        return ""
    grade = score_to_grade(score)
    color = grade_to_color(grade)
    return colored(str(grade), color=color)

def get_normal_distribution(rankings, key):
    win_rates = []

    for card in rankings:
        if card[key]:
            win_rates.append(card[key])

    winrates_mean = np.mean(win_rates)
    winrates_std = np.std(win_rates, ddof=1)

    return NormalDistribution(float(winrates_mean), float(winrates_std))
