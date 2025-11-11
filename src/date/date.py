import calendar
import contextlib
import datetime as _datetime
import logging
import operator
import os
import re
import time
import warnings
import zoneinfo as _zoneinfo
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from functools import lru_cache, partial, wraps
from typing import Self

import dateutil as _dateutil
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import pendulum as _pendulum

warnings.simplefilter(action='ignore', category=DeprecationWarning)

logger = logging.getLogger(__name__)

__all__ = [
    'Date',
    'DateTime',
    'Interval',
    'Time',
    'Timezone',
    'EST',
    'UTC',
    'GMT',
    'LCL',
    'expect_native_timezone',
    'expect_utc_timezone',
    'prefer_native_timezone',
    'prefer_utc_timezone',
    'expect_date',
    'expect_datetime',
    'expect_time',
    'expect_date_or_datetime',
    'Entity',
    'NYSE',
    'WEEKDAY_SHORTNAME',
    'WeekDay',
    ]


def Timezone(name:str = 'US/Eastern') -> _zoneinfo.ZoneInfo:
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


# def caller_entity(func):
    # """Helper to get current entity from function"""
    # # general frame args inspect
    # import inspect
    # frame = inspect.currentframe()
    # outer_frames = inspect.getouterframes(frame)
    # caller_frame = outer_frames[1][0]
    # args = inspect.getargvalues(caller_frame)
    # # find our entity
    # param = inspect.signature(func).parameters.get('entity')
    # default = param.default if param else NYSE
    # entity = args.locals['kwargs'].get('entity', default)
    # return entity


def isdateish(x) -> bool:
    return isinstance(x, _datetime.date | _datetime.datetime | _datetime.time | pd.Timestamp | np.datetime64)


def parse_arg(typ, arg):
    """Parse argument to specified type or 'smart' to preserve Date/DateTime.
    """
    if not isdateish(arg):
        return arg

    if typ == 'smart':
        if isinstance(arg, Date | DateTime):
            return arg
        if isinstance(arg, _datetime.datetime | pd.Timestamp | np.datetime64):
            return DateTime.instance(arg)
        if isinstance(arg, _datetime.date):
            return Date.instance(arg)
        if isinstance(arg, _datetime.time):
            return Time.instance(arg)
        return arg

    if typ == _datetime.datetime:
        return DateTime.instance(arg)
    if typ == _datetime.date:
        return Date.instance(arg)
    if typ == _datetime.time:
        return Time.instance(arg)
    return arg


def parse_args(typ, *args):
    """Parse args to specified type or 'smart' mode.
    """
    this = []
    for a in args:
        if isinstance(a, Sequence) and not isinstance(a, str):
            this.append(parse_args(typ, *a))
        else:
            this.append(parse_arg(typ, a))
    return this


def expect(func=None, *, typ: type[_datetime.date] | str = None, exclkw: bool = False) -> Callable:
    """Decorator to force input type of date/datetime inputs.

    typ can be _datetime.date, _datetime.datetime, _datetime.time, or 'smart'
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            args = parse_args(typ, *args)
            if not exclkw:
                for k, v in kwargs.items():
                    if isdateish(v):
                        kwargs[k] = parse_arg(typ, v)
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    return decorator(func)


expect_date = partial(expect, typ=_datetime.date)
expect_datetime = partial(expect, typ=_datetime.datetime)
expect_time = partial(expect, typ=_datetime.time)
expect_date_or_datetime = partial(expect, typ='smart')


def type_class(typ, obj):
    if isinstance(typ, str):
        if typ == 'Date':
            return Date
        if typ == 'DateTime':
            return DateTime
        if typ == 'Interval':
            return Interval
    if typ:
        return typ
    if obj.__class__ in {_pendulum.Interval, Interval}:
        return Interval
    if obj.__class__ in {_datetime.datetime, _pendulum.DateTime, DateTime}:
        return DateTime
    if obj.__class__ in {_datetime.date, _pendulum.Date, Date}:
        return Date
    raise ValueError(f'Unknown type {typ}')


def store_entity(func=None, *, typ=None):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _entity = self._entity
        d = type_class(typ, self).instance(func(self, *args, **kwargs))
        d._entity = _entity
        return d
    if func is None:
        return partial(store_entity, typ=typ)
    return wrapper


def store_both(func=None, *, typ=None):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        _entity = self._entity
        _business = self._business
        d = type_class(typ, self).instance(func(self, *args, **kwargs))
        d._entity = _entity
        d._business = _business
        return d
    if func is None:
        return partial(store_both, typ=typ)
    return wrapper


def reset_business(func):
    """Decorator to reset business mode after function execution.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self._business = False
            self._start._business = False
            self._end._business = False
    return wrapper


def normalize_date_datetime_pairs(func):
    """Decorator to normalize mixed Date/DateTime pairs to DateTime.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) >= 3:
            cls_or_self, begdate, enddate = args[0], args[1], args[2]
            rest_args = args[3:]

            tz = UTC
            if isinstance(begdate, DateTime) and begdate.tzinfo:
                tz = begdate.tzinfo
            elif isinstance(enddate, DateTime) and enddate.tzinfo:
                tz = enddate.tzinfo

            if isinstance(begdate, Date) and not isinstance(begdate, DateTime):
                if isinstance(enddate, DateTime):
                    begdate = DateTime(begdate.year, begdate.month, begdate.day, tzinfo=tz)
            elif isinstance(enddate, Date) and not isinstance(enddate, DateTime):
                if isinstance(begdate, DateTime):
                    enddate = DateTime(enddate.year, enddate.month, enddate.day, tzinfo=tz)

            args = (cls_or_self, begdate, enddate) + rest_args

        return func(*args, **kwargs)
    return wrapper


def prefer_utc_timezone(func, force:bool = False) -> Callable:
    """Return datetime as UTC.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        d = func(*args, **kwargs)
        if not d:
            return
        if not force and d.tzinfo:
            return d
        return d.replace(tzinfo=UTC)
    return wrapper


