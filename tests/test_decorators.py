import pytest
from opendate import Date
from opendate.decorators import store_calendar, type_class


def test_type_class_rejects_unknown_name():
    """type_class raises on a str naming no opendate class.

    Mutation: an unknown str returned as it is, so store_calendar later
        calls .instance on a str.
    Oracle: type_class's docstring, which returns a type and names only
        'Date', 'DateTime' and 'Interval'.
    """
    assert type_class('Date', None) is Date
    with pytest.raises(ValueError, match='Unknown type Foo'):
        type_class('Foo', Date(2024, 1, 10))

    class Holder:
        _calendar = None

        @store_calendar(typ='Foo')
        def value(self):
            return Date(2024, 1, 10)

    with pytest.raises(ValueError, match='Unknown type Foo'):
        Holder().value()


def test_type_class_empty_name_picks_class_from_obj():
    """type_class treats an empty str like None and reads obj's class.

    Mutation: any str, the empty one included, routed to the name lookup,
        which raises ValueError.
    Oracle: the typ docstring entry; an empty str is falsy, as None is.
    """
    assert type_class('', Date(2024, 1, 10)) is Date
