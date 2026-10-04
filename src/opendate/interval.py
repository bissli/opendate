from __future__ import annotations

import calendar
import operator
import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING

import opendate as _date
import pendulum as _pendulum
from opendate.calendars import get_calendar, get_default_calendar
from opendate.decorators import expect_date_or_datetime
from opendate.decorators import normalize_date_datetime_pairs, reset_business

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from opendate.calendars import Calendar
    from opendate.date_ import Date
    from opendate.datetime_ import DateTime


class Interval(_pendulum.Interval):
    """Span between two dates or datetimes, with business-day counting.

    Parameters
    ----------
    begdate : Date | DateTime
        First endpoint. A datetime.date, datetime.datetime,
        pandas.Timestamp or numpy.datetime64 becomes a Date or DateTime,
        and a Date paired with a DateTime becomes a DateTime.
    enddate : Date | DateTime
        Second endpoint. An enddate before begdate makes the interval
        reversed, and its counts negative.

    Raises
    ------
    AssertionError
        Either endpoint is None or NaT.
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
        self._direction = 1 if begdate <= enddate else -1
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
        """Period functions for unit, keyed get_start, get_end and advance.

        Parameters
        ----------
        unit : str
            Pendulum unit name, or 'quarter', 'decade' or 'century'.

        Returns
        -------
        dict
            get_start and get_end map a date to the start or end of its
            period. advance maps a period start to the next period start.
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
        """Business-day mode on this interval and both endpoints, in place.

        Returns
        -------
        Self
            This interval. range, days, start_of and end_of turn the mode
            off when they return.
        """
        self._business = True
        self._start.business()
        self._end.business()
        return self

    @property
    def b(self) -> Self:
        """Shorthand for business().
        """
        return self.business()

    def calendar(self, cal: str | Calendar | None = None) -> Self:
        """Set the business-day calendar on the interval and both endpoints.

        Parameters
        ----------
        cal : str | Calendar | None, default None
            Calendar name, Calendar instance, or None for the default
            calendar.

        Returns
        -------
        Self
            This interval, changed in place.
        """
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
        """Business-day flag for each calendar day from begdate to enddate.
        """
        self._business = False
        for thedate in self.range('days'):
            yield thedate.is_business_day()

    @reset_business
    def range(self, unit: str = 'days', amount: int = 1) -> Iterator[DateTime | Date]:
        """Dates or datetimes stepping from begdate to enddate, inclusive.

        Parameters
        ----------
        unit : str, default 'days'
            Pendulum unit name: 'days', 'weeks', 'months' or 'years'.
        amount : int, default 1
            Step size, in units.

        Returns
        -------
        Iterator[DateTime | Date]
            A reversed interval steps backward. For 'days' only, business
            mode skips non-business days.
        """
        _business = self._business
        parent_range = _pendulum.Interval.range

        def _range_generator() -> Iterator[DateTime | Date]:
            if self._direction == 1:
                op = operator.le
                this = self._start
                thru = self._end
            else:
                op = operator.ge
                this = self._end
                thru = self._start

            if unit != 'days':
                yield from (
                    type(d).instance(d)
                    for d in parent_range(_pendulum.Interval(this, thru), unit, amount))
                return

            while op(this, thru):
                if _business:
                    if this.is_business_day():
                        yield this
                else:
                    yield this
                this = this.add(days=self._direction * amount)

        return _range_generator()

    @property
    @reset_business
    def days(self) -> int:
        """Signed count of days from begdate to enddate.

        In business mode, the count is of business days from the earlier
        endpoint up to and excluding the later one.
        """
        if not self._business:
            # Use toordinal to avoid recursion with wrapped __sub__
            return self._direction * (self._end.toordinal() - self._start.toordinal())
        brange = tuple(self.range('days'))
        return self._direction * (len(brange) - int(self._end.is_business_day()))

    @property
    def months(self) -> float:
        """Signed month count, with the partial month as a fraction.

        Notes
        -----
        - whole = 12 * (end.year - start.year) + (end.month - start.month)
        - end.day >= start.day: whole + (end.day - start.day) / L
        - end.day < start.day: whole - 1 + (L - start.day + end.day) / L
        - start is the earlier endpoint and L the length of its month. A
          reversed interval negates the result.
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
            days_in_start_month = calendar.monthrange(
                self._start.year, self._start.month)[1]
            day_diff = (days_in_start_month - self._start.day) + self._end.day
            fraction = day_diff / days_in_start_month

        return self._direction * (total_months + fraction)

    @property
    def quarters(self) -> float:
        """Approximate quarter count, as 4 * days / 365.
        """
        return 4 * self.days / 365.0

    @property
    def years(self) -> int:
        """Signed count of whole years, truncated toward zero.
        """
        year_diff = self._end.year - self._start.year
        if self._end.month < self._start.month or \
           (self._end.month == self._start.month and self._end.day < self._start.day):
            year_diff -= 1
        return self._direction * year_diff

    def yearfrac(self, basis: int = 0) -> float:
        """Year fraction between the endpoints under a day-count convention.

        Every basis equals its QuantLib day counter bitwise on an ascending
        interval.

        Parameters
        ----------
        basis : int, default 0
            Day-count convention, with its QuantLib twin:

            - 0: 30/360 US (SIA), ``Thirty360(USA)``
            - 1: ACT/ACT ISDA, ``ActualActual(ISDA)``
            - 2: ACT/360, ``Actual360()``
            - 3: ACT/365 Fixed, ``Actual365Fixed()``
            - 4: 30E/360 (Eurobond), ``Thirty360(European)``
            - 5: ACT/365.25, ``Actual36525()``
            - 6: 30/360 Bond Basis (ISDA 2006 4.16(f)),
              ``Thirty360(BondBasis)``
            - 7: 30E/360 ISDA (German), ``Thirty360(German)`` with no
              termination date, so an end on the last day of February
              always counts as the 30th
            - 8: ACT/365 No Leap, ``Actual365Fixed(NoLeap)``

        Returns
        -------
        float
            The year fraction. A reversed interval returns the negated
            ascending value, where QuantLib re-runs the 30/360 day rules on
            the reversed pair.

        Raises
        ------
        ValueError
            For a basis outside 0-8.
        """

        def is_end_of_feb(date: Date | DateTime) -> bool:
            return date.month == 2 \
                and date.day == calendar.monthrange(date.year, 2)[1]

        def serial_360(date: Date | DateTime, day: int) -> int:
            """Day number on a 30/360 calendar, with day in place of date.day.
            """
            return day + date.month * 30 + date.year * 360

        def basis0(date1: Date | DateTime, date2: Date | DateTime) -> float:
            date1day, date2day = date1.day, date2.day
            if is_end_of_feb(date1):
                if is_end_of_feb(date2):
                    date2day = 30
                date1day = 30
            if date2day == 31 and date1day >= 30:
                date2day = 30
            if date1day == 31:
                date1day = 30
            return (serial_360(date2, date2day) - serial_360(date1, date1day)) / 360

        def _days_between(date1: Date | DateTime, date2: Date | DateTime) -> int:
            """Signed day count from date1 to date2, by ordinal to avoid
            recursion through the wrapped __sub__.
            """
            return date2.toordinal() - date1.toordinal()

        def basis1(date1: Date | DateTime, date2: Date | DateTime) -> float:
            year1_length = 366.0 if calendar.isleap(date1.year) else 365.0
            year2_length = 366.0 if calendar.isleap(date2.year) else 365.0
            year1_days = _days_between(date1, _date.Date(date1.year + 1, 1, 1))
            year2_days = _days_between(_date.Date(date2.year, 1, 1), date2)
            return (float(date2.year - date1.year - 1)
                    + year1_days / year1_length
                    + year2_days / year2_length)

        def basis2(date1: Date | DateTime, date2: Date | DateTime) -> float:
            return _days_between(date1, date2) / 360.0

        def basis3(date1: Date | DateTime, date2: Date | DateTime) -> float:
            return _days_between(date1, date2) / 365.0

        def basis4(date1: Date | DateTime, date2: Date | DateTime) -> float:
            date1day, date2day = date1.day, date2.day
            if date1day == 31:
                date1day = 30
            if date2day == 31:
                date2day = 30
            return (serial_360(date2, date2day) - serial_360(date1, date1day)) / 360

        def basis5(date1: Date | DateTime, date2: Date | DateTime) -> float:
            return _days_between(date1, date2) / 365.25

        def basis6(date1: Date | DateTime, date2: Date | DateTime) -> float:
            date1day, date2day = date1.day, date2.day
            if date1day == 31:
                date1day = 30
            if date2day == 31 and date1day == 30:
                date2day = 30
            return (serial_360(date2, date2day) - serial_360(date1, date1day)) / 360

        def basis7(date1: Date | DateTime, date2: Date | DateTime) -> float:
            date1day, date2day = date1.day, date2.day
            if date1day == 31 or is_end_of_feb(date1):
                date1day = 30
            if date2day == 31 or is_end_of_feb(date2):
                date2day = 30
            return (serial_360(date2, date2day) - serial_360(date1, date1day)) / 360

        def no_leap_index(date: Date | DateTime) -> int:
            """Day index on a calendar with no February 29.

            A February 29 takes February 28's index, so the difference of
            two indices leaves out every leap day between them.
            """
            month_offset = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
            index = date.year * 365 + month_offset[date.month - 1] + date.day
            if date.month == 2 and date.day == 29:
                return index - 1
            return index

        def basis8(date1: Date | DateTime, date2: Date | DateTime) -> float:
            return (no_leap_index(date2) - no_leap_index(date1)) / 365.0

        if basis not in range(9):
            raise ValueError(f'Basis range [0, 8]. Unknown basis {basis}.')
        if self._start.toordinal() == self._end.toordinal():
            return 0.0
        if basis == 0:
            return basis0(self._start, self._end) * self._direction
        if basis == 1:
            return basis1(self._start, self._end) * self._direction
        if basis == 2:
            return basis2(self._start, self._end) * self._direction
        if basis == 3:
            return basis3(self._start, self._end) * self._direction
        if basis == 4:
            return basis4(self._start, self._end) * self._direction
        if basis == 5:
            return basis5(self._start, self._end) * self._direction
        if basis == 6:
            return basis6(self._start, self._end) * self._direction
        if basis == 7:
            return basis7(self._start, self._end) * self._direction
        return basis8(self._start, self._end) * self._direction

    @reset_business
    def start_of(self, unit: str = 'month') -> list[Date | DateTime]:
        """Start of each unit period that overlaps the interval, ascending.

        Parameters
        ----------
        unit : str, default 'month'
            Pendulum unit name ('day', 'week', 'month', 'year'), or
            'quarter', 'decade' or 'century'.

        Returns
        -------
        list[Date | DateTime]
            One start per period. The first can fall before the interval
            start. In business mode, a start on a non-business day moves
            to the next business day.
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
        """End of each unit period that overlaps the interval, ascending.

        Parameters
        ----------
        unit : str, default 'month'
            Pendulum unit name ('day', 'week', 'month', 'year'), or
            'quarter', 'decade' or 'century'.

        Returns
        -------
        list[Date | DateTime]
            One end per period. The last can fall after the interval end.
            In business mode, an end on a non-business day moves to the
            previous business day.
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