def prefer_native_timezone(func, force:bool = False) -> Callable:
    """Return datetime as native.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        d = func(*args, **kwargs)
        if not d:
            return
        if not force and d.tzinfo:
            return d
        return d.replace(tzinfo=LCL)
    return wrapper


expect_native_timezone = partial(prefer_native_timezone, force=True)
expect_utc_timezone = partial(prefer_utc_timezone, force=True)


class Entity(ABC):
    """Abstract base class for calendar entities with business day definitions.

    This class defines the interface for calendar entities that provide
    business day information, such as market open/close times and holidays.
    Not available in pendulum.

    Concrete implementations (like NYSE) provide specific calendar rules
    for different business contexts.
    """

    tz = UTC

    @staticmethod
    @abstractmethod
    def business_days(begdate: _datetime.date, enddate: _datetime.date):
        """Returns all business days over a range"""

    @staticmethod
    @abstractmethod
    def business_hours(begdate: _datetime.date, enddate: _datetime.date):
        """Returns all business open and close times over a range"""

    @staticmethod
    @abstractmethod
    def business_holidays(begdate: _datetime.date, enddate: _datetime.date):
        """Returns only holidays over a range"""


class NYSE(Entity):
    """New York Stock Exchange calendar entity.

    Provides business day definitions, market hours, and holidays
    according to the NYSE trading calendar. Uses pandas_market_calendars
    for the underlying implementation.

    This entity is used as the default for business day calculations
    throughout the library.

    Note: First call to business day methods loads NYSE calendar data
          (~200ms for default 50-year range). Subsequent calls are cached
          and very fast (~0.01ms). Additional ranges can be loaded on-demand
          by calling business_days(begdate, enddate) explicitly.
    """

    BEGDATE = _datetime.date(2000, 1, 1)
    ENDDATE = _datetime.date(2050, 1, 1)
    calendar = mcal.get_calendar('NYSE')

    tz = EST

    @staticmethod
    def business_days(begdate=None, enddate=None) -> set:
        """Get business days for a date range (loads and caches by decade).

        Parameters
            begdate: Start date (defaults to 2000-01-01)
            enddate: End date (defaults to 2050-01-01)

        Returns
            Set of Date objects representing business days

        Note: Calendar data is loaded and cached in decade chunks for efficiency.
              Requesting specific date ranges will load additional decades as needed.
              Queries for dates beyond year 2100 return an empty set to avoid
              pandas timestamp overflow and NYSE calendar data limitations.
        """
        if begdate is None:
            begdate = NYSE.BEGDATE
        if enddate is None:
            enddate = NYSE.ENDDATE

        max_year = 2100
        
        if begdate.year > max_year:
            return set()

        decade_start = _datetime.date(begdate.year // 10 * 10, 1, 1)
        next_decade_year = (enddate.year // 10 + 1) * 10
        if next_decade_year > max_year:
            decade_end = _datetime.date(max_year, 12, 31)
        else:
            decade_end = _datetime.date(next_decade_year, 1, 1)

        return NYSE._get_business_days_cached(decade_start, decade_end)

    @staticmethod
    @lru_cache(maxsize=32)
    def _get_business_days_cached(begdate: _datetime.date, enddate: _datetime.date) -> set:
        """Internal method to load and cache business days by decade.

        Cache size of 32 allows ~320 years of cached data.
        """
        return {Date.instance(d.date())
                for d in NYSE.calendar.valid_days(begdate, enddate)}

    @staticmethod
    @lru_cache
    def business_hours(begdate=None, enddate=None) -> dict:
        """Get market hours for a date range.

        Parameters
            begdate: Start date (defaults to 2000-01-01)
            enddate: End date (defaults to 2050-01-01)

        Returns
            Dict mapping dates to (open_time, close_time) tuples
        """
        if begdate is None:
            begdate = NYSE.BEGDATE
        if enddate is None:
            enddate = NYSE.ENDDATE

        df = NYSE.calendar.schedule(begdate, enddate, tz=EST)
        open_close = [(DateTime.instance(o.to_pydatetime()),
                       DateTime.instance(c.to_pydatetime()))
                      for o, c in zip(df.market_open, df.market_close)]
        return dict(zip(df.index.date, open_close))

    @staticmethod
    @lru_cache
    def business_holidays(begdate=None, enddate=None) -> set:
        """Get business holidays for a date range.

        Parameters
            begdate: Start date (defaults to 2000-01-01)
            enddate: End date (defaults to 2050-01-01)

        Returns
            Set of Date objects representing holidays
        """
        if begdate is None:
            begdate = NYSE.BEGDATE
        if enddate is None:
            enddate = NYSE.ENDDATE

        return {Date.instance(d.date())
                for d in map(pd.to_datetime, NYSE.calendar.holidays().holidays)
                if begdate <= d.date() <= enddate}


class DateBusinessMixin:
    """Mixin class providing business day functionality.

    This mixin adds business day awareness to Date and DateTime classes,
    allowing date operations to account for weekends and holidays according
    to a specified calendar entity.

    Features not available in pendulum:
    - Business day mode toggle
    - Entity-specific calendar rules
    - Business-aware date arithmetic
    """

    _entity: type[NYSE] = NYSE
    _business: bool = False

    def business(self) -> Self:
        """Switch to business day mode for date calculations.

        In business day mode, date arithmetic only counts business days
        as defined by the associated entity (default NYSE).

        Returns
            Self instance for method chaining
        """
        self._business = True
        return self

    @property
    def b(self) -> Self:
        """Shorthand property for business() method.

        Returns
            Self instance for method chaining
        """
        return self.business()

    def entity(self, entity: type[NYSE] = NYSE) -> Self:
        """Set the calendar entity for business day calculations.

        Parameters
            entity: Calendar entity class (defaults to NYSE)

        Returns
            Self instance for method chaining
        """
        self._entity = entity
        return self

    @store_entity
    def add(self, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, **kwargs) -> Self:
        """Add time periods to the current date or datetime.

        Extends pendulum's add method with business day awareness. When in business mode,
        only counts business days for the 'days' parameter.

        Parameters
            years: Number of years to add
            months: Number of months to add
            weeks: Number of weeks to add
            days: Number of days to add (business days if in business mode)
            **kwargs: Additional time units to add

        Returns
            New instance with added time
        """
        _business = self._business
        self._business = False
        if _business:
            if days == 0:
                return self._business_or_next()
            if days < 0:
                return self.business().subtract(days=abs(days))
            while days > 0:
                self = self._business_next(days=1)
                days -= 1
            return self
        return super().add(years, months, weeks, days, **kwargs)

    @store_entity
    def subtract(self, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0, **kwargs) -> Self:
        """Subtract wrapper
        If not business use Pendulum
        If business assume only days (for now) and use local logic
        """
        _business = self._business
        self._business = False
        if _business:
            if days == 0:
                return self._business_or_previous()
            if days < 0:
                return self.business().add(days=abs(days))
            while days > 0:
                self = self._business_previous(days=1)
                days -= 1
            return self
        kwargs = {k: -1*v for k,v in kwargs.items()}
        return super().add(-years, -months, -weeks, -days, **kwargs)

    @store_entity
    def first_of(self, unit: str, day_of_week: WeekDay | None = None) -> Self:
        """Returns an instance set to the first occurrence
        of a given day of the week in the current unit.
        """
        _business = self._business
        self._business = False
        self = super().first_of(unit, day_of_week)
        if _business:
            self = self._business_or_next()
        return self

    @store_entity
    def last_of(self, unit: str, day_of_week: WeekDay | None = None) -> Self:
        """Returns an instance set to the last occurrence
        of a given day of the week in the current unit.
        """
        _business = self._business
        self._business = False
        self = super().last_of(unit, day_of_week)
        if _business:
            self = self._business_or_previous()
        return self

    @store_entity
    def start_of(self, unit: str) -> Self:
        """Returns a copy of the instance with the time reset
        """
        _business = self._business
        self._business = False
        self = super().start_of(unit)
        if _business:
            self = self._business_or_next()
        return self

    @store_entity
    def end_of(self, unit: str) -> Self:
        """Returns a copy of the instance with the time reset
        """
        _business = self._business
        self._business = False
        self = super().end_of(unit)
        if _business:
            self = self._business_or_previous()
        return self

    @store_entity
    def previous(self, day_of_week: WeekDay | None = None) -> Self:
        """Modify to the previous occurrence of a given day of the week.
        """
        _business = self._business
        self._business = False
        self = super().previous(day_of_week)
        if _business:
            self = self._business_or_next()
        return self

    @store_entity
    def next(self, day_of_week: WeekDay | None = None) -> Self:
        """Modify to the next occurrence of a given day of the week.
        """
        _business = self._business
        self._business = False
        self = super().next(day_of_week)
        if _business:
            self = self._business_or_previous()
        return self

    @expect_date
    def business_open(self) -> bool:
        """Check if the date is a business day (market is open).
        """
        return self.is_business_day()

    @expect_date
    def is_business_day(self) -> bool:
        """Check if the date is a business day according to the entity calendar.
        """
        business_days = self._entity.business_days(self, self)
        return self in business_days

    @expect_date
    def business_hours(self) -> 'tuple[DateTime, DateTime]':
        """Get market open and close times for this date.

        Returns (None, None) if not a business day.
        """
        return self._entity.business_hours(self, self)\
            .get(self, (None, None))

    @store_both
    def _business_next(self, days=0):
        """Helper for cycling through N business day"""
        days = abs(days)
        while days > 0:
            try:
                self = super().add(days=1)
            except OverflowError:
                break
            if self.is_business_day():
                days -= 1
        return self

    @store_both
    def _business_previous(self, days=0):
        """Helper for cycling through N business day"""
        days = abs(days)
        while days > 0:
            try:
                self = super().add(days=-1)
            except OverflowError:
                break
            if self.is_business_day():
                days -= 1
        return self

    @store_entity
    def _business_or_next(self):
        self._business = False
        self = super().subtract(days=1)
        self = self._business_next(days=1)
        return self

    @store_entity
    def _business_or_previous(self):
        self._business = False
        self = super().add(days=1)
        self = self._business_previous(days=1)
        return self


class DateExtrasMixin:
    """Extended date functionality not provided by Pendulum.

    .. note::
        This mixin exists primarily for legacy backward compatibility.
        New code should prefer using built-in methods where possible.

    This mixin provides additional date utilities primarily focused on:
    - Financial date calculations (nearest month start/end)
    - Weekday-oriented date navigation
    - Relative date lookups

    These methods extend OpenDate functionality with features commonly
    needed in financial applications and reporting scenarios.
    """

    def nearest_start_of_month(self) -> Self:
        """Get the nearest start of month.

        If day <= 15, returns start of current month.
        If day > 15, returns start of next month.
        In business mode, adjusts to next business day if needed.
        """
        _business = self._business
        self._business = False
        if self.day > 15:
            d = self.end_of('month')
            if _business:
                return d.business().add(days=1)
            return d.add(days=1)
        d = self.start_of('month')
        if _business:
            return d.business().add(days=1)
        return d

    def nearest_end_of_month(self) -> Self:
        """Get the nearest end of month.

        If day <= 15, returns end of previous month.
        If day > 15, returns end of current month.
        In business mode, adjusts to previous business day if needed.
        """
        _business = self._business
        self._business = False
        if self.day <= 15:
            d = self.start_of('month')
            if _business:
                return d.business().subtract(days=1)
            return d.subtract(days=1)
        d = self.end_of('month')
        if _business:
            return d.business().subtract(days=1)
        return d

    def next_relative_date_of_week_by_day(self, day='MO') -> Self:
        """Get next occurrence of the specified weekday (or current date if already that day).
        """
        if self.weekday() == WEEKDAY_SHORTNAME.get(day):
            return self
        return self.next(WEEKDAY_SHORTNAME.get(day))

    def weekday_or_previous_friday(self) -> Self:
        """Return the date if it is a weekday, otherwise return the previous Friday.
        """
        if self.weekday() in {WeekDay.SATURDAY, WeekDay.SUNDAY}:
            return self.previous(WeekDay.FRIDAY)
        return self

    @classmethod
    def third_wednesday(cls, year, month) -> Self:
        """Calculate the date of the third Wednesday in a given month/year.

        .. deprecated::
            Use Date(year, month, 1).nth_of('month', 3, WeekDay.WEDNESDAY) instead.

        Parameters
            year: The year to use
            month: The month to use (1-12)

        Returns
            A Date object representing the third Wednesday of the specified month
        """
        return cls(year, month, 1).nth_of('month', 3, WeekDay.WEDNESDAY)


class Date(DateExtrasMixin, DateBusinessMixin, _pendulum.Date):
    """Date class extending pendulum.Date with business day and additional functionality.

    This class inherits all pendulum.Date functionality while adding:
    - Business day calculations with NYSE calendar integration
    - Additional date navigation methods
    - Enhanced parsing capabilities
    - Custom financial date utilities

    Unlike pendulum.Date, methods that create new instances return Date objects
    that preserve business status and entity association when chained.
    """

    def to_string(self, fmt: str) -> str:
        """Format date to string, handling platform-specific format codes.

        Automatically converts '%-' format codes to '%#' on Windows.
        """
        return self.strftime(fmt.replace('%-', '%#') if os.name == 'nt' else fmt)

    @store_entity(typ='Date')
    def replace(self, *args, **kwargs):
        """Replace method that preserves entity and business status.
        """
        return _pendulum.Date.replace(self, *args, **kwargs)

    @store_entity(typ='Date')
    def closest(self, *args, **kwargs):
        """Closest method that preserves entity and business status.
        """
        return _pendulum.Date.closest(self, *args, **kwargs)

    @store_entity(typ='Date')
    def farthest(self, *args, **kwargs):
        """Farthest method that preserves entity and business status.
        """
        return _pendulum.Date.farthest(self, *args, **kwargs)

    @store_entity(typ='Date')
    def average(self, dt=None):
        """Modify the current instance to the average
        of a given instance (default now) and the current instance.

        Parameters
            dt: The date to average with (defaults to today)

        Returns
            A new Date object representing the average date
        """
        return _pendulum.Date.average(self, dt)

    @classmethod
    def fromordinal(cls, *args, **kwargs) -> Self:
        """Create a Date from an ordinal.

        Parameters
            n: The ordinal value

        Returns
            Date instance
        """
        result = _pendulum.Date.fromordinal(*args, **kwargs)
        return cls.instance(result)

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None) -> Self:
        """Create a Date from a timestamp.

        Parameters
            timestamp: Unix timestamp
            tz: Optional timezone (defaults to UTC)

        Returns
            Date instance
        """
        # Ensure timezone is always applied to get consistent results
        tz = tz or UTC
        dt = _datetime.datetime.fromtimestamp(timestamp, tz=tz)
        return cls(dt.year, dt.month, dt.day)

    @store_entity(typ='Date')
    def nth_of(self, unit: str, nth: int, day_of_week: WeekDay) -> Self:
        """Returns a new instance set to the given occurrence
        of a given day of the week in the current unit.

        Parameters
            unit: The unit to use ("month", "quarter", or "year")
            nth: The position of the day in the unit (1 to 5)
            day_of_week: The day of the week (pendulum.MONDAY to pendulum.SUNDAY)

        Returns
            A new Date object for the nth occurrence

        Raises
            ValueError: If the occurrence can't be found
        """
        return _pendulum.Date.nth_of(self, unit, nth, day_of_week)

    @classmethod
    def parse(
        cls,
        s: str | None,
        fmt: str = None,
        entity: Entity = NYSE,
        raise_err: bool = False,
    ) -> Self | None:
        """Convert a string to a date handling many different formats.

        Supports various date formats including:
        - Standard formats: YYYY-MM-DD, MM/DD/YYYY, MM/DD/YY, YYYYMMDD
        - Named months: DD-MON-YYYY, MON-DD-YYYY, Month DD, YYYY
        - Special codes: T (today), Y (yesterday), P (previous business day)
        - Business day offsets: T-3b, P+2b (add/subtract business days)
        - Custom format strings via fmt parameter

        Parameters
            s: String to parse or None
            fmt: Optional strftime format string for custom parsing
            entity: Calendar entity for business day calculations (default NYSE)
            raise_err: If True, raises ValueError on parse failure instead of returning None

        Returns
            Date instance or None if parsing fails and raise_err is False

        Examples
            Standard numeric formats:
            Date.parse('2020-01-15') → Date(2020, 1, 15)
            Date.parse('01/15/2020') → Date(2020, 1, 15)
            Date.parse('01/15/20') → Date(2020, 1, 15)
            Date.parse('20200115') → Date(2020, 1, 15)

            Named month formats:
            Date.parse('15-Jan-2020') → Date(2020, 1, 15)
            Date.parse('Jan 15, 2020') → Date(2020, 1, 15)
            Date.parse('15JAN2020') → Date(2020, 1, 15)

            Special codes:
            Date.parse('T') → today's date
            Date.parse('Y') → yesterday's date
            Date.parse('P') → previous business day
            Date.parse('M') → last day of previous month

            Business day offsets:
            Date.parse('T-3b') → 3 business days ago
            Date.parse('P+2b') → 2 business days after previous business day
            Date.parse('T+5') → 5 calendar days from today

            Custom format:
            Date.parse('15-Jan-2020', fmt='%d-%b-%Y') → Date(2020, 1, 15)
        """

        def date_for_symbol(s):
            if s == 'N':
                return cls.today()
            if s == 'T':
                return cls.today()
            if s == 'Y':
                return cls.today().subtract(days=1)
            if s == 'P':
                return cls.today().entity(entity).business().subtract(days=1)
            if s == 'M':
                return cls.today().start_of('month').subtract(days=1)

        def year(m):
            try:
                yy = int(m.group('y'))
                if yy < 100:
                    yy += 2000
            except IndexError:
                logger.debug('Using default this year')
                yy = cls.today().year
            return yy

        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, str):
            raise TypeError(f'Invalid type for date parse: {s.__class__}')

        if fmt:
            try:
                return cls(*time.strptime(s, fmt)[:3])
            except:
                if raise_err:
                    raise ValueError(f'Unable to parse {s} using fmt {fmt}')
                return

        with contextlib.suppress(ValueError):
            if float(s) and len(s) != 8:  # 20000101
                if raise_err:
                    raise ValueError('Invalid date: %s', s)
                return

        # special shortcode symbolic values: T, Y-2, P-1b
        if m := DATEMATCH.match(s):
            d = date_for_symbol(m.groupdict().get('d'))
            n = m.groupdict().get('n')
            if not n:
                return d
            n = int(n)
            b = m.groupdict().get('b')
            if b:
                assert b == 'b'
                d = d.entity(entity).business().add(days=n)
            else:
                d = d.add(days=n)
            return d
        if 'today' in s.lower():
            return cls.today()
        if 'yester' in s.lower():
            return cls.today().subtract(days=1)

        # Try ISO format first (most common in data)
        if m := re.match(r'^(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})$', s):
            mm = int(m.group('m'))
            dd = int(m.group('d'))
            yy = year(m)
            return cls(yy, mm, dd)

        # Try dateutil.parser for common formats
        with contextlib.suppress(TypeError, ValueError):
            return cls.instance(_dateutil.parser.parse(s))

        # Regex with Month Numbers (ordered by frequency)
        exps = (
            r'^(?P<m>\d{1,2})[/-](?P<d>\d{1,2})[/-](?P<y>\d{4})$',
            r'^(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})$',
            r'^(?P<m>\d{1,2})[/-](?P<d>\d{1,2})[/-](?P<y>\d{1,2})$',
            r'^(?P<m>\d{1,2})[/-](?P<d>\d{1,2})$',
        )
        for exp in exps:
            if m := re.match(exp, s):
                mm = int(m.group('m'))
                dd = int(m.group('d'))
                yy = year(m)
                return cls(yy, mm, dd)

        # Regex with Month Name
        exps = (
            r'^(?P<d>\d{1,2})[- ](?P<m>[A-Za-z]{3,})[- ](?P<y>\d{4})$',
            r'^(?P<m>[A-Za-z]{3,})[- ](?P<d>\d{1,2})[- ](?P<y>\d{4})$',
            r'^(?P<m>[A-Za-z]{3,}) (?P<d>\d{1,2}), (?P<y>\d{4})$',
            r'^(?P<d>\d{2})(?P<m>[A-Z][a-z]{2})(?P<y>\d{4})$',
            r'^(?P<d>\d{1,2})-(?P<m>[A-Z][a-z][a-z])-(?P<y>\d{2})$',
            r'^(?P<d>\d{1,2})-(?P<m>[A-Z]{3})-(?P<y>\d{2})$',
        )
        for exp in exps:
            if m := re.match(exp, s):
                try:
                    mm = MONTH_SHORTNAME[m.group('m').lower()[:3]]
                except KeyError:
                    logger.debug('Month name did not match MONTH_SHORTNAME')
                    continue
                dd = int(m.group('d'))
                yy = year(m)
                return cls(yy, mm, dd)

        if raise_err:
            raise ValueError('Failed to parse date: %s', s)

    @classmethod
    def instance(
        cls,
        obj: _datetime.date
        | _datetime.datetime
        | _datetime.time
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        raise_err: bool = False,
    ) -> Self | None:
        """Create a Date instance from various date-like objects.

        Converts datetime.date, datetime.datetime, pandas Timestamp,
        numpy datetime64, and other date-like objects to Date instances.

        Parameters
            obj: Date-like object to convert
            raise_err: If True, raises ValueError for None/NA values instead of returning None

        Returns
            Date instance or None if obj is None/NA and raise_err is False
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls:
            return obj

        if isinstance(obj, pd.Timestamp):
            obj = obj.to_pydatetime()
            return cls(obj.year, obj.month, obj.day)
        
        if isinstance(obj, np.datetime64):
            obj = np.datetime64(obj, 'us').astype(_datetime.datetime)
            return cls(obj.year, obj.month, obj.day)

        return cls(obj.year, obj.month, obj.day)

    @classmethod
    def today(cls) -> Self:
        d = _datetime.datetime.now(LCL)
        return cls(d.year, d.month, d.day)

    def isoweek(self) -> int | None:
        """Get ISO week number (1-52/53) following ISO week-numbering standard.
        """
        with contextlib.suppress(Exception):
            return self.isocalendar()[1]

    def lookback(self, unit='last') -> Self:
        """Get date in the past based on lookback unit.

        Supported units: 'last'/'day' (1 day), 'week', 'month', 'quarter', 'year'.
        Respects business day mode if enabled.
        """
        def _lookback(years=0, months=0, weeks=0, days=0):
            _business = self._business
            self._business = False
            d = self\
                .subtract(years=years, months=months, weeks=weeks, days=days)
            if _business:
                return d._business_or_previous()
            return d

        return {
            'day': _lookback(days=1),
            'last': _lookback(days=1),
            'week': _lookback(weeks=1),
            'month': _lookback(months=1),
            'quarter': _lookback(months=3),
            'year': _lookback(years=1),
            }.get(unit)


