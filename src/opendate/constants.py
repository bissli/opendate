from __future__ import annotations

import datetime as _datetime
import os
import re
import zoneinfo as _zoneinfo

import pendulum as _pendulum

_IS_WINDOWS = os.name == 'nt'

MIN_YEAR = 1900
MAX_YEAR = 2100


def Timezone(name: str = 'US/Eastern') -> _zoneinfo.ZoneInfo:
    """Create a timezone object with the specified name.

    Simple wrapper around Pendulum's Timezone function that ensures
    consistent timezone handling across the library. Note that 'US/Eastern'
    is equivalent to 'America/New_York' for all dates.
    """
    return _pendulum.tz.Timezone(name)


PENDULUM_TIMEZONES = (_pendulum.tz.Timezone, _pendulum.tz.FixedTimezone)


def zone_name(tz: _datetime.tzinfo) -> str | None:
    """The name of the zone a tzinfo carries, or None where it has none.

    Parameters
    ----------
    tz : datetime.tzinfo
        Timezone to read a name off.

    Returns
    -------
    str or None
        An IANA name, or None where the tzinfo carries none.

    Notes
    -----
    - `zoneinfo` and pendulum publish the name as `key`, `pytz` as
      `zone`. Neither exposes the other, so reading both in turn names
      one of them and never the wrong one.
    - `dateutil` publishes no name at all: a tzfile knows only the path
      it loaded, so the tail of that path is read back and kept only
      where it names a zone pendulum knows. A dateutil release that
      renames that attribute costs the name, not correctness - an
      unnamed zone still settles on its offset.
    """
    name = getattr(tz, 'key', None) or getattr(tz, 'zone', None)
    if name:
        return name
    filename = getattr(tz, '_filename', None)
    if not filename:
        return None
    parts = filename.split('/')
    known = _pendulum.tz.timezones()
    for depth in (2, 3, 1):
        candidate = '/'.join(parts[-depth:])
        if candidate in known:
            return candidate
    return None


def normalize_timezone(tz: _datetime.tzinfo | str | None,
                       when: _datetime.datetime | None = None
                       ) -> _datetime.tzinfo | None:
    """Return the pendulum timezone standing for any tzinfo.

    Parameters
    ----------
    tz : datetime.tzinfo or str or None
        Timezone to rebuild. None passes through.
    when : datetime.datetime or None, default None
        Aware instant carrying `tz` itself, for a zone that names
        itself nowhere. None reads the offset against no instant, which
        a fixed zone answers and a daylight-saving one does not.

    Returns
    -------
    datetime.tzinfo or None
        `tz` where pendulum already owns it, else pendulum's own
        timezone for the same zone, else `tz` unchanged.

    See Also
    --------
    opendate.constants.zone_name : the name lookup this rebuilds from

    Notes
    -----
    - pendulum answers `.timezone` and `.tz` for its own two tzinfo
      classes only, and rebuilds every derived value from that answer.
      A DateTime holding any other tzinfo therefore comes back naive
      from `deepcopy`, and naive AND shifted by its own offset from
      `add` or `subtract`. A database driver hands back exactly such a
      tzinfo: psycopg3 a `zoneinfo.ZoneInfo`, psycopg2 a fixed
      `datetime.timezone`.
    - A zone that names itself keeps the name, so later arithmetic
      crosses a daylight-saving boundary the way that zone does.
    - A zone that names itself nowhere settles on the offset it reports
      at `when`, and ONLY where that offset holds across the year.
      Freezing one whose offset moves with the season would answer
      plausibly and wrongly the moment a value crossed a transition, so
      such a zone is handed back as it arrived instead - unrepaired,
      which is at least loud.
    - A zero offset settles on UTC rather than on a fixed zone of the
      same offset, so one zone object serves the whole library.
    - A sub-second offset floors rather than truncating toward zero, so
      a negative one rounds the same direction as a positive one.
    - Rebuilding is a repair, so it never raises: a name pendulum
      rejects falls through to the offset, and a tzinfo that answers
      neither is handed back.
    - A str is taken as a zone name, so a caller may hand one wherever
      a tzinfo goes. A name no zone answers to raises, unlike every
      other input here.
    """
    if tz is None or isinstance(tz, PENDULUM_TIMEZONES):
        return tz
    if isinstance(tz, str):
        return Timezone(tz)

    name = zone_name(tz)
    if name is not None:
        try:
            return Timezone(name)
        except Exception:
            pass

    try:
        offset = tz.utcoffset(when)
        if (offset is not None and when is not None
                and tz.utcoffset(when.replace(month=1, day=15))
                != tz.utcoffset(when.replace(month=7, day=15))):
            return tz
    except Exception:
        return tz

    if offset is None:
        return tz
    if not offset:
        return UTC
    return _pendulum.tz.fixed_timezone(offset // _datetime.timedelta(seconds=1))


UTC = Timezone('UTC')
GMT = Timezone('GMT')
EST = Timezone('US/Eastern')
LCL = _pendulum.tz.Timezone(_pendulum.tz.get_local_timezone().name)

WeekDay = _pendulum.day.WeekDay

WEEKDAY_SHORTNAME = {
    'MO': WeekDay.MONDAY,
    'TU': WeekDay.TUESDAY,
    'WE': WeekDay.WEDNESDAY,
    'TH': WeekDay.THURSDAY,
    'FR': WeekDay.FRIDAY,
    'SA': WeekDay.SATURDAY,
    'SU': WeekDay.SUNDAY
}


MONTH_SHORTNAME = {
    'jan': 1,
    'feb': 2,
    'mar': 3,
    'apr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'sep': 9,
    'oct': 10,
    'nov': 11,
    'dec': 12,
}

DATEMATCH = re.compile(r'^(?P<d>N|T|Y|P|M)(?P<n>[-+]?\d+)?(?P<b>b?)?$')

# Only the forms that spell minutes, so a dash inside a time - the
# '45' of '14-30-45' - cannot be read as an offset.
TIMEOFFSET = re.compile(r'^(?P<time>.*\d)\s*(?P<offset>Z|[-+]\d{2}:\d{2}|[-+]\d{4})$')
