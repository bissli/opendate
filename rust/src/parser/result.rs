//! Parse result structures for datetime parsing.
//!
//! This module defines the `ParseResult` struct that holds parsed datetime components.
//! It mirrors dateutil's internal result structure but uses Rust types.

use pyo3::prelude::*;

/// Result of parsing a datetime string.
///
/// All fields are optional since different input strings may only specify
/// some components (e.g., "14:30" only has hour and minute).
#[derive(Debug, Clone, Default)]
pub struct ParseResult {
    /// Year (e.g., 2024)
    pub year: Option<i32>,
    /// Month (1-12)
    pub month: Option<u32>,
    /// Day of month (1-31)
    pub day: Option<u32>,
    /// Hour (0-23)
    pub hour: Option<u32>,
    /// Minute (0-59)
    pub minute: Option<u32>,
    /// Second (0-59)
    pub second: Option<u32>,
    /// Microsecond (0-999999)
    pub microsecond: Option<u32>,
    /// Day of week (0=Monday, 6=Sunday)
    pub weekday: Option<u32>,
    /// Timezone offset in seconds from UTC (e.g., -18000 for EST)
    pub tzoffset: Option<i32>,
    /// Timezone name (e.g., "EST", "UTC")
    pub tzname: Option<String>,
    /// Whether the century was explicitly specified (4-digit year vs 2-digit)
    pub century_specified: bool,
    /// AM/PM indicator (0=AM, 1=PM, None=24-hour)
    pub ampm: Option<u32>,
}

impl ParseResult {
    /// Create a new empty ParseResult.
    pub fn new() -> Self {
        Self::default()
    }

    /// Check if any date components are set.
    pub fn has_date(&self) -> bool {
        self.year.is_some() || self.month.is_some() || self.day.is_some()
    }

    /// Check if any time components are set.
    pub fn has_time(&self) -> bool {
        self.hour.is_some() || self.minute.is_some() || self.second.is_some()
    }

    /// Check if timezone info is set.
    pub fn has_tz(&self) -> bool {
        self.tzoffset.is_some() || self.tzname.is_some()
    }
}

/// Python-exposed ParseResult for returning parsed components to Python.
#[pyclass(name = "ParseResult")]
#[derive(Debug, Clone)]
pub struct PyParseResult {
    #[pyo3(get)]
    pub year: Option<i32>,
    #[pyo3(get)]
    pub month: Option<u32>,
    #[pyo3(get)]
    pub day: Option<u32>,
    #[pyo3(get)]
    pub hour: Option<u32>,
    #[pyo3(get)]
    pub minute: Option<u32>,
    #[pyo3(get)]
    pub second: Option<u32>,
    #[pyo3(get)]
    pub microsecond: Option<u32>,
    #[pyo3(get)]
    pub weekday: Option<u32>,
    #[pyo3(get)]
    pub tzoffset: Option<i32>,
    #[pyo3(get)]
    pub tzname: Option<String>,
}

#[pymethods]
impl PyParseResult {
    fn __repr__(&self) -> String {
        format!(
            "ParseResult(year={:?}, month={:?}, day={:?}, hour={:?}, minute={:?}, second={:?}, microsecond={:?}, tzoffset={:?}, tzname={:?})",
            self.year, self.month, self.day, self.hour, self.minute, self.second, self.microsecond, self.tzoffset, self.tzname
        )
    }
}

impl From<ParseResult> for PyParseResult {
    fn from(r: ParseResult) -> Self {
        PyParseResult {
            year: r.year,
            month: r.month,
            day: r.day,
            hour: r.hour,
            minute: r.minute,
            second: r.second,
            microsecond: r.microsecond,
            weekday: r.weekday,
            tzoffset: r.tzoffset,
            tzname: r.tzname,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_result_default() {
        let r = ParseResult::new();
        assert!(r.year.is_none());
        assert!(r.month.is_none());
        assert!(!r.has_date());
        assert!(!r.has_time());
        assert!(!r.has_tz());
    }

    #[test]
    fn test_parse_result_with_date() {
        let mut r = ParseResult::new();
        r.year = Some(2024);
        r.month = Some(1);
        r.day = Some(15);
        assert!(r.has_date());
        assert!(!r.has_time());
    }

    #[test]
    fn test_parse_result_with_time() {
        let mut r = ParseResult::new();
        r.hour = Some(14);
        r.minute = Some(30);
        assert!(!r.has_date());
        assert!(r.has_time());
    }
}
