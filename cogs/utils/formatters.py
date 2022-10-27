from datetime import datetime


def format_seconds(seconds: int):
    return datetime.strptime(str(seconds), "%S").strftime("`% minutes and %S seconds`")
