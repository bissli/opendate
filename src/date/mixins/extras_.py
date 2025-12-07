from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from date.constants import WEEKDAY_SHORTNAME, WeekDay
from date.decorators import store_calendar

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    pass


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

    @store_calendar
    def nearest_start_of_month(self) -> Self:
        """Get the nearest start of month.

        If day <= 15, returns start of current month.
        If day > 15, returns start of next month.
        In business mode, snaps to next business day if needed.
        """
        _business = self._business
        self._business = False
        if self.day > 15:
            d = self.end_of('month').add(days=1)  # First of next month
        else:
            d = self.start_of('month')  # First of current month
        if _business:
            d = d._business_or_next()
        return d

    @store_calendar
    def nearest_end_of_month(self) -> Self:
        """Get the nearest end of month.

        If day <= 15, returns end of previous month.
        If day > 15, returns end of current month.
        In business mode, snaps to previous business day if needed.
        """
        _business = self._business
        self._business = False
        if self.day <= 15:
            d = self.start_of('month').subtract(days=1)  # End of previous month
        else:
            d = self.end_of('month')  # End of current month
        if _business:
            d = d._business_or_previous()
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
