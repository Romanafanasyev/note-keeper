# scripts/bump_version.py
def bump(version: str) -> str:
    major, minor = map(int, version.strip().split("."))
    return f"{major}.{minor + 1}"


with open("VERSION", "r+", encoding="utf-8") as f:
    current = f.read().strip()
    new = bump(current)
    f.seek(0)
    f.write(new)
    f.truncate()

print(new)
