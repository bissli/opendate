opendate
========

A wrapper around [Pendulum](https://github.com/sdispater/pendulum) with business (NYSE default, extendable) days/hours awareness.

Documentation pending, see tests for examples. Functionality is near-identical to Pendulum with the exception of a business modifier.

The main module is named `date` rather than `pendulum`

Ex:

```python

from date import Date, DateTime, Time, Interval

thedate = Date.today()

# add days
thedate.add(days=5)
thedate.business().add(days=5) # add 5 business day

# subtract days
thedate.subtract(days=5)
thedate.business().subtract(days=5) # subtract 5 business day

# start of month
thedate.start_of('month')
thedate.business().start_of('month') # end of month + N days until valid business day

# end of month
thedate.end_of('month')
thedate.business().end_of('month') # end of month - N days until valid business day

# ...

```
