import random

def chance(probability: float) -> bool:
    return random.random() < probability
