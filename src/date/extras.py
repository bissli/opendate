from collections import namedtuple

from date import NYSE, DateTime, Entity

__all__ = [
    'is_within_business_hours',
    'is_business_day',
    'overlap_days',
]


def is_within_business_hours(entity: Entity = NYSE) -> bool:
    """Return whether the current native datetime is between
    open and close of business hours.

    >>> from unittest.mock import patch
    >>> tz = NYSE.tz

    >>> with patch('date.DateTime.now') as mock:
    ...     mock.return_value = DateTime(2000, 5, 1, 12, 30, 0, 0, tzinfo=tz)
    ...     is_within_business_hours()
    True

    >>> with patch('date.DateTime.now') as mock:
    ...     mock.return_value = DateTime(2000, 7, 2, 12, 15, 0, 0, tzinfo=tz) # Sunday
    ...     is_within_business_hours()
    False

    >>> with patch('date.DateTime.now') as mock:
    ...     mock.return_value = DateTime(2000, 11, 1, 1, 15, 0, 0, tzinfo=tz)
    ...     is_within_business_hours()
    False

    """
    this = DateTime.now()
    this_entity = DateTime.now(tz=entity.tz).entity(entity)
    bounds = this_entity.business_hours()
    return this_entity.business_open() and (bounds[0] <= this.astimezone(entity.tz) <= bounds[1])


def is_business_day(entity: Entity = NYSE) -> bool:
    """Return whether the current native datetime is a business day.
    """
    return DateTime.now(tz=entity.tz).entity(entity).is_business_day()


Range = namedtuple('Range', ['start', 'end'])


def overlap_days(range_one, range_two, days=False):
    """Test by how much two date ranges overlap
    if `days=True`, we return an actual day count,
    otherwise we just return if it overlaps True/False
    poached from Raymond Hettinger http://stackoverflow.com/a/9044111

    >>> from date import Date
    >>> date1 = Date(2016, 3, 1)
    >>> date2 = Date(2016, 3, 2)
    >>> date3 = Date(2016, 3, 29)
    >>> date4 = Date(2016, 3, 30)

    >>> assert overlap_days((date1, date3), (date2, date4))
    >>> assert overlap_days((date2, date4), (date1, date3))
    >>> assert not overlap_days((date1, date2), (date3, date4))

    >>> assert overlap_days((date1, date4), (date1, date4))
    >>> assert overlap_days((date1, date4), (date2, date3))
    >>> overlap_days((date1, date4), (date1, date4), True)
    30

    >>> assert overlap_days((date2, date3), (date1, date4))
    >>> overlap_days((date2, date3), (date1, date4), True)
    28

    >>> assert not overlap_days((date3, date4), (date1, date2))
    >>> overlap_days((date3, date4), (date1, date2), True)
    -26
    """
    r1 = Range(*range_one)
    r2 = Range(*range_two)
    latest_start = max(r1.start, r2.start)
    earliest_end = min(r1.end, r2.end)
    overlap = (earliest_end - latest_start).days + 1
    if days:
        return overlap
    return overlap >= 0


if __name__ == '__main__':
    __import__('doctest').testmod(optionflags=4 | 8 | 32)
