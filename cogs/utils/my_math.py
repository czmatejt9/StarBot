import random


# generate a math equation within the specified range
def generate_equation(lowest: int = 1, highest: int = 100):
    operator = random.choice(["+", "-", "*", "/"])
    if operator == "+":
        a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        while a+b > highest:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} + {b} = ?", a+b
    elif operator == "-":
        a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        while a-b < lowest:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} - {b} = ?", a-b
    elif operator == "*":
        a, b = random.randint(lowest, highest // 10), random.randint(lowest, highest // 10)
        while a*b > highest:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} * {b} = ?", a*b
    elif operator == "/":
        a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        while a//b != a/b:
            a, b = random.randint(lowest, highest), random.randint(lowest, highest)
        return f"{a} / {b} = ?", a//b
