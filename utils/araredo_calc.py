# keirin_ai/utils/araredo_calc.py

def calc_araredo(lowest_odds, median_odds, top3_ratio):
    score = 0
    if lowest_odds > 10: score += 30
    if median_odds > 25: score += 25
    if top3_ratio < 0.25: score += 30
    if lowest_odds > 30: score += 15
    return min(score, 100)