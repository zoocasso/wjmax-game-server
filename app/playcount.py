"""Parsing and storing the play counts the game client reports.

The client sends ``count_log`` as a string holding an object with a ``playDatas`` list. Each entry
is ``"<song title>*<count 1>*...*<count 8>"``: the play count of each of the song's eight charts.
The string uses single quotes, so it is read as a Python literal when it is not valid JSON.
"""

import ast
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, insert, select
from sqlalchemy.engine import Connection

from app.db_session import music_tb, playcount_tb, user_tb

CHARTS_PER_SONG = 8
MAX_SONGS = 1000

# titles the client spells differently from music_tb
TITLE_ALIASES = {"오르트 구름": "Oort Cloud"}


class CountLogError(ValueError):
    """The count log could not be read."""


@dataclass(frozen=True)
class SongCounts:
    title: str
    counts: tuple[int, ...]


def parse_count_log(count_log: str) -> list[SongCounts]:
    try:
        data = json.loads(count_log)
    except json.JSONDecodeError:
        try:
            data = ast.literal_eval(count_log)
        except (ValueError, SyntaxError) as e:
            raise CountLogError("count_log is neither JSON nor a literal") from e
    if not isinstance(data, dict) or not isinstance(data.get("playDatas"), list):
        raise CountLogError("count_log has no playDatas list")
    entries = data["playDatas"]
    if len(entries) > MAX_SONGS:
        raise CountLogError(f"more than {MAX_SONGS} songs")

    songs = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, str):
            raise CountLogError(f"playDatas[{i}] is not a string")
        # the title itself may contain '*', so the counts are taken from the right
        parts = entry.rsplit("*", CHARTS_PER_SONG)
        if len(parts) != CHARTS_PER_SONG + 1 or not parts[0]:
            raise CountLogError(f"playDatas[{i}] needs a title and {CHARTS_PER_SONG} counts")
        try:
            counts = tuple(int(c) for c in parts[1:])
        except ValueError as e:
            raise CountLogError(f"playDatas[{i}] has a count that is not an integer") from e
        if any(c < 0 for c in counts):
            raise CountLogError(f"playDatas[{i}] has a negative count")
        title = parts[0].strip()
        songs.append(SongCounts(TITLE_ALIASES.get(title, title), counts))
    return songs


def first_chart_keys(conn: Connection, titles: set[str]) -> dict[str, int]:
    """The first music_key of each song, in one query."""
    if not titles:
        return {}
    rows = conn.execute(
        select(music_tb.c.name, func.min(music_tb.c.music_key))
        .where(music_tb.c.name.in_(titles))
        .group_by(music_tb.c.name)
    )
    return {name: key for name, key in rows}


def save_play_counts(conn: Connection, device_id: str, songs: list[SongCounts]) -> tuple[int, list[str]]:
    """Registers the device if it is new and appends one row per chart.

    Runs inside the caller's transaction, so either everything is stored or nothing is.
    Returns the number of rows stored and the titles that are not in music_tb.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    # the first report of a device creates it; later reports leave its first-seen time alone
    conn.execute(
        insert(user_tb)
        .prefix_with("IGNORE", dialect="mysql")
        .prefix_with("OR IGNORE", dialect="sqlite")
        .values(device_id=device_id, insert_date=now)
    )

    keys = first_chart_keys(conn, {s.title for s in songs})
    rows, unknown = [], []
    for song in songs:
        start = keys.get(song.title)
        if start is None:
            unknown.append(song.title)
            continue
        rows += [
            {"device_id": device_id, "music_key": start + j, "count": c} for j, c in enumerate(song.counts)
        ]
    if rows:
        conn.execute(insert(playcount_tb), rows)
    return len(rows), unknown
