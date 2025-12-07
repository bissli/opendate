from __future__ import annotations

import calendar
import operator
import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pendulum as _pendulum

import date as _date
from date.decorators import expect_date_or_datetime
from date.decorators import normalize_date_datetime_pairs, reset_business

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from date.calendars import Calendar
    from date.date_ import Date
    from date.datetime_ import DateTime


class Interval(_pendulum.Interval):
    """Interval class extending pendulum.Interval with business day awareness.

    This class represents the difference between two dates or datetimes with
    additional support for business day calculations, entity awareness, and
    financial period calculations.

    Unlike pendulum.Interval:
    - Has business day mode that only counts business days
    - Preserves calendar association (e.g., NYSE, LSE)
    - Additional financial methods like yearfrac()
    - Support for range operations that respect business days
    """

    _business: bool = False
    _calendar: Calendar | None = None

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

    def calendar(self, cal: str | 'Calendar | None' = None) -> Self:
        """Set the calendar for business day calculations.

        Parameters
            cal: Calendar name (str), Calendar instance, or None for default
        """
        from date.calendars import get_calendar, get_default_calendar

        if cal is None:
            cal = get_default_calendar()
        if isinstance(cal, str):
            cal = get_calendar(cal)
        self._calendar = cal
        if self._start:
            self._start._calendar = cal
        if self._end:
            self._end._calendar = cal
        return self

    def is_business_day_range(self) -> Iterator[bool]:
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
            days = (_date.Date(date2.year + 1, 1, 1) - _date.Date(date1.year, 1, 1)).days
            years = (date2.year - date1.year) + 1
            return days / years

        def feb29_between(date1, date2):
            """Requires date2.year = (date1.year + 1) or date2.year = date1.year.

            Returns True if "Feb 29" is between the two dates (date1 may be Feb29).
            Two possibilities: date1.year is a leap year, and date1 <= Feb 29 y1,
            or date2.year is a leap year, and date2 > Feb 29 y2.
            """
            mar1_date1_year = _date.Date(date1.year, 3, 1)
            if calendar.isleap(date1.year) and (date1 < mar1_date1_year) and (date2 >= mar1_date1_year):
                return True
            mar1_date2_year = _date.Date(date2.year, 3, 1)
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

        raise ValueError(f'Basis range [0, 4]. Unknown basis {basis}.')

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
            current._calendar = self._calendar

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
            current._calendar = self._calendar

        while current <= self._end:
            end_date = handlers['get_end'](current)

            if self._business:
                end_date = end_date._business_or_previous()
            result.append(end_date)

            current = handlers['advance'](current)

        return result
