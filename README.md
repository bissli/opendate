# OpenDate

Date/time library built on [Pendulum](https://github.com/sdispater/pendulum) with business day support and financial calculations. Parsing is 1.2-6x faster than pendulum thanks to a Rust-based dateutil port.

```bash
pip install opendate
```

## Quick Reference

```python
from date import Date, DateTime, Time, Interval
from date import EST, UTC, LCL, WeekDay
from date import get_calendar, set_default_calendar

# Basics
today = Date.today()
now = DateTime.now()
parsed = Date.parse('T-3b')  # 3 business days ago

# Business days
today.b.add(days=5)                    # 5 business days forward
today.calendar('LSE').b.subtract(days=3)  # Using London calendar

# Change default calendar globally
set_default_calendar('LSE')
```

---

## Module Functions

| Function | Description |
|----------|-------------|
| `date(y, m, d)` | Create Date |
| `datetime(y, m, d, h, m, s, tz=UTC)` | Create DateTime (defaults to UTC) |
| `time(h, m, s, tz=UTC)` | Create Time (defaults to UTC) |
| `interval(start, end)` | Create Interval |
| `parse(s, calendar=None)` | Parse to DateTime (calendar optional, uses module default) |
| `instance(obj)` | Convert datetime/date/time (preserves obj's tz if present, else UTC) |
| `now(tz=None)` | Current DateTime (local tz if None) |
| `today(tz=None)` | Today at 00:00:00 (local tz if None) |
| `get_calendar(name)` | Get calendar instance |
| `set_default_calendar(name)` | Set module default calendar |
| `get_default_calendar()` | Get current default calendar name |
| `available_calendars()` | List available calendars |

---

## Date

### Constructors

| Method | Description |
|--------|-------------|
| `Date(y, m, d)` | Create from components |
| `Date.today()` | Current date (uses local tz for current day) |
| `Date.parse(s, fmt=None, calendar='NYSE')` | Parse string. Calendar used for business day codes (T-3b, P), defaults to NYSE |
| `Date.instance(obj)` | From datetime.date, Timestamp, datetime64 |
| `Date.fromordinal(n)` | From ordinal |
| `Date.fromtimestamp(ts, tz=None)` | From Unix timestamp (UTC if None) |

### Properties

Inherited from pendulum: `year`, `month`, `day`, `day_of_week`, `day_of_year`, `week_of_month`, `week_of_year`, `days_in_month`, `quarter`

### Arithmetic

| Method | Description |
|--------|-------------|
| `add(years, months, weeks, days)` | Add time units |
| `subtract(years, months, weeks, days)` | Subtract time units |
| `diff(other)` | Get Interval between dates |

### Period Boundaries

| Method | Description |
|--------|-------------|
| `start_of(unit)` | Start of day/week/month/quarter/year |
| `end_of(unit)` | End of day/week/month/quarter/year |
| `first_of(unit, day_of_week=None)` | First (or first weekday) of period |
| `last_of(unit, day_of_week=None)` | Last (or last weekday) of period |
| `nth_of(unit, n, day_of_week)` | Nth occurrence of weekday in period |

### Navigation

| Method | Description |
|--------|-------------|
| `next(day_of_week=None)` | Next occurrence of weekday |
| `previous(day_of_week=None)` | Previous occurrence of weekday |
| `closest(d1, d2)` | Closer of two dates |
| `farthest(d1, d2)` | Further of two dates |
| `average(other=None)` | Midpoint between dates |
| `lookback(unit)` | Go back by unit: day/week/month/quarter/year |

### Business Day

| Method | Description |
|--------|-------------|
| `business()` or `.b` | Enable business day mode |
| `calendar(name)` | Set calendar (NYSE, LSE, etc.) |
| `is_business_day()` | Check if business day |
| `business_hours()` | Returns `(open, close)` or `(None, None)` |

### Extras

| Method | Description |
|--------|-------------|
| `isoweek()` | ISO week number (1-53) |
| `nearest_start_of_month()` | Nearest month start (threshold: day 15) |
| `nearest_end_of_month()` | Nearest month end (threshold: day 15) |
| `weekday_or_previous_friday()` | Snap weekend to Friday |
| `to_string(fmt)` | Format (handles Windows `%-` → `%#`) |

---

## DateTime

### Constructors

| Method | Description |
|--------|-------------|
| `DateTime(y, m, d, h, m, s, us, tzinfo)` | Create from components |
| `DateTime.now(tz=None)` | Current time (local tz if None) |
| `DateTime.today(tz=None)` | Today at 00:00:00 (local tz if None, **differs from pendulum**) |
| `DateTime.parse(s, calendar='NYSE')` | Parse string or timestamp. Strings: preserve explicit tz, else naive. Timestamps: local tz. Calendar used for business day codes, defaults to NYSE |
| `DateTime.instance(obj, tz=None)` | From datetime, Timestamp, datetime64. Preserves obj's tz if present, else uses `tz` param, else UTC |
| `DateTime.combine(date, time, tzinfo=None)` | Combine Date and Time (uses time's tz if tzinfo=None) |
| `DateTime.fromtimestamp(ts, tz=None)` | From Unix timestamp (UTC if None) |
| `DateTime.utcfromtimestamp(ts)` | From timestamp as UTC |
| `DateTime.utcnow()` | Current UTC time |
| `DateTime.strptime(s, fmt)` | Parse with format |
| `DateTime.fromordinal(n)` | From ordinal |

### Properties

Inherited from pendulum: `year`, `month`, `day`, `hour`, `minute`, `second`, `microsecond`, `day_of_week`, `day_of_year`, `week_of_month`, `week_of_year`, `days_in_month`, `quarter`, `timestamp`, `timezone`, `tz`, `timezone_name`, `offset`, `offset_hours`

### Extraction

| Method | Description |
|--------|-------------|
| `date()` | Extract Date |
| `time()` | Extract Time (preserves tz) |
| `epoch()` | Unix timestamp (alias for `timestamp()`) |

### Timezone

| Method | Description |
|--------|-------------|
| `in_timezone(tz)` | Convert to timezone |
| `in_tz(tz)` | Alias for `in_timezone` |
| `astimezone(tz)` | Alias for `in_timezone` |

### Arithmetic & Navigation

Same as Date: `add`, `subtract`, `diff`, `start_of`, `end_of`, `first_of`, `last_of`, `nth_of`, `next`, `previous`

### Business Day

Same as Date: `business()`, `.b`, `calendar(name)`, `is_business_day()`, `business_hours()`

### Formatting

| Method | Description |
|--------|-------------|
| `format(fmt, locale=None)` | Format with tokens |
| `isoformat()` | ISO 8601 string |
| `rfc3339()` | RFC 3339 (same as isoformat) |
| `to_date_string()` | YYYY-MM-DD |
| `to_datetime_string()` | YYYY-MM-DD HH:MM:SS |
| `to_time_string()` | HH:MM:SS |
| `to_iso8601_string()` | Full ISO 8601 |

---

## Time

### Constructors

| Method | Description |
|--------|-------------|
| `Time(h, m, s, us, tzinfo)` | Create from components |
| `Time.parse(s, fmt=None)` | Parse string (always UTC) |
| `Time.instance(obj, tz=None)` | From datetime.time, datetime. Preserves obj's tz if present, else uses `tz` param, else UTC |

### Properties

`hour`, `minute`, `second`, `microsecond`, `tzinfo`

### Methods

| Method | Description |
|--------|-------------|
| `in_timezone(tz)` | Convert to timezone |
| `in_tz(tz)` | Alias |

---

## Interval

### Constructor

```python
Interval(start, end)  # start/end are Date or DateTime
```

### Properties

| Property | Description |
|----------|-------------|
| `days` | Calendar days (business days if `.b`) |
| `months` | Float with fractional months (**differs from pendulum**) |
| `years` | Complete years (floors) |
| `quarters` | Approximate (days/365*4) |
| `start` | Start date |
| `end` | End date |

### Methods

| Method | Description |
|--------|-------------|
| `business()` or `.b` | Enable business day mode |
| `calendar(name)` | Set calendar |
| `range(unit, amount=1)` | Iterate by unit (days/weeks/months/years) |
| `is_business_day_range()` | Yields bool for each day |
| `start_of(unit)` | List of period starts in interval |
| `end_of(unit)` | List of period ends in interval |
| `yearfrac(basis)` | Year fraction (Excel-compatible) |

### yearfrac Basis

| Basis | Convention | Use |
|-------|------------|-----|
| 0 | US (NASD) 30/360 | Corporate bonds |
| 1 | Actual/actual | Treasury bonds |
| 2 | Actual/360 | Money market |
| 3 | Actual/365 | Some bonds |
| 4 | European 30/360 | Eurobonds |

---

## Parsing

OpenDate uses a dateutil-compatible Rust parser that handles virtually any date/time format. The parser supports fuzzy matching, multiple locales, and automatic format detection.

### Special Codes

| Code | Meaning |
|------|---------|
| `T` or `N` | Today |
| `Y` | Yesterday |
| `P` | Previous business day |
| `M` | Last day of previous month |

### Business Day Offsets

| Pattern | Example | Meaning |
|---------|---------|---------|
| `{code}±{n}` | `T-5` | 5 calendar days ago |
| `{code}±{n}b` | `T-3b` | 3 business days ago |

### Parser Capabilities

- **Dates**: ISO 8601, US/European formats, compact, natural language
- **Times**: 12/24-hour, with/without seconds, AM/PM, timezones
- **Combined**: Any date + time combination, Unix timestamps (auto-detects ms/s)
- **Fuzzy**: Extracts dates from text containing other content

```python
# All of these work
Date.parse('2024-01-15')
Date.parse('Jan 15, 2024')
Date.parse('15/01/2024')
DateTime.parse('2024-01-15T09:30:00Z')
DateTime.parse(1640995200)  # Unix timestamp
DateTime.parse('meeting on Jan 15 at 3pm')  # Fuzzy
```

---

## Business Days

### Default Calendar

```python
from date import set_default_calendar, get_default_calendar

get_default_calendar()      # 'NYSE' initially
set_default_calendar('LSE') # Change globally
```

### Per-Operation Calendar

```python
date.calendar('NYSE').b.add(days=5)
date.calendar('LSE').is_business_day()
```

### Available Calendars

All calendars from [exchange-calendars](https://github.com/gerrymanoim/exchange_calendars): NYSE, LSE, XLON, XPAR, XFRA, XJPX, XHKG, etc.

```python
from date import available_calendars
print(available_calendars())
```

### Business Day Examples

```python
# Add/subtract business days
Date(2024, 3, 29).b.add(days=1)  # Skips Good Friday + weekend

# Period boundaries
Date(2024, 7, 1).b.start_of('month')  # First business day of July
Date(2024, 4, 30).b.end_of('month')   # Last business day of April

# Iterate business days only
for d in Interval(start, end).b.range('days'):
    print(d)

# Count business days
Interval(start, end).b.days
```

---

## Timezones

### Built-in

| Constant | Zone |
|----------|------|
| `UTC` | UTC |
| `GMT` | GMT |
| `EST` | America/New_York |
| `LCL` | System local |

### Custom

```python
from date import Timezone
tokyo = Timezone('Asia/Tokyo')
dt = DateTime(2024, 1, 15, 9, 30, tzinfo=tokyo)
```

### Conversion

```python
dt.in_timezone(UTC)   # or in_tz() or astimezone()
```

---

## Decorators

| Decorator | Effect |
|-----------|--------|
| `@expect_date` | Converts arg to Date |
| `@expect_datetime` | Converts arg to DateTime |
| `@expect_time` | Converts arg to Time |
| `@expect_date_or_datetime` | Converts to Date or DateTime |
| `@prefer_utc_timezone` | Adds UTC if no tz |
| `@expect_utc_timezone` | Converts result to UTC |
| `@prefer_native_timezone` | Adds local tz if no tz |
| `@expect_native_timezone` | Converts result to local |

---

## Extras Module

Legacy standalone functions:

```python
from date import is_business_day, is_within_business_hours, overlap_days

is_business_day()              # Is today a business day?
is_within_business_hours()     # Is current time in market hours?

overlap_days(int1, int2)           # Do intervals overlap? (bool)
overlap_days(int1, int2, days=True) # Day count of overlap (int)
```

---

## Pendulum Differences

| Feature | Pendulum | OpenDate |
|---------|----------|----------|
| `DateTime.today()` | Current time | Start of day (00:00:00) |
| `DateTime.instance()` default tz | None | Preserves obj's tz if present, else UTC |
| `Time.parse()` default tz | None | UTC |
| `Interval.months` | int | float (fractional) |
| Business day support | No | Yes |
| Default calendar | N/A | `set_default_calendar()` |

---

## Examples

### Month-End Dates

```python
interval = Interval(Date(2024, 1, 1), Date(2024, 12, 31))
month_ends = interval.end_of('month')
business_month_ends = interval.b.end_of('month')
```

### Third Friday (Options Expiration)

```python
Date.today().add(months=1).start_of('month').nth_of('month', 3, WeekDay.FRIDAY)
```

### Interest Accrual

```python
days_fraction = Interval(issue_date, settlement_date).yearfrac(2)  # Actual/360
accrued = coupon_rate * days_fraction
```

### Market Hours Check

```python
now = DateTime.now(tz=get_calendar('NYSE').tz)
if now.calendar('NYSE').is_business_day():
    open_time, close_time = now.business_hours()
    if open_time and open_time <= now <= close_time:
        print("Market open")
```

---

## Development

See [docs/developer-guide.md](docs/developer-guide.md)

## License

MIT - Built on [Pendulum](https://github.com/sdispater/pendulum) and [pandas-market-calendars](https://github.com/rsheftel/pandas_market_calendars)
