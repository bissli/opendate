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
    """Pendulum timezone for a zone name.

    Parameters
    ----------
    name : str, default 'US/Eastern'
        IANA zone name. 'US/Eastern' and 'America/New_York' are the same
        zone on every date.

    Returns
    -------
    zoneinfo.ZoneInfo
        A pendulum Timezone.

    Raises
    ------
    pendulum.tz.exceptions.InvalidTimezone
        name is no zone pendulum knows. A ValueError subclass.
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
        An IANA name, or None where the tzinfo carries none. A `dateutil`
        tzfile carries no name, so it takes the tail of the path it
        loaded, where pendulum knows that tail as a zone.
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


def normalize_timezone(
    tz: _datetime.tzinfo | str | None,
    when: _datetime.datetime | None = None,
) -> _datetime.tzinfo | None:
    """Return the pendulum timezone standing for any tzinfo.

    Parameters
    ----------
    tz : datetime.tzinfo or str or None
        Timezone to rebuild, or a zone name, so a caller may hand a name
        wherever a tzinfo goes. None passes through.
    when : datetime.datetime or None, default None
        Aware instant carrying `tz` itself, for a zone that names
        itself nowhere. None reads the offset against no instant, which
        a fixed zone answers and a daylight-saving one does not.

    Returns
    -------
    datetime.tzinfo or None
        `tz` where pendulum already owns it, else pendulum's timezone for
        the name `tz` carries, else a fixed zone at the offset `tz`
        reports at `when`, UTC for a zero offset. A zone whose offset
        differs between January and July of `when`'s year, or that
        reports none, comes back unchanged.

    Raises
    ------
    pendulum.tz.exceptions.InvalidTimezone
        tz is a str no zone answers to. No other input raises.

    See Also
    --------
    opendate.constants.zone_name : the name lookup this rebuilds from
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
    'SU': WeekDay.SUNDAY,
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

TIMEOFFSET = re.compile(r'^(?P<time>.*\d)\s*(?P<offset>Z|[-+]\d{2}:\d{2}|[-+]\d{4})$')
