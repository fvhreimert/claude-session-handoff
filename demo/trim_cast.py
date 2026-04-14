#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trim time from the start/end of an asciinema cast and optionally speed it up."
    )
    parser.add_argument("src", help="Input .cast file")
    parser.add_argument("dst", help="Output .cast file")
    parser.add_argument(
        "--trim-start",
        type=float,
        default=0.0,
        help="Seconds to remove from the beginning. Default: 0.",
    )
    parser.add_argument(
        "--trim-end",
        type=float,
        default=0.0,
        help="Seconds to remove from the end. Default: 0.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed multiplier. 1.25 means 25%% faster. Default: 1.0.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.src)
    dst = Path(args.dst)

    if args.speed <= 0:
        raise SystemExit("--speed must be greater than 0")
    if args.trim_start < 0 or args.trim_end < 0:
        raise SystemExit("--trim-start and --trim-end must be non-negative")

    with src.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()

    if not lines:
        raise SystemExit(f"Empty cast file: {src}")

    header = lines[0]
    events = [json.loads(line) for line in lines[1:]]

    absolute_events: list[list] = []
    elapsed = 0.0
    for event in events:
        elapsed += float(event[0])
        absolute_events.append([elapsed, event[1], event[2]])

    total_duration = absolute_events[-1][0] if absolute_events else 0.0
    start_at = args.trim_start
    end_at = max(start_at, total_duration - args.trim_end)

    filtered = [event for event in absolute_events if start_at <= event[0] <= end_at]

    if not filtered:
        raise SystemExit("No events remain after trimming.")

    rewritten: list[list] = []
    previous_time = start_at
    for absolute_time, stream, payload in filtered:
        adjusted_delta = (absolute_time - previous_time) / args.speed
        if not rewritten:
            adjusted_delta = 0.0
        rewritten.append([round(adjusted_delta, 6), stream, payload])
        previous_time = absolute_time

    with dst.open("w", encoding="utf-8") as handle:
        handle.write(header)
        for event in rewritten:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")

    print(f"Wrote {dst}")
    print(f"Original duration: {total_duration:.2f}s")
    print(f"Trimmed start: {args.trim_start:.2f}s")
    print(f"Trimmed end: {args.trim_end:.2f}s")
    print(f"Speed multiplier: {args.speed:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
