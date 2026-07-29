import argparse
from pathlib import Path


def bump(version: str, part: str) -> str:
    pieces = version.strip().split(".")
    if len(pieces) not in (2, 3) or not all(piece.isdigit() for piece in pieces):
        raise ValueError(f"Invalid version: {version!r}")

    major, minor, patch = (*map(int, pieces), 0)[:3]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "part",
        choices=("major", "minor", "patch"),
        default="patch",
        nargs="?",
    )
    args = parser.parse_args()

    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    new_version = bump(version_file.read_text(encoding="utf-8"), args.part)
    version_file.write_text(f"{new_version}\n", encoding="utf-8")
    print(new_version)


if __name__ == "__main__":
    main()
