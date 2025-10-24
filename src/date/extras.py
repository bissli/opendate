"""Legacy compatibility functions for OpenDate.

This module contains functions that exist primarily for backward compatibility
with older codebases. These functions provide alternative interfaces to
functionality that may be available through other means in the core Date,
DateTime, and Interval classes.

New code should prefer using the built-in methods on Date, DateTime, and
Interval objects where applicable.
"""

from date import NYSE, Date, DateTime, Entity, Interval

__all__ = [
    'is_within_business_hours',
    'is_business_day',
    'overlap_days',
]


def is_within_business_hours(entity: Entity = NYSE) -> bool:
    """Return whether the current native datetime is between open and close of business hours.
    """
    this = DateTime.now()
    this_entity = DateTime.now(tz=entity.tz).entity(entity)
    bounds = this_entity.business_hours()
    return this_entity.business_open() and (bounds[0] <= this.astimezone(entity.tz) <= bounds[1])


def is_business_day(entity: Entity = NYSE) -> bool:
    """Return whether the current native datetime is a business day.
    """
    return DateTime.now(tz=entity.tz).entity(entity).is_business_day()


def overlap_days(
    interval_one: Interval | tuple[Date | DateTime, Date | DateTime],
    interval_two: Interval | tuple[Date | DateTime, Date | DateTime],
    days: bool = False,
) -> bool | int:
    """Calculate how much two date intervals overlap.

    When days=False, returns True/False indicating whether intervals overlap.
    When days=True, returns the actual day count (negative if non-overlapping).

    Algorithm adapted from Raymond Hettinger: http://stackoverflow.com/a/9044111
    """
    if not isinstance(interval_one, Interval):
        interval_one = Interval(*interval_one)
    if not isinstance(interval_two, Interval):
        interval_two = Interval(*interval_two)

    latest_start = max(interval_one._start, interval_two._start)
    earliest_end = min(interval_one._end, interval_two._end)
    overlap = (earliest_end - latest_start).days + 1
    if days:
        return overlap
    return overlap >= 0
