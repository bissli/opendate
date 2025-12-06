//! ISO 8601 datetime parser.
//!
//! Port of dateutil.parser.isoparser to Rust.

use super::errors::ParserError;
use super::result::ParseResult;

/// ISO parser with configurable separator.
pub struct IsoParser {
    /// Separator between date and time (default: any single non-numeric char)
    sep: Option<u8>,
}

impl Default for IsoParser {
    fn default() -> Self {
        Self::new()
    }
}

impl IsoParser {
    /// Create a new IsoParser with default settings (any separator).
    pub fn new() -> Self {
        IsoParser { sep: None }
    }

    /// Create a new IsoParser with a specific separator.
    pub fn with_separator(sep: char) -> Result<Self, ParserError> {
        if !sep.is_ascii() || sep.is_ascii_digit() {
            return Err(ParserError::ParseError(
                "Separator must be a single, non-numeric ASCII character".to_string(),
            ));
        }
        Ok(IsoParser {
            sep: Some(sep as u8),
        })
    }

    /// Parse an ISO-8601 datetime string.
    ///
    /// Returns a ParseResult with the parsed components.
    pub fn isoparse(&self, dt_str: &str) -> Result<ParseResult, ParserError> {
        let bytes = dt_str.as_bytes();
        if bytes.is_empty() {
            return Err(ParserError::EmptyString);
        }

        // Parse date portion
        let (mut result, pos) = self.parse_isodate_internal(bytes)?;

        // Check for time portion
        if pos < bytes.len() {
            let sep_byte = bytes[pos];
            // Check separator
            if self.sep.is_none() || Some(sep_byte) == self.sep {
                // Not a digit means it's a separator
                if !sep_byte.is_ascii_digit() {
                    let time_result = self.parse_isotime_internal(&bytes[pos + 1..])?;
                    result.hour = time_result.hour;
                    result.minute = time_result.minute;
                    result.second = time_result.second;
                    result.microsecond = time_result.microsecond;
                    result.tzoffset = time_result.tzoffset;
                    result.tzname = time_result.tzname;
                }
            } else {
                return Err(ParserError::ParseError(
                    "String contains unknown ISO components".to_string(),
                ));
            }
        }

        // Handle 24:00:00 midnight special case
        if result.hour == Some(24) {
            result.hour = Some(0);
            // Caller needs to add one day - we'll signal this via a flag or let Python handle it
            // For now, we just set hour to 0 and let the Python layer handle day increment
        }

        Ok(result)
    }

    /// Parse the date portion of an ISO string.
    pub fn parse_isodate(&self, datestr: &str) -> Result<ParseResult, ParserError> {
        let bytes = datestr.as_bytes();
        if bytes.is_empty() {
            return Err(ParserError::EmptyString);
        }

        let (result, pos) = self.parse_isodate_internal(bytes)?;
        if pos < bytes.len() {
            return Err(ParserError::ParseError(format!(
                "String contains unknown ISO components: {:?}",
                &datestr[pos..]
            )));
        }
        Ok(result)
    }

    /// Parse the time portion of an ISO string.
    pub fn parse_isotime(&self, timestr: &str) -> Result<ParseResult, ParserError> {
        let bytes = timestr.as_bytes();
        if bytes.is_empty() {
            return Err(ParserError::EmptyString);
        }

        let mut result = self.parse_isotime_internal(bytes)?;

        // Handle 24:00:00 midnight
        if result.hour == Some(24) {
            result.hour = Some(0);
        }

        Ok(result)
    }

    /// Parse timezone string.
    pub fn parse_tzstr(&self, tzstr: &str, zero_as_utc: bool) -> Result<Option<i32>, ParserError> {
        let bytes = tzstr.as_bytes();
        self.parse_tzstr_internal(bytes, zero_as_utc)
    }

    // Internal parsing methods

    fn parse_isodate_internal(&self, dt_str: &[u8]) -> Result<(ParseResult, usize), ParserError> {
        // Try common format first, then uncommon
        self.parse_isodate_common(dt_str)
            .or_else(|_| self.parse_isodate_uncommon(dt_str))
    }

