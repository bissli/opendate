"""Hand-computed yearfrac cases for each branch of each basis.

These pin every day rule without QuantLib. The bitwise QuantLib sweep is
in test_yearfrac_quantlib.py.
"""
import struct

import pytest
from opendate import Date, DateTime, Interval


def yearfrac(start, end, basis):
    return Interval(start, end).yearfrac(basis)


def bits(x):
    return struct.pack('<d', x)


def test_usa_rule_order():
    """Verify the 30/360 US rules apply in SIA order, each reading the last.

    Mutation: the rules run as an if/elif chain, so a start on the last
        day of February stops the chain and an end on the 31st stays 31;
        or the d2 rule tested before the February rule sets d1.
    Oracle: hand-computed SIA numerators.
    """
    assert yearfrac(Date(2025, 1, 31), Date(2025, 3, 31), 0) == 60 / 360
    assert yearfrac(Date(2025, 1, 31), Date(2025, 2, 15), 0) == 15 / 360
    assert yearfrac(Date(2023, 1, 15), Date(2023, 3, 31), 0) == 76 / 360
    assert yearfrac(Date(2023, 2, 28), Date(2024, 2, 29), 0) == 1.0
    assert yearfrac(Date(2023, 2, 28), Date(2023, 8, 31), 0) == 180 / 360
    assert yearfrac(Date(2024, 2, 29), Date(2025, 3, 31), 0) == 390 / 360


def test_end_of_february_is_leap_aware():
    """Verify February 28 counts as month-end only in a common year.

    Mutation: the end-of-February test reduced to month 2 and day >= 28,
        which mis-accrues 3 days on a 30/360 US period starting
        2024-02-28 and 2 days on a 30E/360 ISDA period ending there.
    Oracle: hand-computed numerators. Each leap case sits beside the
        February 29 and common-year February 28 cases that must still
        clamp, so the test fails in both directions.
    """
    assert yearfrac(Date(2024, 2, 28), Date(2024, 8, 31), 0) == 183 / 360
    assert yearfrac(Date(2024, 2, 29), Date(2024, 8, 31), 0) == 180 / 360
    assert yearfrac(Date(2023, 2, 28), Date(2023, 8, 31), 0) == 180 / 360

    assert yearfrac(Date(2024, 1, 15), Date(2024, 2, 28), 7) == 43 / 360
    assert yearfrac(Date(2024, 1, 15), Date(2024, 2, 29), 7) == 45 / 360
    assert yearfrac(Date(2023, 1, 15), Date(2023, 2, 28), 7) == 45 / 360


def test_thirty_360_family_divergence():
    """Pin the pairs where the four 30/360 bases differ.

    Mutation: Bond Basis (6) gaining the February rule, 30/360 US (0)
        losing it, or 30E/360 ISDA (7) losing its end-of-February clamp
        and collapsing into 30E/360 (4).
    Oracle: hand-computed numerators.
    """
    cases = [
        (Date(2023, 2, 28), Date(2023, 8, 31), 180, 183),
        (Date(2021, 2, 28), Date(2021, 3, 31), 30, 33),
        (Date(2024, 2, 29), Date(2024, 10, 31), 240, 242),
        ]
    for start, end, usa, bond in cases:
        assert yearfrac(start, end, 0) == usa / 360
        assert yearfrac(start, end, 6) == bond / 360
    assert yearfrac(Date(2025, 1, 31), Date(2025, 2, 28), 4) == 28 / 360
    assert yearfrac(Date(2025, 1, 31), Date(2025, 2, 28), 7) == 30 / 360
    assert yearfrac(Date(2023, 2, 28), Date(2023, 8, 31), 4) == 182 / 360


def test_no_leap_drops_the_leap_day():
    """Verify ACT/365 No Leap removes February 29 from the day count.

    Mutation: basis 8 counting February 29, or dropping it from the
        denominator instead of the numerator, which makes a leap span
        366/366 in place of 365/365.
    Oracle: hand-computed day counts, against ACT/365 Fixed (3) on the
        same span.
    """
    assert yearfrac(Date(2023, 3, 1), Date(2024, 3, 1), 8) == 1.0
    assert yearfrac(Date(2023, 3, 1), Date(2024, 3, 1), 3) == 366 / 365
    assert yearfrac(Date(2024, 2, 28), Date(2024, 3, 1), 8) == 1 / 365
    assert yearfrac(Date(2024, 2, 29), Date(2024, 3, 1), 8) == 1 / 365
    assert yearfrac(Date(2023, 1, 1), Date(2025, 1, 1), 8) == 2.0


def test_act_act_isda_split():
    """Verify ACT/ACT ISDA divides each calendar year's days by its length.

    Mutation: one denominator for the whole span, such as the average
        year length across the span, or 366 whenever a February 29 lies
        inside it. Both agree within one calendar year and diverge
        across a year end.
    Oracle: hand-computed per-year sums.
    """
    assert yearfrac(Date(2023, 1, 1), Date(2025, 1, 1), 1) == 2.0
    assert yearfrac(Date(2023, 7, 1), Date(2025, 7, 1), 1) == 2.0
    assert yearfrac(Date(2023, 6, 1), Date(2024, 3, 1), 1) == 214 / 365 + 60 / 366
    assert yearfrac(Date(2023, 5, 10), Date(2024, 5, 10), 1) == 236 / 365 + 130 / 366
    assert yearfrac(Date(2028, 3, 6), Date(2029, 2, 13), 1) == 301 / 366 + 43 / 365


def test_reversed_interval_negates():
    """Verify a reversed interval returns the negated ascending value.

    Mutation: the 30/360 rules re-run on the reversed pair, as QuantLib
        does, which reads the February rule off the other endpoint; or
        the sign lost on one basis.
    Oracle: the ascending value, negated, compared as IEEE 754 bits.
    """
    start, end = Date(2021, 2, 28), Date(2021, 3, 31)
    for basis in range(9):
        forward = yearfrac(start, end, basis)
        assert bits(yearfrac(end, start, basis)) == bits(-forward), basis
    assert yearfrac(Date(2026, 1, 1), Date(2025, 1, 1), 0) == -1.0


def test_same_day_datetimes_are_zero():
    """Verify endpoints on one day at different times give exactly 0.0.

    Mutation: the zero shortcut comparing full datetimes, so a same-day
        pair reaches the ACT/ACT ISDA three-term sum, which rounds to
        about 1e-17 in place of zero.
    Oracle: QuantLib returns 0.0 for equal dates, and yearfrac reads only
        the date.
    """
    for day in (2, 6):
        start, end = DateTime(2023, 1, day, 9), DateTime(2023, 1, day, 17)
        for basis in range(9):
            assert bits(yearfrac(start, end, basis)) == bits(0.0), (day, basis)


def test_invalid_basis():
    """Verify a basis outside 0-8 raises ValueError.

    Mutation: the range check dropped, so an unknown basis returns None.
    Oracle: the documented basis range 0-8.
    """
    for bad in (-1, 9, 100):
        with pytest.raises(ValueError, match='Basis range'):
            yearfrac(Date(2020, 1, 1), Date(2021, 1, 1), bad)