class Time(_pendulum.Time):
    """Time class extending pendulum.Time with additional functionality.

    This class inherits all pendulum.Time functionality while adding:
    - Enhanced parsing for various time formats
    - Default UTC timezone when created
    - Simple timezone conversion utilities

    Unlike pendulum.Time, this class has more lenient parsing capabilities
    and different timezone defaults.
    """

    @classmethod
    @prefer_utc_timezone
    def parse(cls, s: str | None, fmt: str | None = None, raise_err: bool = False) -> Self | None:
        """Parse time string in various formats.

        Supported formats:
        - hh:mm or hh.mm
        - hh:mm:ss or hh.mm.ss
        - hh:mm:ss.microseconds
        - Any of above with AM/PM
        - Compact: hhmmss or hhmmss.microseconds

        Returns Time with UTC timezone by default.

        Parameters
            s: String to parse or None
            fmt: Optional strftime format string for custom parsing
            raise_err: If True, raises ValueError on parse failure instead of returning None

        Returns
            Time instance with UTC timezone or None if parsing fails and raise_err is False

        Examples
            Basic time formats:
            Time.parse('14:30') → Time(14, 30, 0, 0, tzinfo=UTC)
            Time.parse('14.30') → Time(14, 30, 0, 0, tzinfo=UTC)
            Time.parse('14:30:45') → Time(14, 30, 45, 0, tzinfo=UTC)

            With microseconds:
            Time.parse('14:30:45.123456') → Time(14, 30, 45, 123456000, tzinfo=UTC)
            Time.parse('14:30:45,500000') → Time(14, 30, 45, 500000000, tzinfo=UTC)

            AM/PM formats:
            Time.parse('2:30 PM') → Time(14, 30, 0, 0, tzinfo=UTC)
            Time.parse('11:30 AM') → Time(11, 30, 0, 0, tzinfo=UTC)
            Time.parse('12:30 PM') → Time(12, 30, 0, 0, tzinfo=UTC)

            Compact formats:
            Time.parse('143045') → Time(14, 30, 45, 0, tzinfo=UTC)
            Time.parse('1430') → Time(14, 30, 0, 0, tzinfo=UTC)

            Custom format:
            Time.parse('14-30-45', fmt='%H-%M-%S') → Time(14, 30, 45, 0, tzinfo=UTC)
        """

        def seconds(m):
            try:
                return int(m.group('s'))
            except Exception:
                return 0

        def micros(m):
            try:
                return int(m.group('u'))
            except Exception:
                return 0

        def is_pm(m):
            try:
                return m.group('ap').lower() == 'pm'
            except Exception:
                return False

        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, str):
            raise TypeError(f'Invalid type for time parse: {s.__class__}')

        if fmt:
            try:
                return cls(*time.strptime(s, fmt)[3:6])
            except:
                if raise_err:
                    raise ValueError(f'Unable to parse {s} using fmt {fmt}')
                return

        exps = (
            r'^(?P<h>\d{1,2})[:.](?P<m>\d{2})([:.](?P<s>\d{2})([.,](?P<u>\d+))?)?( +(?P<ap>[aApP][mM]))?$',
            r'^(?P<h>\d{2})(?P<m>\d{2})((?P<s>\d{2})([.,](?P<u>\d+))?)?( +(?P<ap>[aApP][mM]))?$',
        )

        for exp in exps:
            if m := re.match(exp, s):
                hh = int(m.group('h'))
                mm = int(m.group('m'))
                ss = seconds(m)
                uu = micros(m)
                if is_pm(m) and hh < 12:
                    hh += 12
                return cls(hh, mm, ss, uu * 1000)

        with contextlib.suppress(TypeError, ValueError):
            return cls.instance(_dateutil.parser.parse(s))

        if raise_err:
            raise ValueError('Failed to parse time: %s', s)

    @classmethod
    def instance(
        cls,
        obj: _datetime.time
        | _datetime.datetime
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None,
        raise_err: bool = False,
    ) -> Self | None:
        """Create Time instance from time-like object.

        Adds UTC timezone by default unless obj is already a Time instance.
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls and not tz:
            return obj

        tz = tz or obj.tzinfo or UTC

        return cls(obj.hour, obj.minute, obj.second, obj.microsecond, tzinfo=tz)

    def in_timezone(self, tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo) -> Self:
        """Convert time to a different timezone.
        """
        _dt = DateTime.combine(Date.today(), self, tzinfo=self.tzinfo or UTC)
        return _dt.in_timezone(tz).time()

    in_tz = in_timezone


class DateTime(DateBusinessMixin, _pendulum.DateTime):
    """DateTime class extending pendulum.DateTime with business day and additional functionality.

    This class inherits all pendulum.DateTime functionality while adding:
    - Business day calculations with NYSE calendar integration
    - Enhanced timezone handling
    - Extended parsing capabilities
    - Custom utility methods for financial applications

    Unlike pendulum.DateTime:
    - today() returns start of day rather than current time
    - Methods preserve business status and entity when chaining
    - Has timezone handling helpers not present in pendulum
    """

    def epoch(self) -> float:
        """Translate a datetime object into unix seconds since epoch
        """
        return self.timestamp()

    @store_entity(typ='DateTime')
    def astimezone(self, *args, **kwargs):
        """Convert to a timezone-aware datetime in a different timezone.
        """
        return _pendulum.DateTime.astimezone(self, *args, **kwargs)

    @store_entity(typ='DateTime')
    def in_timezone(self, *args, **kwargs):
        """Convert to a timezone-aware datetime in a different timezone.
        """
        return _pendulum.DateTime.in_timezone(self, *args, **kwargs)

    @store_entity(typ='DateTime')
    def in_tz(self, *args, **kwargs):
        """Convert to a timezone-aware datetime in a different timezone.
        """
        return _pendulum.DateTime.in_tz(self, *args, **kwargs)

    @store_entity(typ='DateTime')
    def replace(self, *args, **kwargs):
        """Replace method that preserves entity and business status.
        """
        return _pendulum.DateTime.replace(self, *args, **kwargs)

    @classmethod
    def fromordinal(cls, *args, **kwargs) -> Self:
        """Create a DateTime from an ordinal.

        Parameters
            n: The ordinal value

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.fromordinal(*args, **kwargs)
        return cls.instance(result)

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None) -> Self:
        """Create a DateTime from a timestamp.

        Parameters
            timestamp: Unix timestamp
            tz: Optional timezone

        Returns
            DateTime instance
        """
        tz = tz or UTC
        result = _pendulum.DateTime.fromtimestamp(timestamp, tz)
        return cls.instance(result)

    @classmethod
    def strptime(cls, time_str, fmt) -> Self:
        """Parse a string into a DateTime according to a format.

        Parameters
            time_str: String to parse
            fmt: Format string

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.strptime(time_str, fmt)
        return cls.instance(result)

    @classmethod
    def utcfromtimestamp(cls, timestamp) -> Self:
        """Create a UTC DateTime from a timestamp.

        Parameters
            timestamp: Unix timestamp

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.utcfromtimestamp(timestamp)
        return cls.instance(result)

    @classmethod
    def utcnow(cls) -> Self:
        """Create a DateTime representing current UTC time.

        Returns
            DateTime instance
        """
        result = _pendulum.DateTime.utcnow()
        return cls.instance(result)

    @classmethod
    def now(cls, tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None) -> Self:
        """Get a DateTime instance for the current date and time.
        """
        if tz is None or tz == 'local':
            d = _datetime.datetime.now(LCL)
        elif tz is UTC or tz == 'UTC':
            d = _datetime.datetime.now(UTC)
        else:
            d = _datetime.datetime.now(UTC)
            tz = _pendulum._safe_timezone(tz)
            d = d.astimezone(tz)
        return cls(d.year, d.month, d.day, d.hour, d.minute, d.second,
                   d.microsecond, tzinfo=d.tzinfo, fold=d.fold)

    @classmethod
    def today(cls, tz: str | _zoneinfo.ZoneInfo | None = None) -> Self:
        """Create a DateTime object representing today at the start of day.

        Unlike pendulum.today() which returns current time, this method
        returns a DateTime object at 00:00:00 of the current day.

        Parameters
            tz: Optional timezone (defaults to local timezone)

        Returns
            DateTime instance representing start of current day
        """
        return DateTime.now(tz).start_of('day')

    def date(self) -> Date:
        return Date(self.year, self.month, self.day)

    @classmethod
    def combine(
        cls,
        date: _datetime.date,
        time: _datetime.time,
        tzinfo: _zoneinfo.ZoneInfo | None = None,
    ) -> Self:
        """Combine date and time (*behaves differently from Pendulum `combine`*).
        """
        _tzinfo = tzinfo or time.tzinfo
        return DateTime.instance(_datetime.datetime.combine(date, time, tzinfo=_tzinfo))

    def rfc3339(self) -> str:
        """Return RFC 3339 formatted string (same as isoformat()).
        """
        return self.isoformat()

    def time(self) -> Time:
        """Extract time component from datetime (preserving timezone).
        """
        return Time.instance(self)

    @classmethod
    def parse(
        cls, s: str | int | None,
        entity: Entity = NYSE,
        raise_err: bool = False
        ) -> Self | None:
        """Convert a string or timestamp to a DateTime with extended format support.

        Unlike pendulum's parse, this method supports:
        - Unix timestamps (int/float, handles milliseconds automatically)
        - Special codes: T (today), Y (yesterday), P (previous business day)
        - Business day offsets: T-3b, P+2b (add/subtract business days)
        - Multiple date-time formats beyond ISO 8601
        - Combined date and time strings with various separators

        Parameters
            s: String or timestamp to parse
            entity: Calendar entity for business day calculations (default NYSE)
            raise_err: If True, raises ValueError on parse failure instead of returning None

        Returns
            DateTime instance or None if parsing fails and raise_err is False

        Examples
            Unix timestamps:
            DateTime.parse(1609459200) → DateTime(2021, 1, 1, 0, 0, 0, tzinfo=LCL)
            DateTime.parse(1609459200000) → DateTime(2021, 1, 1, 0, 0, 0, tzinfo=LCL)

            ISO 8601 format:
            DateTime.parse('2020-01-15T14:30:00') → DateTime(2020, 1, 15, 14, 30, 0)

            Date and time separated:
            DateTime.parse('2020-01-15 14:30:00') → DateTime(2020, 1, 15, 14, 30, 0, tzinfo=LCL)
            DateTime.parse('01/15/2020:14:30:00') → DateTime(2020, 1, 15, 14, 30, 0, tzinfo=LCL)

            Date only (time defaults to 00:00:00):
            DateTime.parse('2020-01-15') → DateTime(2020, 1, 15, 0, 0, 0)
            DateTime.parse('01/15/2020') → DateTime(2020, 1, 15, 0, 0, 0)

            Time only (uses today's date):
            DateTime.parse('14:30:00') → DateTime(today's year, month, day, 14, 30, 0, tzinfo=LCL)

            Special codes:
            DateTime.parse('T') → today at 00:00:00
            DateTime.parse('Y') → yesterday at 00:00:00
            DateTime.parse('P') → previous business day at 00:00:00
        """
        if not s:
            if raise_err:
                raise ValueError('Empty value')
            return

        if not isinstance(s, str | int | float):
            raise TypeError(f'Invalid type for datetime parse: {s.__class__}')

        if isinstance(s, int | float):
            if len(str(int(s))) == 13:
                s /= 1000  # Convert from milliseconds to seconds
            iso = _datetime.datetime.fromtimestamp(s).isoformat()
            return cls.parse(iso).replace(tzinfo=LCL)

        with contextlib.suppress(ValueError, TypeError):
            return cls.instance(_dateutil.parser.parse(s))

        for delim in (' ', ':'):
            bits = s.split(delim, 1)
            if len(bits) == 2:
                d = Date.parse(bits[0])
                t = Time.parse(bits[1])
                if d is not None and t is not None:
                    return DateTime.combine(d, t, LCL)

        d = Date.parse(s, entity=entity)
        if d is not None:
            return cls(d.year, d.month, d.day, 0, 0, 0)

        current = Date.today()
        t = Time.parse(s)
        if t is not None:
            return cls.combine(current, t, LCL)

        if raise_err:
            raise ValueError('Invalid date-time format: %s', s)

    @classmethod
    def instance(
        cls,
        obj: _datetime.date
        | _datetime.time
        | pd.Timestamp
        | np.datetime64
        | Self
        | None,
        tz: str | _zoneinfo.ZoneInfo | _datetime.tzinfo | None = None,
        raise_err: bool = False,
    ) -> Self | None:
        """Create a DateTime instance from various datetime-like objects.

        Provides unified interface for converting different date/time types
        including pandas and numpy datetime objects into DateTime instances.

        Unlike pendulum, this method:
        - Handles pandas Timestamp and numpy datetime64 objects
        - Adds timezone (UTC by default) when none is specified
        - Has special handling for Time objects (combines with current date)

        Parameters
            obj: Date, datetime, time, or compatible object to convert
            tz: Optional timezone to apply (if None, uses obj's timezone or UTC)
            raise_err: If True, raises ValueError for None/NA values instead of returning None

        Returns
            DateTime instance or None if obj is None/NA and raise_err is False
        """
        if pd.isna(obj):
            if raise_err:
                raise ValueError('Empty value')
            return

        if type(obj) is cls and not tz:
            return obj

        if isinstance(obj, pd.Timestamp):
            obj = obj.to_pydatetime()
            tz = tz or obj.tzinfo or UTC
            if tz is _datetime.timezone.utc:
                tz = UTC
            elif hasattr(tz, 'zone'):
                tz = Timezone(tz.zone)
            elif isinstance(tz, str):
                tz = Timezone(tz)
            return cls(obj.year, obj.month, obj.day, obj.hour, obj.minute,
                       obj.second, obj.microsecond, tzinfo=tz)
        
        if isinstance(obj, np.datetime64):
            obj = np.datetime64(obj, 'us').astype(_datetime.datetime)
            tz = tz or UTC
            return cls(obj.year, obj.month, obj.day, obj.hour, obj.minute,
                       obj.second, obj.microsecond, tzinfo=tz)

        if type(obj) is Date:
            return cls(obj.year, obj.month, obj.day, tzinfo=tz or UTC)
        
        if isinstance(obj, _datetime.date) and not isinstance(obj, _datetime.datetime):
            return cls(obj.year, obj.month, obj.day, tzinfo=tz or UTC)

        tz = tz or obj.tzinfo or UTC

        if type(obj) is Time:
            return cls.combine(Date.today(), obj, tzinfo=tz)
        
        if isinstance(obj, _datetime.time):
            return cls.combine(Date.today(), obj, tzinfo=tz)

        return cls(obj.year, obj.month, obj.day, obj.hour, obj.minute,
                   obj.second, obj.microsecond, tzinfo=tz)


