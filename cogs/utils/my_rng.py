import random


def coinflip():
    return random.randint(0, 1)


def random_int(lowest: int, highest: int):
    return random.randint(lowest, highest)


def random_float():
    return random.uniform(0, 1)
