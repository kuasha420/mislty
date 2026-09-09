"""
misltyd: Background service and device daemon for MisLTy.
"""

import sys
import argparse
import mislty

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="misltyd",
        description="Core background supervisor daemon for Qualcomm MDM9600 UFI modems"
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {mislty.__version__}"
    )
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run daemon in foreground (do not detach)"
    )
    return parser

def main(args=None):
    parser = build_parser()
    parsed = parser.parse_args(args)
    print(f"Starting misltyd {mislty.__version__} (foreground={parsed.foreground})...")

if __name__ == "__main__":
    main()
