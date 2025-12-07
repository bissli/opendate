# OpenDate

A powerful date and time library for Python, built on top of [Pendulum](https://github.com/sdispater/pendulum) with extensive business day support and financial date calculations.

## Overview

OpenDate extends Pendulum's excellent date/time handling with:

- **Business Day Calculations**: NYSE calendar by default, extensible via `exchange-calendars`
- **Enhanced Parsing**: Special codes (`T`, `Y`, `P`), business day offsets (`T-3b`), multiple formats
- **Financial Functions**: Excel-compatible yearfrac, fractional months, period calculations
- **Type Safety**: Comprehensive type annotations and conversion decorators
- **Modular Architecture**: Clean separation following Pendulum's patterns

## Installation

```bash
pip install opendate
```

## Quick Start

```python
from date import Date, DateTime, Time, Interval, EST

# Create dates
today = Date.today()
meeting = DateTime(2024, 1, 15, 14, 30, tzinfo=EST)

# Business day arithmetic
next_business_day = today.business().add(days=1)  # or today.b.add(days=1)
five_business_days_ago = today.b.subtract(days=5)

# Parse various formats
date = Date.parse('2024-01-15')
date = Date.parse('01/15/2024')
date = Date.parse('T-3b')  # 3 business days ago

# Intervals and ranges
interval = Interval(Date(2024, 1, 1), Date(2024, 12, 31))
business_days = interval.b.days  # Count only business days
yearfrac = interval.yearfrac(0)  # Financial year fraction
```

## Core Classes

### Date

Extended `pendulum.Date` with business day awareness:

```python
from date import Date, get_calendar

# Create dates
today = Date.today()
date = Date(2024, 1, 15)
parsed = Date.parse('2024-01-15')

# Business day operations
date.business().add(days=5)     # Add 5 business days
date.b.subtract(days=3)          # Subtract 3 business days (shorthand)
date.b.start_of('month')         # First business day of month
date.b.end_of('month')           # Last business day of month

# Check business day status
date.is_business_day()           # True if NYSE is open
date.business_hours()            # (open_time, close_time) or (None, None)

# Period boundaries
date.start_of('week')            # Monday (or next business day if .b)
date.end_of('month')             # Last day of month
date.first_of('quarter')         # First day of quarter
date.last_of('year')             # December 31

# Navigation
date.next(WeekDay.FRIDAY)        # Next Friday
date.previous(WeekDay.MONDAY)    # Previous Monday
date.lookback('month')           # One month ago
```

### DateTime

Extended `pendulum.DateTime` with business day support:

**Important differences from Pendulum:**
- `DateTime.today()` returns start of day (00:00:00) instead of current time like `pendulum.today()`
- Methods preserve business status and entity when chaining
- `DateTime.instance()` adds UTC timezone by default if none specified

```python
from date import DateTime, EST, UTC

# Create datetimes (timezone parameter available)
now = DateTime.now()                          # Current time in local timezone
now_utc = DateTime.now(tz=UTC)               # Current time in UTC
dt = DateTime(2024, 1, 15, 9, 30, 0, tzinfo=EST)
parsed = DateTime.parse('2024-01-15T09:30:00')  # Parsed with local timezone

# Business day operations (preserves time)
dt.b.add(days=1)                 # Next business day at 9:30 AM
dt.b.subtract(days=3)            # Three business days ago at 9:30 AM

# Timezone conversions
dt.in_timezone(UTC)              # Convert to UTC
dt.astimezone(EST)               # Alternative syntax

# Combine date and time
from date import Date, Time
date = Date(2024, 1, 15)
time = Time(9, 30, tzinfo=EST)
dt = DateTime.combine(date, time, tzinfo=EST)  # tzinfo parameter determines result timezone

# Extract components
dt.date()                        # Date(2024, 1, 15)
dt.time()                        # Time(9, 30, 0, tzinfo=EST)
```

### Time

Extended `pendulum.Time` with enhanced parsing:

```python
from date import Time, UTC

# Create times (timezone must be specified)
time = Time(9, 30, 0, tzinfo=UTC)

# Parsed times default to UTC timezone
parsed = Time.parse('9:30 AM')           # Returns with tzinfo=UTC
parsed = Time.parse('14:30:45.123')      # Returns with tzinfo=UTC

# Supported formats
Time.parse('9:30')               # 09:30:00
Time.parse('9:30 PM')            # 21:30:00
Time.parse('093015')             # 09:30:15
Time.parse('14:30:45.123456')    # With microseconds

# Timezone conversion
time.in_timezone(EST)            # Convert to different timezone
```

### Interval

Extended `pendulum.Interval` with business day and financial calculations:

**Note:** Unlike Pendulum's `Interval.months` (which returns int), OpenDate's returns float with fractional months calculated from actual day counts.

```python
from date import Date, Interval

# Create intervals
start = Date(2024, 1, 1)
end = Date(2024, 12, 31)
interval = Interval(start, end)

# Basic properties
interval.days                    # 365 (calendar days)
interval.months                  # 12.0 (float with fractional months)
interval.years                   # 1 (always floors to int)
interval.quarters                # 4.0 (approximate, based on days/365*4)

# Business day calculations
interval.b.days                  # ~252 (only business days)
interval.calendar('NYSE').b.days # Explicitly set calendar

# Check which days are business days
business_flags = list(interval.is_business_day_range())
# [True, True, True, False, True, ...]  # Mon-Fri are True, Sat-Sun are False

# Iterate over interval with different units
for date in interval.range('days'):
    print(date)                  # Every day

for date in interval.range('weeks'):
    print(date)                  # Every Monday

for date in interval.range('months'):
    print(date)                  # First of each month

for date in interval.range('years'):
    print(date)                  # January 1st of each year

# Business days only (works with 'days' unit)
for date in interval.b.range('days'):
    print(date)                  # Only business days (skips weekends/holidays)

# Get period boundaries within interval
month_starts = interval.start_of('month')
# [2024-01-01, 2024-02-01, ..., 2024-12-01]

month_ends = interval.end_of('month')
# [2024-01-31, 2024-02-29, ..., 2024-12-31]

week_starts = interval.start_of('week')
# All Mondays in the interval

week_ends = interval.end_of('week')
# All Sundays in the interval

quarter_starts = interval.start_of('quarter')
# [2024-01-01, 2024-04-01, 2024-07-01, 2024-10-01]

year_starts = interval.start_of('year')
# [2024-01-01]

# Business day adjustments for period boundaries
# When a period start/end falls on a non-business day, it's automatically adjusted
interval_2018 = Interval(Date(2018, 1, 5), Date(2018, 4, 5))

# Start of month - shifts forward to next business day if needed
business_month_starts = interval_2018.b.start_of('month')
# [2018-01-02, 2018-02-01, 2018-03-01, 2018-04-02]
# Note: Jan 1 is holiday → Jan 2, Apr 1 is Sunday → Apr 2

# End of month - shifts backward to previous business day if needed
business_month_ends = interval_2018.b.end_of('month')
# [2018-01-31, 2018-02-28, 2018-03-29, 2018-04-30]
# Note: Mar 30 is Good Friday → Mar 29

# Works for all time units
interval_weeks = Interval(Date(2018, 1, 5), Date(2018, 1, 25))
business_week_starts = interval_weeks.b.start_of('week')
# [2018-01-02, 2018-01-08, 2018-01-16, 2018-01-22]
# Note: Jan 1 (Mon) is holiday → Jan 2, Jan 15 (Mon) is MLK Day → Jan 16

business_week_ends = interval_weeks.b.end_of('week')
# [2018-01-05, 2018-01-12, 2018-01-19, 2018-01-26]
# All Fridays (already business days)

interval_years = Interval(Date(2017, 6, 1), Date(2019, 6, 1))
business_year_starts = interval_years.b.start_of('year')
# [2017-01-03, 2018-01-02, 2019-01-02]
# Jan 1 falls on holidays/weekends → adjusted to first business day

business_year_ends = interval_years.b.end_of('year')
# [2017-12-29, 2018-12-31, 2019-12-31]
# Dec 31 on weekends → adjusted to last business day before

# Financial calculations (Excel-compatible)
interval.yearfrac(0)             # US 30/360 basis (corporate bonds)
interval.yearfrac(1)             # Actual/actual (Treasury bonds)
interval.yearfrac(2)             # Actual/360 (money market)
interval.yearfrac(3)             # Actual/365 (some bonds)
interval.yearfrac(4)             # European 30/360 (Eurobonds)

# Negative intervals (when end < start)
backward = Interval(Date(2024, 12, 31), Date(2024, 1, 1))
backward.days                    # -365
backward.months                  # -12.0
backward.years                   # -1
```

## Enhanced Parsing

### Date Parsing

```python
from date import Date

# Standard formats
Date.parse('2024-01-15')         # YYYY-MM-DD
Date.parse('01/15/2024')         # MM/DD/YYYY
Date.parse('01/15/24')           # MM/DD/YY
Date.parse('20240115')           # YYYYMMDD

# Named months
Date.parse('15-Jan-2024')        # DD-MON-YYYY
Date.parse('Jan 15, 2024')       # MON DD, YYYY
Date.parse('January 15, 2024')   # Full month name
Date.parse('15JAN2024')          # Compact

# Special codes
Date.parse('T')                  # Today
Date.parse('Y')                  # Yesterday
Date.parse('P')                  # Previous business day
Date.parse('M')                  # Last day of previous month

# Date arithmetic with parsing
Date.parse('T-5')                # 5 days ago
Date.parse('T+10')               # 10 days from now
Date.parse('T-3b')               # 3 business days ago
Date.parse('P+2b')               # 2 business days after previous business day
```

### DateTime Parsing

```python
from date import DateTime

# ISO 8601
DateTime.parse('2024-01-15T09:30:00')
DateTime.parse('2024-01-15T09:30:00Z')

# Date and time separated
DateTime.parse('2024-01-15 09:30:00')
DateTime.parse('01/15/2024 09:30:00')

# Unix timestamps
DateTime.parse(1640995200)       # Seconds
DateTime.parse(1640995200000)    # Milliseconds (auto-detected)

# Special codes (returns start of day)
DateTime.parse('T')              # Today at 00:00:00
DateTime.parse('Y')              # Yesterday at 00:00:00
DateTime.parse('P')              # Previous business day at 00:00:00
```

## Business Day Operations

### Calendars

```python
from date import Date, get_calendar, set_default_calendar

# Use default calendar (NYSE)
date = Date.today().business().add(days=5)

# Change default calendar module-wide
set_default_calendar('LSE')  # All operations now use London Stock Exchange

# Or set calendar explicitly per-operation
date = Date.today().calendar('NYSE').business().add(days=5)

# Check business day status
Date(2024, 1, 1).is_business_day()          # False (New Year's Day)
Date(2024, 7, 4).is_business_day()          # False (Independence Day)
Date(2024, 12, 25).is_business_day()        # False (Christmas)

# Get market hours
Date(2024, 1, 15).business_hours()          # (09:30 AM EST, 04:00 PM EST)
Date(2024, 1, 1).business_hours()           # (None, None) - holiday
```

### Business Day Arithmetic

```python
from date import Date

date = Date(2024, 1, 15)

# Add/subtract business days
date.b.add(days=5)               # 5 business days later
date.b.subtract(days=3)          # 3 business days earlier

# Works across weekends and holidays
Date(2024, 3, 29).b.add(days=1)  # 2024-04-01 (skips Good Friday + weekend)

# Period boundaries with business days
Date(2024, 7, 6).b.start_of('month')  # 2024-07-05 (skips July 4th)
Date(2024, 4, 30).b.end_of('month')   # 2024-04-30 (Tuesday, not Sunday)
```

## Financial Calculations

### Year Fractions

Excel-compatible year fraction calculations for financial formulas:

```python
from date import Date, Interval

start = Date(2024, 1, 1)
end = Date(2024, 12, 31)
interval = Interval(start, end)

# Different day count conventions
interval.yearfrac(0)  # US (NASD) 30/360 - common for US corporate bonds
interval.yearfrac(1)  # Actual/actual - US Treasury bonds
interval.yearfrac(2)  # Actual/360 - money market instruments
interval.yearfrac(3)  # Actual/365 - some corporate bonds
interval.yearfrac(4)  # European 30/360 - Eurobonds
```

### Fractional Periods

**Note:** `Interval.months` returns float (unlike Pendulum which returns int).
Fractional months are calculated based on actual day counts within partial months.

```python
from date import Date, Interval

# Fractional months (not just integer count)
Interval(Date(2024, 1, 1), Date(2024, 2, 15)).months    # ~1.5
Interval(Date(2024, 1, 15), Date(2024, 2, 14)).months   # ~0.97
Interval(Date(2024, 1, 1), Date(2024, 2, 1)).months     # 1.0 (exactly)

# Approximate quarters
Interval(Date(2024, 1, 1), Date(2024, 3, 31)).quarters  # ~1.0
```

## Timezone Handling

```python
from date import DateTime, EST, UTC, GMT, LCL, Timezone

# Built-in timezones
dt_est = DateTime(2024, 1, 15, 9, 30, tzinfo=EST)    # US/Eastern (same as America/New_York)
dt_utc = DateTime(2024, 1, 15, 14, 30, tzinfo=UTC)   # UTC
dt_gmt = DateTime(2024, 1, 15, 14, 30, tzinfo=GMT)   # GMT
dt_lcl = DateTime.now(tz=LCL)                         # Local timezone (from system)

# Custom timezones
tokyo = Timezone('Asia/Tokyo')
dt_tokyo = DateTime(2024, 1, 15, 23, 30, tzinfo=tokyo)

# Convert between timezones (preserves the instant in time, changes timezone)
dt_est.in_timezone(UTC)          # 9:30 AM EST → 2:30 PM UTC
dt_utc.in_tz(EST)                # 2:30 PM UTC → 9:30 AM EST (shorthand)
dt_est.astimezone(tokyo)         # 9:30 AM EST → 11:30 PM JST
```

## Helper Functions and Decorators

### Type Conversion Decorators

```python
from date import expect_date, expect_datetime, expect_time
import datetime

@expect_date
def process_date(d):
    return d.add(days=1)

# Automatically converts datetime.date to Date
result = process_date(datetime.date(2024, 1, 15))  # Returns Date object

@expect_datetime
def process_datetime(dt):
    return dt.add(hours=1)

# Automatically converts to DateTime
result = process_datetime(datetime.datetime(2024, 1, 15, 9, 0))
```

### Timezone Decorators

```python
from date import prefer_utc_timezone, expect_utc_timezone

@prefer_utc_timezone
def get_timestamp():
    return DateTime(2024, 1, 15, 9, 0)  # Adds UTC if no timezone

@expect_utc_timezone
def get_utc_time():
    return DateTime(2024, 1, 15, 9, 0, tzinfo=EST)  # Forces to UTC
```

## Legacy Compatibility Functions

The `date.extras` module provides standalone functions for backward compatibility:

```python
from date import is_business_day, is_within_business_hours
from date import overlap_days
from date import Date, Interval

# Check current time against market hours
is_business_day()                # Is today a business day?
is_within_business_hours()       # Is it between market open/close?

# Calculate interval overlap
interval1 = (Date(2024, 1, 1), Date(2024, 1, 31))
interval2 = (Date(2024, 1, 15), Date(2024, 2, 15))

# Boolean check - do they overlap?
overlap_days(interval1, interval2)            # True (they overlap)

# Get actual day count of overlap
overlap_days(interval1, interval2, days=True)  # 17 (days of overlap)

# Works with Interval objects too
int1 = Interval(Date(2024, 1, 1), Date(2024, 1, 31))
int2 = Interval(Date(2024, 1, 15), Date(2024, 2, 15))
overlap_days(int1, int2, days=True)           # 17

# Non-overlapping intervals return negative
int3 = Interval(Date(2024, 1, 1), Date(2024, 1, 10))
int4 = Interval(Date(2024, 1, 20), Date(2024, 1, 31))
overlap_days(int3, int4)                      # False
overlap_days(int3, int4, days=True)           # -9 (negative = no overlap)
```

## Advanced Features

### Method Chaining

Date and DateTime operations preserve type and state (business mode, calendar), allowing for clean method chaining:

```python
from date import Date

result = Date(2024, 1, 15)\
    .calendar('NYSE')\
    .business()\
    .end_of('month')\
    .subtract(days=5)\
    .start_of('week')
```

### Custom Date Navigation

```python
from date import Date, WeekDay

date = Date(2024, 1, 15)

# Nth occurrence of weekday in period
date.nth_of('month', 3, WeekDay.WEDNESDAY)  # 3rd Wednesday of month

# Named day navigation
date.next(WeekDay.FRIDAY)                    # Next Friday
date.previous(WeekDay.MONDAY)                # Previous Monday

# Relative date finding
date.closest(date1, date2)                   # Closest of two dates
date.farthest(date1, date2)                  # Farthest of two dates
date.average(other_date)                     # Average of two dates
```

### Lookback Operations

```python
from date import Date

date = Date(2024, 1, 15)

date.lookback('day')      # Yesterday
date.lookback('week')     # One week ago
date.lookback('month')    # One month ago
date.lookback('quarter')  # One quarter ago
date.lookback('year')     # One year ago

# With business mode
date.b.lookback('month')  # One month ago, adjusted to business day
```

## Compatibility

OpenDate maintains compatibility with Python datetime, Pandas, and NumPy. It extends Pendulum with some intentional differences for financial use cases:

| Feature                          | Pendulum     | OpenDate                 |
| ---------                        | ----------   | ----------               |
| `DateTime.today()`               | Current time | Start of day (00:00:00)  |
| `DateTime.instance()` default tz | None         | UTC                      |
| `Time.parse()` default tz        | None         | UTC                      |
| `Interval.months`                | int          | float (fractional)       |
| Business day support             | No           | Yes (configurable)       |
| Default calendar                 | N/A          | `set_default_calendar()` |

```python
from date import Date, DateTime
import datetime
import pandas as pd
import numpy as np

# From Python datetime
Date.instance(datetime.date(2024, 1, 15))
DateTime.instance(datetime.datetime(2024, 1, 15, 9, 30))

# From Pandas
Date.instance(pd.Timestamp('2024-01-15'))
DateTime.instance(pd.Timestamp('2024-01-15 09:30:00'))

# From NumPy
Date.instance(np.datetime64('2024-01-15'))
DateTime.instance(np.datetime64('2024-01-15T09:30:00'))
```

## Why OpenDate?

### Over Pendulum

- Business day calculations with holiday awareness
- Financial functions (yearfrac, fractional periods)
- Enhanced parsing with special codes and business day offsets
- Built-in NYSE calendar (extensible to others)
- `Interval.months` returns float for precise financial calculations
- `DateTime.today()` returns start of day for consistent behavior

**Note:** Some Pendulum behavior is intentionally modified for financial use cases.

### Over datetime

- All benefits of Pendulum (better API, timezone handling, etc.)
- Plus all OpenDate business day features
- Cleaner syntax for common date operations
- Period-aware calculations

### Over pandas

- Lighter weight for non-DataFrame operations
- Better business day support
- Cleaner API for date arithmetic
- Financial functions built-in

## Examples

### Generate Month-End Dates

```python
from date import Date, Interval

interval = Interval(Date(2024, 1, 1), Date(2024, 12, 31))

# Get all month-end dates
month_ends = interval.end_of('month')
# [2024-01-31, 2024-02-29, ..., 2024-12-31]

# Get all month-start dates
month_starts = interval.start_of('month')
# [2024-01-01, 2024-02-01, ..., 2024-12-01]

# Get business day month-ends (adjusts for weekends/holidays)
business_month_ends = interval.b.end_of('month')
# Automatically adjusts any month-end that falls on non-business day
# to the previous business day

# Get business day month-starts (adjusts for weekends/holidays)
business_month_starts = interval.b.start_of('month')
# Automatically adjusts any month-start that falls on non-business day
# to the next business day

# Works with other periods too
quarter_ends = interval.end_of('quarter')
# [2024-03-31, 2024-06-30, 2024-09-30, 2024-12-31]

business_quarter_ends = interval.b.end_of('quarter')
# Quarter-ends adjusted to business days

week_starts = interval.start_of('week')
# All Mondays in 2024

business_week_starts = interval.b.start_of('week')
# All week starts adjusted to business days (skips holidays on Mondays)

# Partial year example
partial = Interval(Date(2024, 3, 15), Date(2024, 7, 20))
partial.end_of('month')
# [2024-03-31, 2024-04-30, 2024-05-31, 2024-06-30, 2024-07-31]

partial.b.end_of('month')
# Same as above but adjusted for any non-business days
```

### Calculate Business Days Between Dates

```python
from date import Date, Interval

start = Date(2024, 1, 1)
end = Date(2024, 12, 31)
interval = Interval(start, end)

# Count business days
business_days = interval.b.days  # ~252

# Count calendar days
calendar_days = interval.days    # 365

# Get list of which days are business days
is_bday = list(interval.is_business_day_range())
# [True, True, False, False, True, ...]

# Iterate only over business days
for bday in interval.b.range('days'):
    print(f"{bday} is a business day")
```

### Find Next Options Expiration (3rd Friday)

```python
from date import Date, WeekDay

today = Date.today()
third_friday = today.add(months=1).start_of('month').nth_of('month', 3, WeekDay.FRIDAY)
```

### Working with Market Hours

```python
from date import DateTime, get_calendar

nyse = get_calendar('NYSE')
now = DateTime.now(tz=nyse.tz)

if now.calendar('NYSE').is_business_day():
    open_time, close_time = now.calendar('NYSE').business_hours()
    if open_time <= now <= close_time:
        print("Market is open")
```

### Calculate Interest Accrual

```python
from date import Date, Interval

issue_date = Date(2024, 1, 15)
settlement_date = Date(2024, 6, 15)
coupon_rate = 0.05

# Using Actual/360 convention (basis 2)
days_fraction = Interval(issue_date, settlement_date).yearfrac(2)
accrued_interest = coupon_rate * days_fraction
```

## Developer Guide

See [docs/developer-guide.md](docs/developer-guide.md) for instructions on:

- Setting up the development environment
- Building locally with Rust
- Version management with bump2version
- Releasing to GitHub and PyPI

## Testing

OpenDate includes comprehensive test coverage:

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_date.py
pytest tests/test_business.py
pytest tests/test_interval.py

# Run with coverage
pytest --cov=date tests/
```

## Contributing

OpenDate is open source (MIT License). Contributions welcome!

## License

MIT License - see LICENSE file for details.

## Credits

Built on top of the excellent [Pendulum](https://github.com/sdispater/pendulum) library by Sébastien Eustace.

Business day calendars provided by [pandas-market-calendars](https://github.com/rsheftel/pandas_market_calendars).