    fn parse_isodate_common(&self, dt_str: &[u8]) -> Result<(ParseResult, usize), ParserError> {
        let len_str = dt_str.len();
        let mut result = ParseResult::new();

        if len_str < 4 {
            return Err(ParserError::ParseError("ISO string too short".to_string()));
        }

        // Year (always 4 digits)
        result.year = Some(parse_int(&dt_str[0..4])? as i32);
        result.century_specified = true;
        let mut pos = 4;

        if pos >= len_str {
            // Just YYYY
            result.month = Some(1);
            result.day = Some(1);
            return Ok((result, pos));
        }

        let has_sep = dt_str[pos] == b'-';
        if has_sep {
            pos += 1;
        }

        // Month
        if len_str - pos < 2 {
            return Err(ParserError::ParseError("Invalid common month".to_string()));
        }
        result.month = Some(parse_int(&dt_str[pos..pos + 2])?);
        pos += 2;

        if pos >= len_str {
            if has_sep {
                // YYYY-MM format
                result.day = Some(1);
                return Ok((result, pos));
            } else {
                // YYYYMM is not valid ISO format
                return Err(ParserError::ParseError("Invalid ISO format".to_string()));
            }
        }

        if has_sep {
            if dt_str[pos] != b'-' {
                return Err(ParserError::ParseError(
                    "Invalid separator in ISO string".to_string(),
                ));
            }
            pos += 1;
        }

        // Day
        if len_str - pos < 2 {
            return Err(ParserError::ParseError("Invalid common day".to_string()));
        }
        result.day = Some(parse_int(&dt_str[pos..pos + 2])?);
        pos += 2;

        Ok((result, pos))
    }

    fn parse_isodate_uncommon(&self, dt_str: &[u8]) -> Result<(ParseResult, usize), ParserError> {
        if dt_str.len() < 4 {
            return Err(ParserError::ParseError("ISO string too short".to_string()));
        }

        let year = parse_int(&dt_str[0..4])? as i32;
        let has_sep = dt_str.get(4) == Some(&b'-');
        let mut pos = 4 + if has_sep { 1 } else { 0 };

        if dt_str.get(pos) == Some(&b'W') {
            // Week date: YYYY-Www or YYYYWww or YYYY-Www-D or YYYYWwwD
            pos += 1;
            if dt_str.len() < pos + 2 {
                return Err(ParserError::ParseError("Invalid week number".to_string()));
            }

            let weekno = parse_int(&dt_str[pos..pos + 2])? as i32;
            pos += 2;

            let mut dayno = 1i32;
            if dt_str.len() > pos {
                let day_has_sep = dt_str.get(pos) == Some(&b'-');
                if day_has_sep != has_sep {
                    return Err(ParserError::ParseError(
                        "Inconsistent use of dash separator".to_string(),
                    ));
                }
                if day_has_sep {
                    pos += 1;
                }
                if pos < dt_str.len() && dt_str[pos].is_ascii_digit() {
                    dayno = (dt_str[pos] - b'0') as i32;
                    pos += 1;
                }
            }

            let (y, m, d) = calculate_weekdate(year, weekno, dayno)?;
            let mut result = ParseResult::new();
            result.year = Some(y);
            result.month = Some(m);
            result.day = Some(d);
            result.century_specified = true;
            return Ok((result, pos));
        }

        // Ordinal date: YYYY-DDD or YYYYDDD
        if dt_str.len() - pos < 3 {
            return Err(ParserError::ParseError("Invalid ordinal day".to_string()));
        }

        let ordinal_day = parse_int(&dt_str[pos..pos + 3])? as i32;
        pos += 3;

        let days_in_year = if is_leap_year(year) { 366 } else { 365 };
        if ordinal_day < 1 || ordinal_day > days_in_year {
            return Err(ParserError::ParseError(format!(
                "Invalid ordinal day {} for year {}",
                ordinal_day, year
            )));
        }

        let (m, d) = ordinal_to_month_day(year, ordinal_day)?;
        let mut result = ParseResult::new();
        result.year = Some(year);
        result.month = Some(m);
        result.day = Some(d);
        result.century_specified = true;
        Ok((result, pos))
    }

