#![allow(clippy::useless_conversion)]

use once_cell::sync::Lazy;
use pyo3::prelude::*;

use crate::calendar;
use crate::parser::{IsoParser, Parser, PyParseResult};

/// Static default parser instance - avoids recreating HashMaps on every parse() call.
static DEFAULT_PARSER: Lazy<Parser> = Lazy::new(Parser::default);

/// Static ISO parser instance.
static DEFAULT_ISO_PARSER: Lazy<IsoParser> = Lazy::new(IsoParser::new);

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

/// Python wrapper for IsoParser.
#[pyclass(name = "IsoParser")]
pub struct PyIsoParser {
    inner: IsoParser,
}

#[pymethods]
impl PyIsoParser {
    #[new]
    #[pyo3(signature = (sep=None))]
    fn new(sep: Option<char>) -> PyResult<Self> {
        let inner = match sep {
            Some(s) => IsoParser::with_separator(s)?,
            None => IsoParser::new(),
        };
        Ok(PyIsoParser { inner })
    }

    /// Parse an ISO-8601 datetime string.
    fn isoparse(&self, dt_str: &str) -> PyResult<PyParseResult> {
        let result = self.inner.isoparse(dt_str)?;
        Ok(result.into())
    }

    /// Parse the date portion of an ISO string.
    fn parse_isodate(&self, datestr: &str) -> PyResult<PyParseResult> {
        let result = self.inner.parse_isodate(datestr)?;
        Ok(result.into())
    }

    /// Parse the time portion of an ISO string.
    fn parse_isotime(&self, timestr: &str) -> PyResult<PyParseResult> {
        let result = self.inner.parse_isotime(timestr)?;
        Ok(result.into())
    }
}

/// Parse an ISO-8601 datetime string (convenience function).
#[pyfunction]
fn isoparse(dt_str: &str) -> PyResult<PyParseResult> {
    // Use static ISO parser instance
    let result = DEFAULT_ISO_PARSER.isoparse(dt_str)?;
    Ok(result.into())
}

/// Python wrapper for the general datetime parser.
#[pyclass(name = "Parser")]
pub struct PyParser {
    inner: Parser,
}

#[pymethods]
impl PyParser {
    #[new]
    #[pyo3(signature = (dayfirst=false, yearfirst=false))]
    fn new(dayfirst: bool, yearfirst: bool) -> Self {
        PyParser {
            inner: Parser::new(dayfirst, yearfirst),
        }
    }

    /// Parse a datetime string.
    ///
    /// # Arguments
    /// * `timestr` - The datetime string to parse
    /// * `dayfirst` - Override dayfirst setting (None = use default)
    /// * `yearfirst` - Override yearfirst setting (None = use default)
    /// * `fuzzy` - Whether to allow fuzzy parsing
    /// * `fuzzy_with_tokens` - If true, return skipped tokens tuple
    #[pyo3(signature = (timestr, dayfirst=None, yearfirst=None, fuzzy=false, fuzzy_with_tokens=false))]
    fn parse(
        &self,
        timestr: &str,
        dayfirst: Option<bool>,
        yearfirst: Option<bool>,
        fuzzy: bool,
        fuzzy_with_tokens: bool,
    ) -> PyResult<PyParseResultOrTuple> {
        let (result, tokens) =
            self.inner
                .parse(timestr, dayfirst, yearfirst, fuzzy, fuzzy_with_tokens)?;

        if fuzzy_with_tokens {
            Ok(PyParseResultOrTuple::WithTokens(
                result.into(),
                tokens.unwrap_or_default(),
            ))
        } else {
            Ok(PyParseResultOrTuple::Result(result.into()))
        }
    }
}

/// Return type for parse() - either ParseResult or (ParseResult, tokens).
pub enum PyParseResultOrTuple {
    Result(PyParseResult),
    WithTokens(PyParseResult, Vec<String>),
}

impl IntoPy<PyObject> for PyParseResultOrTuple {
    fn into_py(self, py: Python<'_>) -> PyObject {
        match self {
            PyParseResultOrTuple::Result(r) => r.into_py(py),
            PyParseResultOrTuple::WithTokens(r, tokens) => (r, tokens).into_py(py),
        }
    }
}

/// Parse a datetime string (convenience function).
#[pyfunction]
#[pyo3(signature = (timestr, dayfirst=None, yearfirst=None, fuzzy=false, fuzzy_with_tokens=false))]
fn parse(
    timestr: &str,
    dayfirst: Option<bool>,
    yearfirst: Option<bool>,
    fuzzy: bool,
    fuzzy_with_tokens: bool,
) -> PyResult<PyParseResultOrTuple> {
    // Use static default parser to avoid HashMap recreation on every call
    let (result, tokens) =
        DEFAULT_PARSER.parse(timestr, dayfirst, yearfirst, fuzzy, fuzzy_with_tokens)?;

    if fuzzy_with_tokens {
        Ok(PyParseResultOrTuple::WithTokens(
            result.into(),
            tokens.unwrap_or_default(),
        ))
    } else {
        Ok(PyParseResultOrTuple::Result(result.into()))
    }
}

/// Parse a standalone time string (convenience function).
///
/// Handles formats:
/// - HHMM: "0930" → 09:30
/// - HHMMSS: "093015" → 09:30:15
/// - HHMMSS with fraction: "093015.751" or "093015,751"
/// - Separated: "9:30", "9.30", "9:30:15", "9.30.15"
/// - With AM/PM: "0930 PM", "9:30 AM", "12:00 PM"
///
/// Returns None for invalid inputs.
#[pyfunction]
fn parse_time(timestr: &str) -> PyResult<Option<PyParseResult>> {
    match DEFAULT_PARSER.parse_time_only(timestr) {
        Ok(result) => Ok(Some(result.into())),
        Err(_) => Ok(None),
    }
}

#[pymodule]
pub fn _opendate(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBusinessCalendar>()?;
    m.add_class::<PyParseResult>()?;
    m.add_class::<PyIsoParser>()?;
    m.add_class::<PyParser>()?;
    m.add_function(wrap_pyfunction!(isoparse, m)?)?;
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_function(wrap_pyfunction!(parse_time, m)?)?;
    Ok(())
}
