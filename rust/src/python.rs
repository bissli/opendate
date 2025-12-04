use pyo3::prelude::*;

use crate::calendar;

#[pyclass(name = "BusinessCalendar")]
pub struct PyBusinessCalendar {
    inner: calendar::BusinessCalendar,
}

#[pymethods]
impl PyBusinessCalendar {
    #[new]
    fn new(ordinals: Vec<i32>) -> Self {
        PyBusinessCalendar {
            inner: calendar::BusinessCalendar::new(ordinals),
        }
    }

    fn is_business_day(&self, ordinal: i32) -> bool {
        self.inner.is_business_day(ordinal)
    }

    fn add_business_days(&self, ordinal: i32, n: i32) -> Option<i32> {
        self.inner.add_business_days(ordinal, n)
    }

    fn next_business_day(&self, ordinal: i32) -> Option<i32> {
        self.inner.next_business_day(ordinal)
    }

    fn prev_business_day(&self, ordinal: i32) -> Option<i32> {
        self.inner.prev_business_day(ordinal)
    }

    fn business_days_in_range(&self, start: i32, end: i32) -> Vec<i32> {
        self.inner.business_days_in_range(start, end)
    }

    fn count_business_days(&self, start: i32, end: i32) -> usize {
        self.inner.count_business_days(start, end)
    }

    fn get_business_day_index(&self, ordinal: i32) -> Option<usize> {
        self.inner.get_index(ordinal)
    }

    fn get_business_day_at_index(&self, index: usize) -> Option<i32> {
        self.inner.get_at_index(index)
    }

    fn len(&self) -> usize {
        self.inner.len()
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

#[pymodule]
pub fn _opendate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBusinessCalendar>()?;
    Ok(())
}
