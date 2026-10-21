"""Parsing and storing the play counts the game client reports.

The client sends ``count_log`` as a string holding an object with a ``playDatas`` list. Each entry
is ``"<song title>*<count 1>*...*<count 8>"``: the play count of each of the song's eight charts.
The string uses single quotes, so it is read as a Python literal when it is not valid JSON.
"""

import ast
import hashlib
import io
import json
import re
import tokenize
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, insert, select
from sqlalchemy.engine import Connection

from app.db_session import music_tb, playcount_tb, report_tb, user_tb

CHARTS_PER_SONG = 8
MAX_SONGS = 1000
# playcount_tb.count is a signed MySQL INT
MAX_COUNT = 2**31 - 1
# a log is an object holding a list of strings (two levels); the rest is slack for extra fields
MAX_DEPTH = 4

# titles the client spells differently from music_tb
TITLE_ALIASES = {"오르트 구름": "Oort Cloud"}

# ASCII digits only: int() alone also takes "+2", "1_000", " 3" and non-ASCII digits
COUNT_PATTERN = re.compile(r"[0-9]{1,10}")
# an escape such as "\ud800" in the log decodes to half of a surrogate pair, which UTF-8 (and so MySQL
# and the JSON response) cannot hold
SURROGATE = re.compile("[\ud800-\udfff]")