    fn parse_isotime_internal(&self, timestr: &[u8]) -> Result<ParseResult, ParserError> {
        let len_str = timestr.len();
        let mut result = ParseResult::new();
        result.hour = Some(0);
        result.minute = Some(0);
        result.second = Some(0);
        result.microsecond = Some(0);

        let mut pos = 0;
        let mut comp: i32 = -1; // Will be incremented to 0 at start of first iteration

        if len_str < 2 {
            return Err(ParserError::ParseError("ISO time too short".to_string()));
        }

        let mut has_sep = false;

        while pos < len_str && comp < 4 {
            comp += 1;

            // Check for timezone boundary
            if let Some(&b) = timestr.get(pos) {
                if b == b'-' || b == b'+' || b == b'Z' || b == b'z' {
                    let tz_offset = self.parse_tzstr_internal(&timestr[pos..], true)?;
                    result.tzoffset = tz_offset;
                    if tz_offset == Some(0) {
                        result.tzname = Some("UTC".to_string());
                    }
                    pos = len_str;
                    break;
                }
            }

            // Handle separator after hour (before minute)
            if comp == 1 {
                if let Some(&b) = timestr.get(pos) {
                    if b == b':' {
                        has_sep = true;
                        pos += 1;
                    }
                }
            }
            // Handle separator after minute (before second)
            else if comp == 2 && has_sep {
                if let Some(&b) = timestr.get(pos) {
                    if b != b':' {
                        return Err(ParserError::ParseError(
                            "Inconsistent use of colon separator".to_string(),
                        ));
                    }
                    pos += 1;
                }
            }

            if comp < 3 {
                // Hour, minute, second
                if pos + 2 > len_str {
                    // Not enough characters - this might be end of string or timezone
                    break;
                }
                // Check if next chars are digits
                if !timestr[pos].is_ascii_digit() {
                    break;
                }
                let value = parse_int(&timestr[pos..pos + 2])?;
                match comp {
                    0 => result.hour = Some(value),
                    1 => result.minute = Some(value),
                    2 => result.second = Some(value),
                    _ => {}
                }
                pos += 2;
            } else if comp == 3 {
                // Fraction of a second
                if let Some(&b) = timestr.get(pos) {
                    if b == b'.' || b == b',' {
                        pos += 1;
                        let frac_start = pos;
                        while pos < len_str && timestr[pos].is_ascii_digit() {
                            pos += 1;
                        }
                        if pos > frac_start {
                            let frac_str = &timestr[frac_start..pos.min(frac_start + 6)];
                            let frac_len = frac_str.len();
                            let us = parse_int(frac_str)? * 10u32.pow(6 - frac_len as u32);
                            result.microsecond = Some(us);
                        }
                    }
                }
            }
        }

        // Validate 24:00:00 midnight
        if result.hour == Some(24) {
            if result.minute != Some(0) || result.second != Some(0) || result.microsecond != Some(0)
            {
                return Err(ParserError::ParseError(
                    "Hour may only be 24 at 24:00:00.000".to_string(),
                ));
            }
        }

        Ok(result)
    }

    fn parse_tzstr_internal(
        &self,
        tzstr: &[u8],
        zero_as_utc: bool,
    ) -> Result<Option<i32>, ParserError> {
        if tzstr.is_empty() {
            return Ok(None);
        }

        // Z or z
        if tzstr == b"Z" || tzstr == b"z" {
            return Ok(Some(0));
        }

        let len = tzstr.len();
        if len != 3 && len != 5 && len != 6 {
            return Err(ParserError::InvalidTimezone(format!(
                "Time zone offset must be 1, 3, 5 or 6 characters, got {}",
                len
            )));
        }

        let mult: i32 = match tzstr[0] {
            b'-' => -1,
            b'+' => 1,
            _ => {
                return Err(ParserError::InvalidTimezone(
                    "Time zone offset requires sign".to_string(),
                ))
            }
        };

        let hours = parse_int(&tzstr[1..3])? as i32;
        let minutes = if len == 3 {
            0
        } else if tzstr[3] == b':' {
            // ±HH:MM
            parse_int(&tzstr[4..])? as i32
        } else {
            // ±HHMM
            parse_int(&tzstr[3..])? as i32
        };

        if hours > 23 {
            return Err(ParserError::InvalidTimezone(
                "Invalid hours in time zone offset".to_string(),
            ));
        }
        if minutes > 59 {
            return Err(ParserError::InvalidTimezone(
                "Invalid minutes in time zone offset".to_string(),
            ));
        }

        let offset_seconds = mult * (hours * 3600 + minutes * 60);

        if zero_as_utc && offset_seconds == 0 {
            Ok(Some(0))
        } else {
            Ok(Some(offset_seconds))
        }
    }
}

