from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from opendate.calendars import get_calendar, get_default_calendar
from opendate.constants import MAX_YEAR, MIN_YEAR, WeekDay
from opendate.decorators import store_calendar

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
    """

    _calendar: Calendar | None = None
    _business: bool = False

    def business(self) -> Self:
        """Switch to business day mode for the next date calculation.

        In business day mode, date arithmetic only counts business days
        as defined by the associated calendar (default NYSE).

        Returns
        -------
        Self
            This instance, flagged in place. The next add, subtract,
            first_of, last_of, start_of, end_of, previous or next call
            clears the flag.
        """
        self._business = True
        return self

    @property
    def b(self) -> Self:
        """Same as business().
        """
        return self.business()

    def calendar(self, cal: str | Calendar | None = None) -> Self:
        """Set the calendar for business day calculations.

        Parameters
        ----------
        cal : str or Calendar, optional
            Calendar name or instance. None means get_default_calendar().

        Returns
        -------
        Self
            This instance, changed in place.

        Raises
        ------
        ValueError
            cal is a name that get_calendar does not recognize.

        Examples
        --------
        >>> d.calendar('NYSE').b.add(days=1)
        >>> d.calendar('LSE').b.subtract(days=5)
        >>> d.calendar(my_custom_calendar).is_business_day()
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
        """True when the year lies outside MIN_YEAR..MAX_YEAR.
        """
        return self.year < MIN_YEAR or self.year > MAX_YEAR

    @store_calendar
    def add(
        self,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        **kwargs) -> Self:
        """Add time periods to the current date or datetime.

        Extends pendulum's add with business day awareness.

        Parameters
        ----------
        years : int, default 0
            Ignored in business mode.
        months : int, default 0
            Ignored in business mode.
        weeks : int, default 0
            Ignored in business mode.
        days : int, default 0
            In business mode, a count of business days. There, 0 moves
            forward to a business day when off one, and a negative count
            subtracts.
        **kwargs
            Further pendulum units such as hours, applied after the
            business-day move.

        Returns
        -------
        Self
            A new instance. In business mode, a date outside
            MIN_YEAR..MAX_YEAR comes back unchanged.
        """
        _business = self._business
        self._business = False
        if _business:
            if days == 0 and not kwargs:
                return self._business_or_next()
            if days == 0 and kwargs:
                return self._business_or_next().add(**kwargs)
            if days < 0:
                negated_kwargs = {k: -v for k, v in kwargs.items()}
                return self.business().subtract(days=abs(days), **negated_kwargs)
            if self._is_out_of_range():
                return self
            result = self._add_business_days(days)
            result = result if result is not None else self
            if kwargs:
                return result.add(**kwargs)
            return result
        return super().add(years, months, weeks, days, **kwargs)

    @store_calendar
    def subtract(
        self,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        **kwargs) -> Self:
        """Subtract time periods from the current date or datetime.

        Parameters
        ----------
        years : int, default 0
            Ignored in business mode.
        months : int, default 0
            Ignored in business mode.
        weeks : int, default 0
            Ignored in business mode.
        days : int, default 0
            In business mode, a count of business days. There, 0 moves
            back to a business day when off one, and a negative count adds.
        **kwargs
            Further pendulum units such as hours, applied after the
            business-day move.

        Returns
        -------
        Self
            A new instance. In business mode, a date outside
            MIN_YEAR..MAX_YEAR comes back unchanged.
        """
        _business = self._business
        self._business = False
        if _business:
            if days == 0 and not kwargs:
                return self._business_or_previous()
            if days == 0 and kwargs:
                return self._business_or_previous().subtract(**kwargs)
            if days < 0:
                negated_kwargs = {k: -v for k, v in kwargs.items()}
                return self.business().add(days=abs(days), **negated_kwargs)
            if self._is_out_of_range():
                return self
            result = self._add_business_days(-days)
            result = result if result is not None else self
            if kwargs:
                return result.subtract(**kwargs)
            return result
        kwargs = {k: -1 * v for k, v in kwargs.items()}
        return super().add(-years, -months, -weeks, -days, **kwargs)

    @store_calendar
    def first_of(self, unit: str, day_of_week: WeekDay | None = None) -> Self:
        """First occurrence of a weekday in the current unit.

        Parameters
        ----------
        unit : str
            'month', 'quarter' or 'year'.
        day_of_week : WeekDay, optional
            None means the unit's first day.

        Returns
        -------
        Self
            In business mode, moved forward to a business day when off one.
        """
        _business = self._business
        self._business = False
        self = super().first_of(unit, day_of_week)
        if _business:
            self = self._business_or_next()
        return self

    @store_calendar
    def last_of(self, unit: str, day_of_week: WeekDay | None = None) -> Self:
        """Last occurrence of a weekday in the current unit.

        Parameters
        ----------
        unit : str
            'month', 'quarter' or 'year'.
        day_of_week : WeekDay, optional
            None means the unit's last day.

        Returns
        -------
        Self
            In business mode, moved back to a business day when off one.
        """
        _business = self._business
        self._business = False
        self = super().last_of(unit, day_of_week)
        if _business:
            self = self._business_or_previous()
        return self

    @store_calendar
    def start_of(self, unit: str) -> Self:
        """Start of the current unit.

        Parameters
        ----------
        unit : str
            A pendulum unit such as 'week', 'month' or 'year'.

        Returns
        -------
        Self
            In business mode, moved forward to a business day when off one.
        """
        _business = self._business
        self._business = False
        self = super().start_of(unit)
        if _business:
            self = self._business_or_next()
        return self

    @store_calendar
    def end_of(self, unit: str) -> Self:
        """End of the current unit.

        Parameters
        ----------
        unit : str
            A pendulum unit such as 'week', 'month' or 'year'.

        Returns
        -------
        Self
            In business mode, moved back to a business day when off one.
        """
        _business = self._business
        self._business = False
        self = super().end_of(unit)
        if _business:
            self = self._business_or_previous()
        return self

    @store_calendar
    def previous(self, day_of_week: WeekDay | None = None) -> Self:
        """Previous occurrence of a weekday, before this date.

        Parameters
        ----------
        day_of_week : WeekDay, optional
            None means this date's own weekday.

        Returns
        -------
        Self
            In business mode, moved back to a business day when off one.
        """
        _business = self._business
        self._business = False
        self = super().previous(day_of_week)
        if _business:
            self = self._business_or_previous()
        return self

    @store_calendar
    def next(self, day_of_week: WeekDay | None = None) -> Self:
        """Next occurrence of a weekday, after this date.

        Parameters
        ----------
        day_of_week : WeekDay, optional
            None means this date's own weekday.

        Returns
        -------
        Self
            In business mode, moved forward to a business day when off one.
        """
        _business = self._business
        self._business = False
        self = super().next(day_of_week)
        if _business:
            self = self._business_or_next()
        return self

    def is_business_day(self) -> bool:
        """Check if the date is a business day according to the calendar.

        Returns
        -------
        bool
            False outside MIN_YEAR..MAX_YEAR. A DateTime is judged by its
            wall-clock date, without conversion to the calendar's tz.
        """
        # Deferred: opendate imports this mixin, a circular import.
        import opendate
        obj = self
        if isinstance(self, opendate.DateTime):
            obj = opendate.Date(self.year, self.month, self.day)
            obj._calendar = self._calendar
        if obj._is_out_of_range():
            return False
        cal = obj._active_calendar._get_calendar(obj)
        if cal is None:
            return False
        return cal.is_business_day(obj.toordinal())

    business_open = is_business_day

    def business_hours(self) -> tuple[DateTime | None, DateTime | None]:
        """Get market open and close times for this date.

        Returns
        -------
        tuple of DateTime
            (open, close) in the calendar's tz, or (None, None) when this
            date is not a business day.
        """
        # Deferred: opendate imports this mixin, a circular import.
        import opendate
        obj = self
        if isinstance(self, opendate.DateTime):
            obj = opendate.Date(self.year, self.month, self.day)
            obj._calendar = self._calendar
        return obj._active_calendar.business_hours(obj, obj)\
            .get(obj, (None, None))

    def _add_business_days(self, days: int) -> Self | None:
        """Add business days using Rust calendar.

        Parameters
        ----------
        days : int
            Nonzero business-day count; its sign sets the direction.

        Returns
        -------
        Self or None
            Self unchanged outside MIN_YEAR..MAX_YEAR. None when no calendar
            covers this date or the count runs past the calendar's range.
        """
        if self._is_out_of_range():
            return self
        cal = self._active_calendar._get_calendar(self)
        if cal is None:
            return None
        start_ord = self.toordinal()
        forward = days > 0
        offset = 1 if forward else -1
        find_business_day = cal.next_business_day if forward else cal.prev_business_day
        first_bd = find_business_day(start_ord + offset)
        if first_bd is None:
            return None
        result_ord = cal.add_business_days(first_bd, (abs(days) - 1) * offset)
        if result_ord is None:
            return None
        return super().add(days=result_ord - start_ord)

    @store_calendar
    def _snap_to_business_day(self, forward: bool = True) -> Self:
        """Snap to a business day if not already on one.

        Parameters
        ----------
        forward : bool, default True
            True moves to the next business day, False to the previous.

        Returns
        -------
        Self
            Unchanged on a business day. A date outside MIN_YEAR..MAX_YEAR
            is a sentinel and also comes back unchanged, so a caller after
            the last or first valid business day must start from an
            in-range date such as Date(2100, 12, 31).
        """
        self._business = False
        if self._is_out_of_range():
            return self
        cal = self._active_calendar._get_calendar(self)
        if cal is None:
            return self
        if self.is_business_day():
            return self
        ordinal = self.toordinal()
        if forward:
            target = cal.next_business_day(ordinal)
        else:
            target = cal.prev_business_day(ordinal)
        if target is None:
            return self
        return super().add(days=target - ordinal)

    def _business_or_next(self) -> Self:
        return self._snap_to_business_day(forward=True)

    def _business_or_previous(self) -> Self:
        return self._snap_to_business_day(forward=False)
