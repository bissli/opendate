import pendulum
import pytest

from opendate import UTC, Date, DateTime, Time


def test_time_constructor():
    """None or empty constructor returns current time
    """
    T = Time()
    assert T == pendulum.Time()
    assert isinstance(T, Time)


def test_datetime_to_time():

    D = pendulum.DateTime(2022, 1, 1, 12, 30)
    assert Time.instance(D.time()) == Time(12, 30, tzinfo=UTC)


@pytest.mark.parametrize(('input_str', 'expected'), [
    # Colon-separated formats
    ('9:30', Time(9, 30, 0, tzinfo=UTC)),
    ('9:30:15', Time(9, 30, 15, tzinfo=UTC)),
    ('9:30:15.751', Time(9, 30, 15, 751000, tzinfo=UTC)),
    ('9:30 AM', Time(9, 30, 0, tzinfo=UTC)),
    ('9:30 pm', Time(21, 30, 0, tzinfo=UTC)),
    ('9:30:15.751 PM', Time(21, 30, 15, 751000, tzinfo=UTC)),
    # Compact formats
    ('0930', Time(9, 30, 0, tzinfo=UTC)),
    ('093015', Time(9, 30, 15, tzinfo=UTC)),
    ('093015,751', Time(9, 30, 15, 751000, tzinfo=UTC)),
    ('093015.751', Time(9, 30, 15, 751000, tzinfo=UTC)),  # dot fraction
    ('0930 pm', Time(21, 30, 0, tzinfo=UTC)),
    ('093015,751 PM', Time(21, 30, 15, 751000, tzinfo=UTC)),
    # Dot-separated formats
    ('9.30', Time(9, 30, 0, tzinfo=UTC)),
    ('9.30.15', Time(9, 30, 15, tzinfo=UTC)),
    # Midnight and noon edge cases
    ('1200 AM', Time(0, 0, 0, tzinfo=UTC)),   # 12 AM = midnight
    ('12:00 PM', Time(12, 0, 0, tzinfo=UTC)),  # 12 PM = noon
    ('12:00 AM', Time(0, 0, 0, tzinfo=UTC)),  # 12 AM = midnight (colon format)
])
def test_time_parse_formats(input_str, expected):
    """Test Time.parse with various format strings."""
    assert Time.parse(input_str) == expected


@pytest.mark.parametrize('input_str', [
    '9930',   # invalid hour (99)
    '0970',   # invalid minute (70)
    '930',    # 3 digits (invalid)
    '09301',  # 5 digits (invalid)
])
def test_time_parse_invalid(input_str):
    """Test Time.parse returns None for invalid inputs."""
    assert Time.parse(input_str) is None


def test_time_instance_basic():
    """Test Time.instance with various input types.
    """
    import datetime

    assert Time.instance(datetime.time(12, 30, 1)) == Time(12, 30, 1, tzinfo=UTC)
    assert Time.instance(pendulum.Time(12, 30, 1)) == Time(12, 30, 1, tzinfo=UTC)
    assert Time.instance(None) is None

    result = Time.instance(Time(12, 30, 1))
    assert result == Time(12, 30, 1)
    assert result.tzinfo is None


def test_time_in_timezone():
    """Test timezone conversion for Time objects.
    """
    from opendate import Timezone

    result = Time(12, 0).in_timezone(Timezone('America/Sao_Paulo'))
    assert result.hour == 9
    assert result.minute == 0
    assert result.second == 0

    result = Time(12, 0, tzinfo=Timezone('Europe/Moscow')).in_timezone(Timezone('America/Sao_Paulo'))
    assert result.hour == 6
    assert result.minute == 0
    assert result.second == 0


def test_combine():
    """Test DateTime.combine with different timezones"""

    D = Date(2022, 1, 1)
    T = Time(12, 30)

    # Use EST instead of LCL to ensure timezone differs from UTC in CI
    from opendate import EST

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=EST)
    assert _.tzinfo == EST

    comb = DateTime.combine(D, T, tzinfo=EST)
    assert comb == _

    comb = DateTime.combine(D, T, tzinfo=UTC)
    assert comb != _

    # ==

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=EST)
    assert _.tzinfo == EST

    comb = DateTime.combine(D, T, tzinfo=EST)
    assert comb == _

    comb = DateTime.combine(D, T, tzinfo=UTC)
    assert comb != _

    # ==

    _ = DateTime(2022, 1, 1, 12, 30, tzinfo=UTC)
    assert _.tzinfo == UTC

    comb = DateTime.combine(D, T, tzinfo=UTC)
    assert comb == _

    comb = DateTime.combine(D, T, tzinfo=EST)
    assert comb != _


if __name__ == '__main__':
    pytest.main([__file__])
