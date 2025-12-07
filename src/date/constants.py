from __future__ import annotations

import os
import re
import zoneinfo as _zoneinfo

import pendulum as _pendulum

# Cache platform check for to_string() performance
_IS_WINDOWS = os.name == 'nt'

# Year bounds for calendar caching
_MIN_YEAR = 1900
_MAX_YEAR = 2100


def Timezone(name: str = 'US/Eastern') -> _zoneinfo.ZoneInfo:
    """Create a timezone object with the specified name.

    Simple wrapper around Pendulum's Timezone function that ensures
    consistent timezone handling across the library. Note that 'US/Eastern'
    is equivalent to 'America/New_York' for all dates.
    """
    return _pendulum.tz.Timezone(name)


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
