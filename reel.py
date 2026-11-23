"""Which story / visual style is being built, and where its files live.

    REEL_STORY=grandma  (default)  -> story.json,            build/grandma/
    REEL_STORY=umbrella            -> stories/umbrella.json, build/umbrella/
    REEL_STYLE=anime | illustrated (default: the story's own "style")
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
STORY = os.environ.get("REEL_STORY", "grandma")
STORY_FILE = os.path.join(ROOT, "story.json") if STORY == "grandma" else os.path.join(ROOT, "stories", STORY + ".json")
CFG = json.load(open(STORY_FILE))
STYLE = os.environ.get("REEL_STYLE", CFG.get("style", "illustrated"))
ANIME = STYLE == "anime"
B = os.path.join(ROOT, "build", STORY)
OUT = os.path.join(ROOT, "output")


def output_name():
    base = CFG.get("output", STORY)
    suffix = "_anime" if ANIME and CFG.get("style") != "anime" else ""
    return os.path.join(OUT, base + suffix + ".mp4")