class Interval(_pendulum.Interval):
    """Interval class extending pendulum.Interval with business day awareness.

    This class represents the difference between two dates or datetimes with
    additional support for business day calculations, entity awareness, and
    financial period calculations.

    Unlike pendulum.Interval:
    - Has business day mode that only counts business days
    - Preserves entity association (e.g., NYSE)
    - Additional financial methods like yearfrac()
    - Support for range operations that respect business days
    """

    _business: bool = False
    _entity: type[NYSE] = NYSE

    @expect_date_or_datetime
    @normalize_date_datetime_pairs
    def __new__(cls, begdate: Date | DateTime, enddate: Date | DateTime) -> Self:
        assert begdate and enddate, 'Interval dates cannot be None'
        instance = super().__new__(cls, begdate, enddate, False)
        return instance

    @expect_date_or_datetime
    @normalize_date_datetime_pairs
    def __init__(self, begdate: Date | DateTime, enddate: Date | DateTime) -> None:
        super().__init__(begdate, enddate, False)
        self._sign = 1 if begdate <= enddate else -1
        if begdate <= enddate:
            self._start = begdate
            self._end = enddate
        else:
            self._start = enddate
            self._end = begdate

    @staticmethod
    def _get_quarter_start(date: Date | DateTime) -> Date | DateTime:
        """Get the start date of the quarter containing the given date.
        """
        quarter_month = ((date.month - 1) // 3) * 3 + 1
        return date.replace(month=quarter_month, day=1)

    @staticmethod
    def _get_quarter_end(date: Date | DateTime) -> Date | DateTime:
        """Get the end date of the quarter containing the given date.
        """
        quarter_month = ((date.month - 1) // 3) * 3 + 3
        return date.replace(month=quarter_month).end_of('month')

    def _get_unit_handlers(self, unit: str) -> dict:
        """Get handlers for the specified time unit.

        Returns a dict with:
            get_start: Function to get start of period containing date
            get_end: Function to get end of period containing date
            advance: Function to advance to next period start
        """
        if unit == 'quarter':
            return {
                'get_start': self._get_quarter_start,
                'get_end': self._get_quarter_end,
                'advance': lambda date: self._get_quarter_start(date.add(months=3)),
            }

        if unit == 'decade':
            return {
                'get_start': lambda date: date.start_of('decade'),
                'get_end': lambda date: date.end_of('decade'),
                'advance': lambda date: date.add(years=10).start_of('decade'),
            }

        if unit == 'century':
            return {
                'get_start': lambda date: date.start_of('century'),
                'get_end': lambda date: date.end_of('century'),
                'advance': lambda date: date.add(years=100).start_of('century'),
            }

        return {
            'get_start': lambda date: date.start_of(unit),
            'get_end': lambda date: date.end_of(unit),
            'advance': lambda date: date.add(**{f'{unit}s': 1}).start_of(unit),
        }

    def business(self) -> Self:
        self._business = True
        self._start.business()
        self._end.business()
        return self

    @property
    def b(self) -> Self:
        return self.business()

    def entity(self, e: type[NYSE] = NYSE) -> Self:
        self._entity = e
        if self._start:
            self._end._entity = e
        if self._end:
            self._end._entity = e
        return self

    def is_business_day_range(self) -> list[bool]:
        """Generate boolean values indicating whether each day in the range is a business day.
        """
        self._business = False
        for thedate in self.range('days'):
            yield thedate.is_business_day()

    @reset_business
    def range(self, unit: str = 'days', amount: int = 1) -> Iterator[DateTime | Date]:
        """Generate dates/datetimes over the interval.

        Parameters
            unit: Time unit ('days', 'weeks', 'months', 'years')
            amount: Step size (e.g., every N units)

        In business mode (for 'days' only), skips non-business days.
        """
        _business = self._business
        parent_range = _pendulum.Interval.range

        def _range_generator():
            if unit != 'days':
                yield from (type(d).instance(d) for d in parent_range(self, unit, amount))
                return

            if self._sign == 1:
                op = operator.le
                this = self._start
                thru = self._end
            else:
                op = operator.ge
                this = self._end
                thru = self._start

            while op(this, thru):
                if _business:
                    if this.is_business_day():
                        yield this
                else:
                    yield this
                this = this.add(days=self._sign * amount)

        return _range_generator()

    @property
    @reset_business
    def days(self) -> int:
        """Get number of days in the interval (respects business mode and sign).
        """
        if not self._business:
            return self._sign * (self._end - self._start).days
        return self._sign * len(tuple(self.range('days'))) - self._sign

    @property
    def months(self) -> float:
        """Get number of months in the interval including fractional parts.

        Overrides pendulum's months property to return a float instead of an integer.
        Calculates fractional months based on actual day counts within partial months.
        """
        year_diff = self._end.year - self._start.year
        month_diff = self._end.month - self._start.month
        total_months = year_diff * 12 + month_diff

        if self._end.day >= self._start.day:
            day_diff = self._end.day - self._start.day
            days_in_month = calendar.monthrange(self._start.year, self._start.month)[1]
            fraction = day_diff / days_in_month
        else:
            total_months -= 1
            days_in_start_month = calendar.monthrange(self._start.year, self._start.month)[1]
            day_diff = (days_in_start_month - self._start.day) + self._end.day
            fraction = day_diff / days_in_start_month

        return self._sign * (total_months + fraction)

    @property
    def quarters(self) -> float:
        """Get approximate number of quarters in the interval.

        Note: This is an approximation using day count / 365 * 4.
        """
        return self._sign * 4 * self.days / 365.0

    @property
    def years(self) -> int:
        """Get number of complete years in the interval (always floors).
        """
        year_diff = self._end.year - self._start.year
        if self._end.month < self._start.month or \
           (self._end.month == self._start.month and self._end.day < self._start.day):
            year_diff -= 1
        return self._sign * year_diff

    def yearfrac(self, basis: int = 0) -> float:
        """Calculate the fraction of years between two dates (Excel-compatible).

        This method provides precise calculation using various day count conventions
        used in finance. Results are tested against Excel for compatibility.

        Parameters
            basis: Day count convention to use:
                0 = US (NASD) 30/360 (default)
                1 = Actual/actual
                2 = Actual/360
                3 = Actual/365
                4 = European 30/360

        Note: Excel has a known leap year bug for year 1900 which is intentionally
        replicated for compatibility (1900 is treated as a leap year even though it wasn't).
        """

        def average_year_length(date1, date2):
            """Algorithm for average year length"""
            days = (Date(date2.year + 1, 1, 1) - Date(date1.year, 1, 1)).days
            years = (date2.year - date1.year) + 1
            return days / years

        def feb29_between(date1, date2):
            """Requires date2.year = (date1.year + 1) or date2.year = date1.year.

            Returns True if "Feb 29" is between the two dates (date1 may be Feb29).
            Two possibilities: date1.year is a leap year, and date1 <= Feb 29 y1,
            or date2.year is a leap year, and date2 > Feb 29 y2.
            """
            mar1_date1_year = Date(date1.year, 3, 1)
            if calendar.isleap(date1.year) and (date1 < mar1_date1_year) and (date2 >= mar1_date1_year):
                return True
            mar1_date2_year = Date(date2.year, 3, 1)
            return bool(calendar.isleap(date2.year) and date2 >= mar1_date2_year and date1 < mar1_date2_year)

        def appears_lte_one_year(date1, date2):
            """Returns True if date1 and date2 "appear" to be 1 year or less apart.

            This compares the values of year, month, and day directly to each other.
            Requires date1 <= date2; returns boolean. Used by basis 1.
            """
            if date1.year == date2.year:
                return True
            return bool(date1.year + 1 == date2.year and (date1.month > date2.month or date1.month == date2.month and date1.day >= date2.day))

        def basis0(date1, date2):
            # change day-of-month for purposes of calculation.
            date1day, date1month, date1year = date1.day, date1.month, date1.year
            date2day, date2month, date2year = date2.day, date2.month, date2.year
            if date1day == 31 and date2day == 31:
                date1day = 30
                date2day = 30
            elif date1day == 31:
                date1day = 30
            elif date1day == 30 and date2day == 31:
                date2day = 30
            # Note: If date2day==31, it STAYS 31 if date1day < 30.
            # Special fixes for February:
            elif date1month == 2 and date2month == 2 and date1 == date1.end_of('month') \
                and date2 == date2.end_of('month'):
                date1day = 30  # Set the day values to be equal
                date2day = 30
            elif date1month == 2 and date1 == date1.end_of('month'):
                date1day = 30  # "Illegal" Feb 30 date.
            daydiff360 = (date2day + date2month * 30 + date2year * 360) \
                - (date1day + date1month * 30 + date1year * 360)
            return daydiff360 / 360

        def basis1(date1, date2):
            if appears_lte_one_year(date1, date2):
                if date1.year == date2.year and calendar.isleap(date1.year):
                    year_length = 366.0
                elif feb29_between(date1, date2) or (date2.month == 2 and date2.day == 29):
                    year_length = 366.0
                else:
                    year_length = 365.0
                return (date2 - date1).days / year_length
            return (date2 - date1).days / average_year_length(date1, date2)

        def basis2(date1, date2):
            return (date2 - date1).days / 360.0

        def basis3(date1, date2):
            return (date2 - date1).days / 365.0

        def basis4(date1, date2):
            # change day-of-month for purposes of calculation.
            date1day, date1month, date1year = date1.day, date1.month, date1.year
            date2day, date2month, date2year = date2.day, date2.month, date2.year
            if date1day == 31:
                date1day = 30
            if date2day == 31:
                date2day = 30
            # Remarkably, do NOT change Feb. 28 or 29 at ALL.
            daydiff360 = (date2day + date2month * 30 + date2year * 360) - \
                (date1day + date1month * 30 + date1year * 360)
            return daydiff360 / 360

        if self._start == self._end:
            return 0.0
        if basis == 0:
            return basis0(self._start, self._end) * self._sign
        if basis == 1:
            return basis1(self._start, self._end) * self._sign
        if basis == 2:
            return basis2(self._start, self._end) * self._sign
        if basis == 3:
            return basis3(self._start, self._end) * self._sign
        if basis == 4:
            return basis4(self._start, self._end) * self._sign

        raise ValueError('Basis range [0, 4]. Unknown basis {basis}.')

    @reset_business
    def start_of(self, unit: str = 'month') -> list[Date | DateTime]:
        """Return the start of each unit within the interval.

        Parameters
            unit: Time unit ('month', 'week', 'year', 'quarter')

        Returns
            List of Date or DateTime objects representing start of each unit

        In business mode, each start date is adjusted to the next business day
        if it falls on a non-business day.
        """
        handlers = self._get_unit_handlers(unit)
        result = []

        current = handlers['get_start'](self._start)

        if self._business:
            current._entity = self._entity

        while current <= self._end:
            if self._business:
                current = current._business_or_next()
            result.append(current)
            current = handlers['advance'](current)

        return result

    @reset_business
    def end_of(self, unit: str = 'month') -> list[Date | DateTime]:
        """Return the end of each unit within the interval.

        Parameters
            unit: Time unit ('month', 'week', 'year', 'quarter')

        Returns
            List of Date or DateTime objects representing end of each unit

        In business mode, each end date is adjusted to the previous business day
        if it falls on a non-business day.
        """
        handlers = self._get_unit_handlers(unit)
        result = []

        current = handlers['get_start'](self._start)

        if self._business:
            current._entity = self._entity

        while current <= self._end:
            end_date = handlers['get_end'](current)

            if self._business:
                end_date = end_date._business_or_previous()
            result.append(end_date)

            current = handlers['advance'](current)

        return result