// Helper functions

fn parse_int(bytes: &[u8]) -> Result<u32, ParserError> {
    let s = std::str::from_utf8(bytes)
        .map_err(|_| ParserError::ParseError("Invalid UTF-8".to_string()))?;
    s.parse::<u32>()
        .map_err(|_| ParserError::ParseError(format!("Invalid integer: {}", s)))
}

fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}

fn days_in_month(year: i32, month: u32) -> u32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            if is_leap_year(year) {
                29
            } else {
                28
            }
        }
        _ => 0,
    }
}

fn ordinal_to_month_day(year: i32, ordinal: i32) -> Result<(u32, u32), ParserError> {
    let mut remaining = ordinal;
    for month in 1..=12 {
        let days = days_in_month(year, month) as i32;
        if remaining <= days {
            return Ok((month, remaining as u32));
        }
        remaining -= days;
    }
    Err(ParserError::ParseError(format!(
        "Invalid ordinal day {}",
        ordinal
    )))
}

/// Calculate the date from ISO year-week-day.
fn calculate_weekdate(year: i32, week: i32, day: i32) -> Result<(i32, u32, u32), ParserError> {
    if week < 1 || week > 53 {
        return Err(ParserError::ParseError(format!("Invalid week: {}", week)));
    }
    if day < 1 || day > 7 {
        return Err(ParserError::ParseError(format!(
            "Invalid weekday: {}",
            day
        )));
    }

    // Find January 4th of the given year (always in week 1)
    // January 4th's day of week tells us where week 1 starts
    let jan_4_dow = day_of_week(year, 1, 4); // 0=Monday, 6=Sunday

    // Week 1, day 1 (Monday) is jan_4 - jan_4_dow days
    // Then we add (week-1)*7 + (day-1) days
    let days_from_jan4 = -(jan_4_dow as i32) + (week - 1) * 7 + (day - 1);

    // Start from January 4
    let mut y = year;
    let mut m = 1u32;
    let mut d = 4i32 + days_from_jan4;

    // Normalize the date
    while d < 1 {
        // Go to previous month
        if m == 1 {
            m = 12;
            y -= 1;
        } else {
            m -= 1;
        }
        d += days_in_month(y, m) as i32;
    }

    while d > days_in_month(y, m) as i32 {
        d -= days_in_month(y, m) as i32;
        if m == 12 {
            m = 1;
            y += 1;
        } else {
            m += 1;
        }
    }

    Ok((y, m, d as u32))
}

