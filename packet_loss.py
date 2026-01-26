from random import random


def should_drop(lost_rate: float) -> float:
    return random() < lost_rate
