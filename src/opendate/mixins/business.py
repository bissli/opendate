from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from opendate.calendars import get_calendar, get_default_calendar
from opendate.constants import MAX_YEAR, MIN_YEAR, WeekDay
from opendate.decorators import expect_date, store_calendar

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from opendate.calendars import Calendar
    from opendate.datetime_ import DateTime


class DateBusinessMixin:
    """Mixin class providing business day functionality.

    This mixin adds business day awareness to Date and DateTime classes,
    allowing date operations to account for weekends and holidays according
    to a specified calendar.

    Features not available in pendulum:
    - Business day mode toggle
    - Calendar-specific rules (exchanges, custom)
    - Business-aware date arithmetic
    """

    _calendar: Calendar | None = None
    _business: bool = False

    def business(self) -> Self:
        """Switch to business day mode for date calculations.

        In business day mode, date arithmetic only counts business days
        as defined by the associated calendar (default NYSE).

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

    def calendar(self, cal: str | Calendar | None = None) -> Self:
        """Set the calendar for business day calculations.

        Parameters
            cal: Calendar name (str), Calendar instance, or None for default

        Returns
            Self instance for method chaining

        Examples
            d.calendar('NYSE').b.add(days=1)
            d.calendar('LSE').b.subtract(days=5)
            d.calendar(my_custom_calendar).is_business_day()
        """
        if cal is None:
            cal = get_default_calendar()
        if isinstance(cal, str):
            self._calendar = get_calendar(cal)
        else:
            self._calendar = cal
        return self

    @property
    def _active_calendar(self) -> Calendar:
        """Get the active calendar (uses module default if not set).
        """
        if self._calendar is None:
            return get_calendar(get_default_calendar())
        return self._calendar

    def _is_out_of_range(self) -> bool:
        """Check if date is outside valid calendar range (1900-2100)."""
        return self.year < MIN_YEAR or self.year > MAX_YEAR

    @store_calendar
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
            if self._is_out_of_range() and self.year > MAX_YEAR:
                return self
            target = self._business_or_next() if self._is_out_of_range() else self
            result = target._add_business_days(days)
            return result if result is not None else self
        return super().add(years, months, weeks, days, **kwargs)

    @store_calendar
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
            target = self._business_or_previous() if self._is_out_of_range() else self
            result = target._add_business_days(-days)
            return result if result is not None else self
        kwargs = {k: -1*v for k, v in kwargs.items()}
        return super().add(-years, -months, -weeks, -days, **kwargs)

    @store_calendar
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

    @store_calendar
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

    @store_calendar
    def start_of(self, unit: str) -> Self:
        """Returns a copy of the instance with the time reset
        """
        _business = self._business
        self._business = False
        self = super().start_of(unit)
        if _business:
            self = self._business_or_next()
        return self

    @store_calendar
    def end_of(self, unit: str) -> Self:
        """Returns a copy of the instance with the time reset
        """
        _business = self._business
        self._business = False
        self = super().end_of(unit)
        if _business:
            self = self._business_or_previous()
        return self

    @store_calendar
    def previous(self, day_of_week: WeekDay | None = None) -> Self:
        """Modify to the previous occurrence of a given day of the week.

        In business mode, snaps BACKWARD to maintain 'previous' semantics.
        """
        _business = self._business
        self._business = False
        self = super().previous(day_of_week)
        if _business:
            self = self._business_or_previous()
        return self

    @store_calendar
    def next(self, day_of_week: WeekDay | None = None) -> Self:
        """Modify to the next occurrence of a given day of the week.

        In business mode, snaps FORWARD to maintain 'next' semantics.
        """
        _business = self._business
        self._business = False
        self = super().next(day_of_week)
        if _business:
            self = self._business_or_next()
        return self

    @expect_date
    def is_business_day(self) -> bool:
        """Check if the date is a business day according to the calendar.

        Returns False for dates outside valid calendar range (1900-2100).
        """
        if self._is_out_of_range():
            return False
        cal = self._active_calendar._get_calendar(self)
        if cal is None:
            return False
        return cal.is_business_day(self.toordinal())

    # Alias for backwards compatibility
    business_open = is_business_day

    @expect_date
    def business_hours(self) -> tuple[DateTime, DateTime]:
        """Get market open and close times for this date.

        Returns (None, None) if not a business day.
        """
        return self._active_calendar.business_hours(self, self)\
            .get(self, (None, None))

    def _add_business_days(self, days: int) -> Self | None:
        """Add business days using Rust calendar.

        Returns self unchanged for dates outside valid range (1900-2100).
        """
        if self._is_out_of_range():
            return self
        cal = self._active_calendar._get_calendar(self)
        if cal is None:
            return None
        start_ord = self.toordinal()
        forward = days > 0
        offset = 1 if forward else -1
        first_bd = (cal.next_business_day if forward else cal.prev_business_day)(start_ord + offset)
        if first_bd is None:
            return None
        result_ord = cal.add_business_days(first_bd, (abs(days) - 1) * offset)
        if result_ord is None:
            return None
        return super().add(days=result_ord - start_ord)

    @store_calendar
    def _snap_to_business_day(self, forward: bool = True) -> Self:
        """Snap to nearest business day if not already on one.

        For dates outside valid range (1900-2100):
        - If forward=False and year > 2100: snap to last business day of 2100
        - If forward=True and year < 1900: snap to first business day of 1900
        - Otherwise return self unchanged
        """
        self._business = False
        if self._is_out_of_range():
            from opendate.date_ import Date
            if self.year > MAX_YEAR and not forward:
                boundary = Date(MAX_YEAR, 12, 31)
                boundary._calendar = self._calendar
                return boundary._snap_to_business_day(forward=False)
            elif self.year < MIN_YEAR and forward:
                boundary = Date(MIN_YEAR, 1, 1)
                boundary._calendar = self._calendar
                return boundary._snap_to_business_day(forward=True)
            return self
        cal = self._active_calendar._get_calendar(self)
        if cal is None:
            return self
        if self.is_business_day():
            return self
        ordinal = self.toordinal()
        target = cal.next_business_day(ordinal) if forward else cal.prev_business_day(ordinal)
        if target is None:
            return self
        return super().add(days=target - ordinal)

    def _business_or_next(self) -> Self:
        return self._snap_to_business_day(forward=True)

    def _business_or_previous(self) -> Self:
        return self._snap_to_business_day(forward=False)
