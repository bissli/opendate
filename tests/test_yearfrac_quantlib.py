"""Bitwise QuantLib oracle for every yearfrac basis.

QuantLib's date domain is 1901-01-01 to 2199-12-31, which bounds the
sweep.
"""
import datetime
import random
import struct

import pytest
import QuantLib as ql
from opendate import Interval

QL_TWINS = {
    0: ql.Thirty360(ql.Thirty360.USA),
    1: ql.ActualActual(ql.ActualActual.ISDA),
    2: ql.Actual360(),
    3: ql.Actual365Fixed(),
    4: ql.Thirty360(ql.Thirty360.European),
    5: ql.Actual36525(),
    6: ql.Thirty360(ql.Thirty360.BondBasis),
    7: ql.Thirty360(ql.Thirty360.German),
    8: ql.Actual365Fixed(ql.Actual365Fixed.NoLeap),
    }


def ql_date(d):
    return ql.Date(d.day, d.month, d.year)


def assert_bitwise(start, end):
    interval = Interval(start, end)
    for basis, counter in QL_TWINS.items():
        got = interval.yearfrac(basis)
        expected = counter.yearFraction(ql_date(start), ql_date(end))
        assert struct.pack('<d', got) == struct.pack('<d', expected), (
            f'{start}..{end} basis {basis}: {got!r} != {expected!r}')


def month_ends(years):
    ends = []
    for year in years:
        for month in range(1, 13):
            next_month = datetime.date(year + (month == 12), month % 12 + 1, 1)
            ends.append(next_month - datetime.timedelta(days=1))
    return ends


def test_basis_range_matches_twins():
    """Verify every basis in yearfrac's range has a QuantLib twin here.

    Mutation: a basis added to yearfrac without a twin, which leaves it
        outside the bitwise sweeps below.
    Oracle: the basis range yearfrac accepts, probed at each end.
    """
    interval = Interval(datetime.date(2020, 1, 1), datetime.date(2021, 1, 1))
    for basis in QL_TWINS:
        interval.yearfrac(basis)
    with pytest.raises(ValueError):
        interval.yearfrac(max(QL_TWINS) + 1)


def test_month_end_pairs_bitwise():
    """Verify month-end pairs across leap and century windows bitwise.

    Mutation: a twin's 30/360 month-end rule or ACT/ACT leap split
        dropped, 2100 taken as a leap year, or ACT/ACT ISDA dividing a
        same-year span once in place of QuantLib's three-term sum.
    Oracle: QuantLib day counters, IEEE 754 bit equality.
    """
    for window in ((1999, 2000, 2001), (2023, 2024, 2025), (2099, 2100, 2101)):
        ends = month_ends(window)
        for i, start in enumerate(ends):
            for end in ends[i:]:
                assert_bitwise(start, end)


def test_seeded_sweep_bitwise():
    """Verify a seeded sweep of pairs over QuantLib's full date domain.

    Mutation: a divergence the month-end grid misses - mid-month pairs,
        spans over a century, or a float operation reordered so the
        last bit differs.
    Oracle: QuantLib day counters, IEEE 754 bit equality, on ascending
        pairs: QuantLib's 30/360 counters re-run the day rules on a
        reversed pair, where yearfrac negates the ascending value.
    """
    rng = random.Random(20260807)
    lo = datetime.date(1901, 1, 1).toordinal()
    hi = datetime.date(2199, 12, 31).toordinal()
    for _ in range(2000):
        start = datetime.date.fromordinal(rng.randint(lo, hi))
        end = datetime.date.fromordinal(rng.randint(lo, hi))
        if end < start:
            start, end = end, start
        assert_bitwise(start, end)
