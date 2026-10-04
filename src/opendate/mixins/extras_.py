from __future__ import annotations

import sys

from opendate.constants import WEEKDAY_SHORTNAME, WeekDay
from opendate.decorators import store_calendar

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class DateExtrasMixin:
    """Date helpers pendulum lacks, kept for legacy callers.

    New code should prefer the built-in methods where one exists.
    """

    @store_calendar
    def nearest_start_of_month(self) -> Self:
        """First of the month nearest this date.

        Returns
        -------
        Self
            The first of this month on day 15 or earlier, else the first
            of next month. In business mode, the business day on or after
            it.
        """
        _business = self._business
        self._business = False
        if self.day > 15:
            d = self.end_of('month').add(days=1)
        else:
            d = self.start_of('month')
        if _business:
            d = d._business_or_next()
        return d

    @store_calendar
    def nearest_end_of_month(self) -> Self:
        """Last day of the month nearest this date.

        Returns
        -------
        Self
            The last day of last month on day 15 or earlier, else the last
            day of this month. In business mode, the business day on or
            before it.
        """
        _business = self._business
        self._business = False
        if self.day <= 15:
            d = self.start_of('month').subtract(days=1)
        else:
            d = self.end_of('month')
        if _business:
            d = d._business_or_previous()
        return d

    def next_relative_date_of_week_by_day(self, day: str = 'MO') -> Self:
        """This date where it falls on day, else the next date that does.

        Parameters
        ----------
        day : str, default 'MO'
            Weekday code, 'MO' through 'SU', upper case.

        Returns
        -------
        Self

        Raises
        ------
        KeyError
            day is no such code, 'mo' included.
        """
        weekday = WEEKDAY_SHORTNAME[day]
        if self.weekday() == weekday:
            return self
        return self.next(weekday)

    def weekday_or_previous_friday(self) -> Self:
        """This date on a weekday, else the Friday before it.
        """
        if self.weekday() in {WeekDay.SATURDAY, WeekDay.SUNDAY}:
            return self.previous(WeekDay.FRIDAY)
        return self

    @classmethod
    def third_wednesday(cls, year: int, month: int) -> Self:
        """Third Wednesday of a month.

        .. deprecated::
            Use Date(year, month, 1).nth_of('month', 3, WeekDay.WEDNESDAY).

        Parameters
        ----------
        year : int
            Calendar year.
        month : int
            1-12.

        Returns
        -------
        Self
        """
        return cls(year, month, 1).nth_of('month', 3, WeekDay.WEDNESDAY)