# the tokens a count log is made of; see check_shape
_OPEN, _CLOSE, _SEPARATORS = {"{", "["}, {"}", "]"}, {":", ","}
_KEYWORDS = {"True", "False", "None", "true", "false", "null"}
_LAYOUT = {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
# a bracket after a value would be a subscript ("None[0][0]..."), so it may only follow these
_BEFORE_OPEN = {None, *_OPEN, *_SEPARATORS}
MAX_NUMBER_CHARS = 20


class CountLogError(ValueError):
    """The count log could not be read."""


class ReportConflict(Exception):
    """A report id the device has used before, sent again with different play counts."""


@dataclass(frozen=True)
class SongCounts:
    title: str
    counts: tuple[int, ...]


@dataclass(frozen=True)
class SaveResult:
    saved: int
    unknown_titles: list[str]
    duplicate: bool


def _tokens(count_log: str):
    try:
        yield from tokenize.generate_tokens(io.StringIO(count_log).readline)
    except (tokenize.TokenError, SyntaxError) as e:
        raise CountLogError("count_log is neither JSON nor a literal") from e


def check_shape(count_log: str) -> None:
    """Lets through only objects and lists of strings, numbers and keywords, MAX_DEPTH levels deep.

    json.loads and ast.literal_eval recurse while they parse, so "[" * 150000, "-" * 150000 + "1"
    or "None" + "[0]" * 100000 make them raise RecursionError or MemoryError instead of a parse
    error. The tokenizer does not recurse, and this loop stops at the first token a count log
    cannot contain: operators, parentheses, subscripts, names, prefixed strings or f-strings.
    """
    depth, previous = 0, None
    for tok in _tokens(count_log):
        if tok.type in _LAYOUT:
            continue
        if tok.type == tokenize.OP and tok.string in _OPEN:
            depth += 1
            if previous not in _BEFORE_OPEN or depth > MAX_DEPTH:
                raise CountLogError(f"count_log must be objects and lists at most {MAX_DEPTH} deep")
        elif tok.type == tokenize.OP and tok.string in _CLOSE:
            depth -= 1
        elif not (
            (tok.type == tokenize.OP and tok.string in _SEPARATORS)
            or (tok.type == tokenize.STRING and tok.string[0] in "'\"")
            or (tok.type == tokenize.NAME and tok.string in _KEYWORDS)
            or (tok.type == tokenize.NUMBER and len(tok.string) <= MAX_NUMBER_CHARS)
        ):
            raise CountLogError(f"count_log may not contain {tok.string[:20]!r}")
        previous = tok.string if tok.type == tokenize.OP else "value"


def _load(count_log: str):
    try:
        return json.loads(count_log)
    except ValueError:
        return ast.literal_eval(count_log)


def parse_count_log(count_log: str) -> list[SongCounts]:
    check_shape(count_log)
    try:
        data = _load(count_log)
    # TypeError: an unhashable key such as {[]: 1}; the rest is kept in case check_shape misses one
    except (ValueError, TypeError, SyntaxError, RecursionError, MemoryError) as e:
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
        title = parts[0].strip()
        if len(parts) != CHARTS_PER_SONG + 1 or not title:
            raise CountLogError(f"playDatas[{i}] needs a title and {CHARTS_PER_SONG} counts")
        if SURROGATE.search(title):
            raise CountLogError(f"playDatas[{i}] has a title that is not valid Unicode text")
        if not all(COUNT_PATTERN.fullmatch(c) for c in parts[1:]):
            raise CountLogError(f"playDatas[{i}] has a count that is not a non-negative integer")
        counts = tuple(int(c) for c in parts[1:])
        if max(counts) > MAX_COUNT:
            raise CountLogError(f"playDatas[{i}] has a count above {MAX_COUNT}")
        songs.append(SongCounts(TITLE_ALIASES.get(title, title), counts))
    return combine_entries(songs)


def combine_entries(songs: list[SongCounts]) -> list[SongCounts]:
    """Adds up the entries that name the same song (a title twice, or a title and its alias), so a
    report stores one row per chart."""
    totals: dict[str, tuple[int, ...]] = {}
    for song in songs:
        previous = totals.get(song.title, (0,) * CHARTS_PER_SONG)
        totals[song.title] = tuple(a + b for a, b in zip(previous, song.counts, strict=True))
    if any(max(counts) > MAX_COUNT for counts in totals.values()):
        raise CountLogError(f"the counts of one song add up to more than {MAX_COUNT}")
    return [SongCounts(title, counts) for title, counts in totals.items()]


def counts_digest(songs: list[SongCounts]) -> str:
    """SHA-256 of the play counts as parsed, so the same report sent in another quoting style matches."""
    canonical = json.dumps([[s.title, *s.counts] for s in songs], ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


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


def insert_ignore(table):
    """An INSERT that skips a row whose key is already there, in MySQL and in SQLite."""
    return insert(table).prefix_with("IGNORE", dialect="mysql").prefix_with("OR IGNORE", dialect="sqlite")


def save_play_counts(conn: Connection, device_id: str, report_id: str, songs: list[SongCounts]) -> SaveResult:
    """Registers the device if it is new, records the report and appends one row per chart.

    Runs inside the caller's transaction, so either everything is stored or nothing is. A report id
    the device has sent before marks a retry: nothing is written and the result counts the rows the
    first delivery stored. If the play counts differ from the first delivery's, the id has been reused
    for another report and ReportConflict is raised.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    digest = counts_digest(songs)
    # the first report of a device creates it; later reports leave its first-seen time alone
    conn.execute(insert_ignore(user_tb).values(device_id=device_id, insert_date=now))

    keys = first_chart_keys(conn, {s.title for s in songs})
    unknown = [s.title for s in songs if s.title not in keys]

    # (device_id, report_id) is report_tb's primary key: of two concurrent deliveries of one report,
    # the second waits for the first to commit and then inserts nothing
    inserted = conn.execute(
        insert_ignore(report_tb).values(
            device_id=device_id, report_id=report_id, reported_at=now, counts_sha256=digest
        )
    ).rowcount
    if not inserted:
        # locking reads see the first delivery's rows even when this transaction's snapshot predates
        # its commit (MySQL's REPEATABLE READ); SQLite has no row locks and ignores them
        first_digest = conn.execute(
            select(report_tb.c.counts_sha256)
            .where(report_tb.c.device_id == device_id, report_tb.c.report_id == report_id)
            .with_for_update(read=True)
        ).scalar_one()
        if first_digest != digest:
            raise ReportConflict(f"report_id {report_id} was already used for other play counts")
        stored = conn.execute(
            select(func.count())
            .select_from(playcount_tb)
            .where(playcount_tb.c.device_id == device_id, playcount_tb.c.report_id == report_id)
            .with_for_update(read=True)
        ).scalar_one()
        return SaveResult(stored, unknown, duplicate=True)

    rows = [
        {"device_id": device_id, "report_id": report_id, "music_key": keys[song.title] + j, "count": c}
        for song in songs
        if song.title in keys
        for j, c in enumerate(song.counts)
    ]
    if rows:
        conn.execute(insert(playcount_tb), rows)
    return SaveResult(len(rows), unknown, duplicate=False)
