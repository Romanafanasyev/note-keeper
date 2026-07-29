import json
import os
import re
import sys
from urllib.request import Request, urlopen

TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")


def check() -> None:
    token = os.environ.get("BOT_TOKEN", "")
    if not TOKEN_RE.fullmatch(token):
        raise RuntimeError("BOT_TOKEN is missing or invalid")

    request = Request(
        f"https://api.telegram.org/bot{token}/getMe",
        headers={"User-Agent": "planbot-health/0.10.1"},
    )
    with urlopen(request, timeout=10) as response:
        payload = json.load(response)

    bot_id = payload.get("result", {}).get("id")
    if payload.get("ok") is not True or not isinstance(bot_id, int) or bot_id <= 0:
        raise RuntimeError("Telegram returned an invalid bot identity")


def main() -> int:
    try:
        check()
    except Exception as exc:
        print(f"healthcheck failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