/// Calculate day of week (0=Monday, 6=Sunday) using Zeller's congruence variant.
fn day_of_week(year: i32, month: u32, day: u32) -> u32 {
    // Adjust for January and February
    let (y, m) = if month <= 2 {
        (year - 1, month + 12)
    } else {
        (year, month)
    };

    let q = day as i32;
    let k = y % 100;
    let j = y / 100;

    // Zeller's formula for Gregorian calendar
    let h = (q + (13 * (m as i32 + 1)) / 5 + k + k / 4 + j / 4 - 2 * j) % 7;

    // Convert from Zeller's (0=Saturday) to ISO (0=Monday)
    ((h + 5) % 7) as u32
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_iso_date() {
        let parser = IsoParser::new();

        // YYYY-MM-DD
        let r = parser.parse_isodate("2024-01-15").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(15));

        // YYYYMMDD
        let r = parser.parse_isodate("20240115").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(15));

        // YYYY-MM
        let r = parser.parse_isodate("2024-01").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));

        // YYYY
        let r = parser.parse_isodate("2024").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));
    }

    #[test]
    fn test_parse_iso_datetime() {
        let parser = IsoParser::new();

        let r = parser.isoparse("2024-01-15T10:30:00").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(15));
        assert_eq!(r.hour, Some(10));
        assert_eq!(r.minute, Some(30));
        assert_eq!(r.second, Some(0));
    }

    #[test]
    fn test_parse_iso_time() {
        let parser = IsoParser::new();

        let r = parser.parse_isotime("14:30:45").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(30));
        assert_eq!(r.second, Some(45));

        let r = parser.parse_isotime("14:30").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(30));
        assert_eq!(r.second, Some(0));

        let r = parser.parse_isotime("14").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(0));
    }

    #[test]
    fn test_parse_iso_time_with_microseconds() {
        let parser = IsoParser::new();

        let r = parser.parse_isotime("14:30:45.123456").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(30));
        assert_eq!(r.second, Some(45));
        assert_eq!(r.microsecond, Some(123456));

        // Shorter fractions
        let r = parser.parse_isotime("14:30:45.123").unwrap();
        assert_eq!(r.microsecond, Some(123000));

        // Comma separator
        let r = parser.parse_isotime("14:30:45,5").unwrap();
        assert_eq!(r.microsecond, Some(500000));
    }

    #[test]
    fn test_parse_iso_timezone() {
        let parser = IsoParser::new();

        // UTC
        let r = parser.isoparse("2024-01-15T10:30:00Z").unwrap();
        assert_eq!(r.tzoffset, Some(0));

        // Positive offset
        let r = parser.isoparse("2024-01-15T10:30:00+05:30").unwrap();
        assert_eq!(r.tzoffset, Some(5 * 3600 + 30 * 60));

        // Negative offset
        let r = parser.isoparse("2024-01-15T10:30:00-05:00").unwrap();
        assert_eq!(r.tzoffset, Some(-5 * 3600));

        // Compact offset
        let r = parser.isoparse("2024-01-15T10:30:00+0530").unwrap();
        assert_eq!(r.tzoffset, Some(5 * 3600 + 30 * 60));

        // Hour only offset
        let r = parser.isoparse("2024-01-15T10:30:00-05").unwrap();
        assert_eq!(r.tzoffset, Some(-5 * 3600));
    }

    #[test]
    fn test_parse_ordinal_date() {
        let parser = IsoParser::new();

        // 2024-001 = January 1
        let r = parser.parse_isodate("2024-001").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));

        // 2024-032 = February 1
        let r = parser.parse_isodate("2024-032").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(2));
        assert_eq!(r.day, Some(1));

        // 2024-366 (leap year)
        let r = parser.parse_isodate("2024-366").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(12));
        assert_eq!(r.day, Some(31));
    }

    #[test]
    fn test_parse_week_date() {
        let parser = IsoParser::new();

        // 2024-W01-1 = Monday of week 1, 2024
        let r = parser.parse_isodate("2024-W01-1").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));

        // Compact form
        let r = parser.parse_isodate("2024W011").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));
    }

    #[test]
    fn test_midnight_24() {
        let parser = IsoParser::new();

        // 24:00:00 should be normalized to 00:00:00
        let r = parser.parse_isotime("24:00:00").unwrap();
        assert_eq!(r.hour, Some(0));
        assert_eq!(r.minute, Some(0));
        assert_eq!(r.second, Some(0));
    }

    #[test]
    fn test_day_of_week() {
        // 2024-01-01 is Monday (0)
        assert_eq!(day_of_week(2024, 1, 1), 0);
        // 2024-01-07 is Sunday (6)
        assert_eq!(day_of_week(2024, 1, 7), 6);
        // 2024-01-04 is Thursday (3)
        assert_eq!(day_of_week(2024, 1, 4), 3);
    }

    #[test]
    fn test_leap_year() {
        assert!(is_leap_year(2024));
        assert!(!is_leap_year(2023));
        assert!(is_leap_year(2000));
        assert!(!is_leap_year(1900));
    }
}
