//! Parser error types.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::fmt;

/// Errors that can occur during datetime parsing.
#[derive(Debug, Clone)]
pub enum ParserError {
    /// Input string is empty
    EmptyString,
    /// Failed to parse the input string
    ParseError(String),
    /// Invalid value for a datetime component
    InvalidValue { field: &'static str, value: i64 },
    /// Ambiguous date that cannot be resolved
    AmbiguousDate(String),
    /// Invalid timezone specification
    InvalidTimezone(String),
    /// Year out of valid range
    YearOutOfRange(i32),
    /// Month out of valid range (1-12)
    MonthOutOfRange(u32),
    /// Day out of valid range for the given month
    DayOutOfRange { year: i32, month: u32, day: u32 },
    /// Hour out of valid range (0-23)
    HourOutOfRange(u32),
    /// Minute out of valid range (0-59)
    MinuteOutOfRange(u32),
    /// Second out of valid range (0-59)
    SecondOutOfRange(u32),
    /// Microsecond out of valid range (0-999999)
    MicrosecondOutOfRange(u32),
}

impl fmt::Display for ParserError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParserError::EmptyString => write!(f, "Empty string"),
            ParserError::ParseError(msg) => write!(f, "Parse error: {}", msg),
            ParserError::InvalidValue { field, value } => {
                write!(f, "Invalid {} value: {}", field, value)
            }
            ParserError::AmbiguousDate(s) => write!(f, "Ambiguous date: {}", s),
            ParserError::InvalidTimezone(s) => write!(f, "Invalid timezone: {}", s),
            ParserError::YearOutOfRange(y) => write!(f, "Year out of range: {}", y),
            ParserError::MonthOutOfRange(m) => write!(f, "Month out of range: {}", m),
            ParserError::DayOutOfRange { year, month, day } => {
                write!(f, "Day {} out of range for {}-{:02}", day, year, month)
            }
            ParserError::HourOutOfRange(h) => write!(f, "Hour out of range: {}", h),
            ParserError::MinuteOutOfRange(m) => write!(f, "Minute out of range: {}", m),
            ParserError::SecondOutOfRange(s) => write!(f, "Second out of range: {}", s),
            ParserError::MicrosecondOutOfRange(us) => {
                write!(f, "Microsecond out of range: {}", us)
            }
        }
    }
}

impl std::error::Error for ParserError {}

impl From<ParserError> for PyErr {
    fn from(err: ParserError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        assert_eq!(ParserError::EmptyString.to_string(), "Empty string");
        assert_eq!(
            ParserError::ParseError("test".to_string()).to_string(),
            "Parse error: test"
        );
        assert_eq!(
            ParserError::InvalidValue {
                field: "month",
                value: 13
            }
            .to_string(),
            "Invalid month value: 13"
        );
        assert_eq!(
            ParserError::DayOutOfRange {
                year: 2024,
                month: 2,
                day: 30
            }
            .to_string(),
            "Day 30 out of range for 2024-02"
        );
    }
}
