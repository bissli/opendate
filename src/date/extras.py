from collections import namedtuple

from date import NYSE, DateTime, Entity

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


Range = namedtuple('Range', ['start', 'end'])


def overlap_days(range_one, range_two, days=False):
    """Calculate how much two date ranges overlap.

    When days=False, returns True/False indicating whether ranges overlap.
    When days=True, returns the actual day count (negative if non-overlapping).

    Algorithm adapted from Raymond Hettinger: http://stackoverflow.com/a/9044111
    """
    r1 = Range(*range_one)
    r2 = Range(*range_two)
    latest_start = max(r1.start, r2.start)
    earliest_end = min(r1.end, r2.end)
    overlap = (earliest_end - latest_start).days + 1
    if days:
        return overlap
    return overlap >= 0


#  def start_of_range(self, unit='month') -> list[Date]:
    #  """Return a series between and inclusive of begdate and enddate.

    #  >>> Interval(Date(2018, 1, 5), Date(2018, 4, 5)).start_of_range('month')
    #  [Date(2018, 1, 1), Date(2018, 2, 1), Date(2018, 3, 1), Date(2018, 4, 1)]
    #  >>> Interval(Date(2018, 4, 30), Date(2018, 7, 30)).start_of_range('month')
    #  [Date(2018, 4, 1), Date(2018, 5, 1), Date(2018, 6, 1), Date(2018, 7, 1)]
    #  >>> Interval(Date(2018, 1, 5), Date(2018, 4, 5)).start_of_range('week')
    #  [Date(2018, 1, 1), Date(2018, 1, 8), ..., Date(2018, 4, 2)]
    #  """
    #  return [type(d).instance(d).start_of(unit) for d in self.range(f'{unit}s')]

#  def end_of_range(self, unit='month') -> list[Date]:
    #  """Return a series between and inclusive of begdate and enddate.

    #  >>> Interval(Date(2018, 1, 5), Date(2018, 4, 5)).end_of_range('month')
    #  [Date(2018, 1, 31), Date(2018, 2, 28), Date(2018, 3, 31), Date(2018, 4, 30)]
    #  >>> Interval(Date(2018, 4, 30), Date(2018, 7, 30)).end_of_range('month')
    #  [Date(2018, 4, 30), Date(2018, 5, 31), Date(2018, 6, 30), Date(2018, 7, 31)]
    #  >>> Interval(Date(2018, 1, 5), Date(2018, 4, 5)).end_of_range('week')
    #  [Date(2018, 1, 7), Date(2018, 1, 14), ..., Date(2018, 4, 8)]
    #  """
    #  return [type(d).instance(d).end_of(unit) for d in self.range(f'{unit}s')]


