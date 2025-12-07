"""Test calendar context preservation across all Date/DateTime methods.

This test matrix ensures that _calendar context is preserved when calling
any pendulum method that returns a new Date or DateTime object.
"""
import pendulum
import pytest

from date import Date, DateTime

# Date methods that return a new Date and should preserve calendar
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

# DateTime-specific methods (in addition to Date methods)
# Note: nth_of is excluded for DateTime since it returns Date, not DateTime
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

    @pytest.fixture
    def date_with_lse(self):
        """Create a Date with LSE calendar set."""
        return Date(2024, 6, 15).calendar('LSE')

    @pytest.mark.parametrize(('method', 'kwargs'), DATE_INSTANCE_METHODS)
    def test_method_preserves_nyse_calendar(self, date_with_nyse, method, kwargs):
        """Each method should preserve NYSE calendar context."""
        d = date_with_nyse
        result = getattr(d, method)(**kwargs)

        assert isinstance(result, Date), f'{method} should return Date'
        assert result._calendar is not None, f'{method} lost _calendar'
        assert result._calendar.name == 'NYSE', f'{method} changed calendar from NYSE'

    @pytest.mark.parametrize(('method', 'kwargs'), DATE_INSTANCE_METHODS)
    def test_method_preserves_lse_calendar(self, date_with_lse, method, kwargs):
        """Each method should preserve LSE (non-default) calendar context."""
        d = date_with_lse
        result = getattr(d, method)(**kwargs)

        assert isinstance(result, Date), f'{method} should return Date'
        assert result._calendar is not None, f'{method} lost _calendar'
        assert result._calendar.name == 'LSE', f'{method} changed calendar from LSE'

    def test_chained_operations_preserve_calendar(self, date_with_nyse):
        """Chained operations should all preserve calendar."""
        result = (date_with_nyse
                  .add(days=1)
                  .start_of('month')
                  .add(days=5))

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_closest_preserves_calendar(self):
        """Test closest() preserves calendar."""
        d = Date(2024, 6, 15).calendar('NYSE')
        d1 = Date(2024, 6, 10)
        d2 = Date(2024, 6, 20)
        result = d.closest(d1, d2)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_farthest_preserves_calendar(self):
        """Test farthest() preserves calendar."""
        d = Date(2024, 6, 15).calendar('NYSE')
        d1 = Date(2024, 6, 10)
        d2 = Date(2024, 6, 20)
        result = d.farthest(d1, d2)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_average_preserves_calendar(self):
        """Test average() preserves calendar."""
        d = Date(2024, 6, 15).calendar('NYSE')
        d2 = Date(2024, 6, 20)
        result = d.average(d2)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'


class TestDateTimeCalendarPersistence:
    """Test that DateTime methods preserve _calendar context."""

    @pytest.fixture
    def datetime_with_nyse(self):
        """Create a DateTime with NYSE calendar set."""
        return DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')

    @pytest.fixture
    def datetime_with_lse(self):
        """Create a DateTime with LSE calendar set."""
        return DateTime(2024, 6, 15, 12, 0, 0).calendar('LSE')

    @pytest.mark.parametrize(('method', 'kwargs'), DATETIME_INSTANCE_METHODS)
    def test_method_preserves_nyse_calendar(self, datetime_with_nyse, method, kwargs):
        """Each DateTime method should preserve NYSE calendar context."""
        d = datetime_with_nyse
        result = getattr(d, method)(**kwargs)

        assert isinstance(result, DateTime), f'{method} should return DateTime'
        assert result._calendar is not None, f'{method} lost _calendar'
        assert result._calendar.name == 'NYSE', f'{method} changed calendar from NYSE'

    @pytest.mark.parametrize(('method', 'kwargs'), DATETIME_INSTANCE_METHODS)
    def test_method_preserves_lse_calendar(self, datetime_with_lse, method, kwargs):
        """Each DateTime method should preserve LSE (non-default) calendar context."""
        d = datetime_with_lse
        result = getattr(d, method)(**kwargs)

        assert isinstance(result, DateTime), f'{method} should return DateTime'
        assert result._calendar is not None, f'{method} lost _calendar'
        assert result._calendar.name == 'LSE', f'{method} changed calendar from LSE'


class TestMetaclassWrappedMethods:
    """Tests for methods wrapped by DateContextMeta metaclass.

    These methods are automatically wrapped to preserve _calendar context
    when they return new Date/DateTime instances.
    """

    def test_date_set_preserves_calendar(self):
        """Date.set() should preserve calendar."""
        d = Date(2024, 6, 15).calendar('NYSE')
        result = d.set(day=20)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_set_preserves_calendar(self):
        """DateTime.set() should preserve calendar."""
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')
        result = d.set(hour=14)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_at_preserves_calendar(self):
        """DateTime.at() should preserve calendar."""
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')
        result = d.at(14, 30, 0)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_on_preserves_calendar(self):
        """DateTime.on() should preserve calendar."""
        d = DateTime(2024, 6, 15, 12, 0, 0).calendar('NYSE')
        result = d.on(2024, 7, 1)

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'

    def test_datetime_naive_preserves_calendar(self):
        """DateTime.naive() should preserve calendar."""
        import pendulum
        d = DateTime(2024, 6, 15, 12, 0, 0, tzinfo=pendulum.timezone('US/Eastern')).calendar('NYSE')
        result = d.naive()

        assert result._calendar is not None
        assert result._calendar.name == 'NYSE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
