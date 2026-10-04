"""Test calendar context preservation across all Date/DateTime methods.
"""
import pendulum
import pytest

from opendate import Date, DateTime

DATE_INSTANCE_METHODS = [
    ('add', {'days': 1}),
    ('subtract', {'days': 1}),
    ('first_of', {'unit': 'month'}),
    ('last_of', {'unit': 'month'}),
    ('start_of', {'unit': 'month'}),
    ('end_of', {'unit': 'month'}),
    ('previous', {}),
    ('next', {}),
    ('replace', {'day': 15}),
    ('nth_of', {'unit': 'month', 'nth': 2, 'day_of_week': 0}),
    ('set', {'day': 15}),
    ]

# nth_of is left out because on a DateTime it returns a Date.
DATETIME_INSTANCE_METHODS = [
    ('add', {'days': 1}),
    ('subtract', {'days': 1}),
    ('first_of', {'unit': 'month'}),
    ('last_of', {'unit': 'month'}),
    ('start_of', {'unit': 'month'}),
    ('end_of', {'unit': 'month'}),
    ('previous', {}),
    ('next', {}),
    ('replace', {'day': 15}),
    ('astimezone', {'tz': pendulum.timezone('UTC')}),
    ('in_timezone', {'tz': 'UTC'}),
    ('in_tz', {'tz': 'UTC'}),
    ('at', {'hour': 12, 'minute': 0, 'second': 0}),
    ('on', {'year': 2024, 'month': 6, 'day': 20}),
    ('naive', {}),
    ('set', {'hour': 14}),
    ]


class TestDateCalendarPersistence:
    """Test that Date methods preserve _calendar context."""

    @pytest.fixture
    def date_with_nyse(self):
        """Create a Date with NYSE calendar set."""
        return Date(2024, 6, 15).calendar('NYSE')

    @pytest.mark.parametrize('cal_name', ['NYSE', 'LSE'])
    @pytest.mark.parametrize(('method', 'kwargs'), DATE_INSTANCE_METHODS)
    def test_method_preserves_calendar(self, method, kwargs, cal_name):
        """Each method should preserve the calendar context.

        Mutation: a method returning a Date with no _calendar, or with the
            default NYSE in place of LSE.
        Oracle: the calendar name set on the input.
        """
        d = Date(2024, 6, 15).calendar(cal_name)
        result = getattr(d, method)(**kwargs)

        assert isinstance(result, Date), f'{method} should return Date'
        assert result._calendar is not None, f'{method} lost _calendar'
        assert result._calendar.name == cal_name, (
            f'{method} changed calendar from {cal_name}')

    def test_chained_operations_preserve_calendar(self, date_with_nyse):
        """Chained operations should all preserve calendar.

        Mutation: one link of the chain dropping _calendar.
        Oracle: NYSE set on the input.
        """
        result = (date_with_nyse
                  .add(days=1)
                  .start_of('month')
                  .add(days=5))

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_closest_preserves_calendar(self):
        """Test closest() preserves calendar.

        Mutation: closest() returning the bare argument, which has no
            calendar.
        Oracle: NYSE set on the receiver.
        """
        d = Date(2024, 6, 15).calendar('NYSE')
        d1 = Date(2024, 6, 10)
        d2 = Date(2024, 6, 20)
        result = d.closest(d1, d2)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_farthest_preserves_calendar(self):
        """Test farthest() preserves calendar.

        Mutation: farthest() returning the bare argument, which has no
            calendar.
        Oracle: NYSE set on the receiver.
        """
        d = Date(2024, 6, 15).calendar('NYSE')
        d1 = Date(2024, 6, 10)
        d2 = Date(2024, 6, 20)
        result = d.farthest(d1, d2)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_average_preserves_calendar(self):
        """Test average() preserves calendar.

        Mutation: average() building its result without the receiver's
            calendar.
        Oracle: NYSE set on the receiver.
        """
        d = Date(2024, 6, 15).calendar('NYSE')
        d2 = Date(2024, 6, 20)
        result = d.average(d2)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'


class TestDateTimeCalendarPersistence:
    """Test that DateTime methods preserve _calendar context."""

    @pytest.mark.parametrize('cal_name', ['NYSE', 'LSE'])
    @pytest.mark.parametrize(('method', 'kwargs'), DATETIME_INSTANCE_METHODS)
    def test_method_preserves_calendar(self, method, kwargs, cal_name):
        """Each DateTime method should preserve the calendar context.

        Mutation: a method returning a DateTime with no _calendar, or with
            the default NYSE in place of LSE.
        Oracle: the calendar name set on the input.
        """
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar(cal_name)
        result = getattr(d, method)(**kwargs)

        assert isinstance(result, DateTime), f'{method} should return DateTime'
        assert result._calendar is not None, f'{method} lost _calendar'
        assert result._calendar.name == cal_name, (
            f'{method} changed calendar from {cal_name}')


class TestMetaclassWrappedMethods:
    """Tests for methods wrapped by DateContextMeta metaclass.
    """

    def test_date_set_preserves_calendar(self):
        """Date.set() should preserve calendar.

        Mutation: DateContextMeta leaving Date.set unwrapped.
        Oracle: NYSE set on the input.
        """
        d = Date(2024, 6, 15).calendar('NYSE')
        result = d.set(day=20)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_set_preserves_calendar(self):
        """DateTime.set() should preserve calendar.

        Mutation: DateContextMeta leaving DateTime.set unwrapped.
        Oracle: NYSE set on the input.
        """
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')
        result = d.set(hour=14)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_at_preserves_calendar(self):
        """DateTime.at() should preserve calendar.

        Mutation: the at() wrapper dropping positional arguments or
            _calendar.
        Oracle: NYSE set on the input.
        """
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')
        result = d.at(14, 30, 0)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_on_preserves_calendar(self):
        """DateTime.on() should preserve calendar.

        Mutation: the on() wrapper dropping positional arguments or
            _calendar.
        Oracle: NYSE set on the input.
        """
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')
        result = d.on(2024, 7, 1)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_naive_preserves_calendar(self):
        """DateTime.naive() should preserve calendar.

        Mutation: naive() on an aware DateTime dropping _calendar.
        Oracle: NYSE set on the input.
        """
        tz = pendulum.timezone('US/Eastern')
        d = DateTime(2024, 6, 15, 12, 0, 0, tzinfo=tz).calendar('NYSE')
        result = d.naive()

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
