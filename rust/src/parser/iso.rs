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
    ///
    /// # Errors
    ///
    /// `ParserError::ParseError` when `sep` is non-ASCII or a digit.
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
    /// # Arguments
    ///
    /// * `dt_str` - A date in any form `parse_isodate` takes, then
    ///   optionally one separator byte and a time in any form
    ///   `parse_isotime` takes.
    ///
    /// # Returns
    ///
    /// The parsed components. A time of `24:00` comes back as hour 0 on
    /// the next day. Where the date is outside the calendar (year 0, a
    /// month outside 1-12, day 0 or a day past the month's end), the hour
    /// is still 0 and the date fields stay as parsed.
    ///
    /// # Errors
    ///
    /// * `ParserError::EmptyString` - `dt_str` is empty.
    /// * `ParserError::ParseError` - a malformed date or time, a separator
    ///   other than the configured one, or text other than spaces and tabs
    ///   after the time.
    /// * `ParserError::InvalidTimezone` - a malformed UTC offset.
    pub fn isoparse(&self, dt_str: &str) -> Result<ParseResult, ParserError> {
        let bytes = dt_str.as_bytes();
        let len = bytes.len();
        if len == 0 {
            return Err(ParserError::EmptyString);
        }

        let (mut result, pos) = self.parse_isodate_internal(bytes)?;

        if pos < len {
            let sep_byte = bytes[pos];
            if self.sep.is_none() || Some(sep_byte) == self.sep {
                let time_start = pos + 1;
                let time_len = len - time_start;
                let (time_result, time_pos) =
                    self.parse_isotime_internal_slice(bytes, time_start, time_len)?;
                result.hour = time_result.hour;
                result.minute = time_result.minute;
                result.second = time_result.second;
                result.microsecond = time_result.microsecond;
                result.tzoffset = time_result.tzoffset;
                result.tzname = time_result.tzname;

                let consumed = time_start + time_pos;
                if consumed < len {
                    let mut all_whitespace = true;
                    let mut i = consumed;
                    while i < len {
                        if bytes[i] != b' ' && bytes[i] != b'\t' {
                            all_whitespace = false;
                            break;
                        }
                        i += 1;
                    }
                    if !all_whitespace {
                        return Err(ParserError::ParseError(format!(
                            "String contains unknown ISO components: {:?}",
                            slice_to_str(bytes, consumed, len)
                        )));
                    }
                }
            } else {
                return Err(ParserError::ParseError(
                    "String contains unknown ISO components".to_string(),
                ));
            }
        }

        if result.hour == Some(24) {
            result.hour = Some(0);
            if let (Some(year @ 1..), Some(month @ 1..=12), Some(day @ 1..)) =
                (result.year, result.month, result.day)
            {
                let month_days = days_in_month(year, month);
                if day < month_days {
                    result.day = Some(day + 1);
                } else if day == month_days && month == 12 {
                    result.year = Some(year + 1);
                    result.month = Some(1);
                    result.day = Some(1);
                } else if day == month_days {
                    result.month = Some(month + 1);
                    result.day = Some(1);
                }
            }
        }

        Ok(result)
    }

    /// Parse the date portion of an ISO string.
    ///
    /// # Arguments
    ///
    /// * `datestr` - `YYYY`, `YYYY-MM`, `YYYY-MM-DD` or `YYYYMMDD`; a week
    ///   date `YYYY-Www[-D]` or `YYYYWww[D]`; or an ordinal date
    ///   `YYYY-DDD` or `YYYYDDD`. A missing month, day or weekday is 1.
    ///
    /// # Errors
    ///
    /// * `ParserError::EmptyString` - `datestr` is empty.
    /// * `ParserError::ParseError` - a malformed date, or any text after it.
    pub fn parse_isodate(&self, datestr: &str) -> Result<ParseResult, ParserError> {
        let bytes = datestr.as_bytes();
        let len = bytes.len();
        if len == 0 {
            return Err(ParserError::EmptyString);
        }

        let (result, pos) = self.parse_isodate_internal(bytes)?;
        if pos < len {
            return Err(ParserError::ParseError(format!(
                "String contains unknown ISO components: {:?}",
                slice_to_str(bytes, pos, len)
            )));
        }
        Ok(result)
    }

    /// Parse the time portion of an ISO string.
    ///
    /// # Arguments
    ///
    /// * `timestr` - `HH`, `HH:MM` or `HHMM`, or `HH:MM:SS` or `HHMMSS`
    ///   with an optional `.` or `,` fraction of a second, then an
    ///   optional `Z`, `+HH`, `+HHMM` or `+HH:MM` offset (or `-`).
    ///   Fraction digits past the sixth are dropped, never rounded.
    ///
    /// # Returns
    ///
    /// The parsed components, with an absent minute, second or
    /// microsecond as 0. `24:00` comes back as hour 0.
    ///
    /// # Errors
    ///
    /// * `ParserError::EmptyString` - `timestr` is empty.
    /// * `ParserError::ParseError` - a malformed time, hour 24 with a
    ///   nonzero part, or text other than spaces and tabs after the time.
    /// * `ParserError::InvalidTimezone` - a malformed UTC offset.
    pub fn parse_isotime(&self, timestr: &str) -> Result<ParseResult, ParserError> {
        let bytes = timestr.as_bytes();
        let len = bytes.len();
        if len == 0 {
            return Err(ParserError::EmptyString);
        }

        let (mut result, pos) = self.parse_isotime_internal_slice(bytes, 0, len)?;

        if pos < len {
            let mut all_whitespace = true;
            let mut i = pos;
            while i < len {
                if bytes[i] != b' ' && bytes[i] != b'\t' {
                    all_whitespace = false;
                    break;
                }
                i += 1;
            }
            if !all_whitespace {
                return Err(ParserError::ParseError(format!(
                    "String contains unknown ISO components: {:?}",
                    slice_to_str(bytes, pos, len)
                )));
            }
        }

        if result.hour == Some(24) {
            result.hour = Some(0);
        }

        Ok(result)
    }

    /// Parse timezone string.
    ///
    /// # Arguments
    ///
    /// * `tzstr` - `Z`, `z`, `+HH`, `+HHMM` or `+HH:MM` (or `-`).
    /// * `zero_as_utc` - Has no effect: a zero offset gives `Some(0)`
    ///   either way.
    ///
    /// # Returns
    ///
    /// The offset in seconds east of UTC, or `None` for an empty string.
    ///
    /// # Errors
    ///
    /// * `ParserError::InvalidTimezone` - a wrong length, a missing sign,
    ///   hours above 23 or minutes above 59.
    /// * `ParserError::ParseError` - a non-digit where a digit belongs.
    #[allow(dead_code)]
    pub fn parse_tzstr(&self, tzstr: &str, zero_as_utc: bool) -> Result<Option<i32>, ParserError> {
        let bytes = tzstr.as_bytes();
        let len = bytes.len();
        self.parse_tzstr_internal_slice(bytes, 0, len, zero_as_utc)
    }

    // Internal parsing methods

    /// Parse a date at the start of `dt_str` and count the bytes it took.
    fn parse_isodate_internal(&self, dt_str: &[u8]) -> Result<(ParseResult, usize), ParserError> {
        match self.parse_isodate_common(dt_str) {
            Ok(r) => Ok(r),
            Err(_) => self.parse_isodate_uncommon(dt_str),
        }
    }

    /// Parse a calendar date at the start of `dt_str` and count the bytes
    /// it took.
    fn parse_isodate_common(&self, dt_str: &[u8]) -> Result<(ParseResult, usize), ParserError> {
        let len_str = dt_str.len();
        let mut result = ParseResult::new();

        if len_str < 4 {
            return Err(ParserError::ParseError("ISO string too short".to_string()));
        }

        result.year = Some(parse_int_slice(dt_str, 0, 4)? as i32);
        result.century_specified = true;
        let mut pos = 4usize;

        if pos >= len_str {
            result.month = Some(1);
            result.day = Some(1);
            return Ok((result, pos));
        }

        let has_sep = dt_str[pos] == b'-';
        if has_sep {
            pos += 1;
        }

        if len_str - pos < 2 {
            return Err(ParserError::ParseError("Invalid common month".to_string()));
        }
        result.month = Some(parse_int_slice(dt_str, pos, pos + 2)?);
        pos += 2;

        if pos >= len_str {
            if has_sep {
                result.day = Some(1);
                return Ok((result, pos));
            } else {
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

        if len_str - pos < 2 {
            return Err(ParserError::ParseError("Invalid common day".to_string()));
        }
        result.day = Some(parse_int_slice(dt_str, pos, pos + 2)?);
        pos += 2;

        Ok((result, pos))
    }

    /// Parse a week or ordinal date at the start of `dt_str` and count the
    /// bytes it took.
    fn parse_isodate_uncommon(&self, dt_str: &[u8]) -> Result<(ParseResult, usize), ParserError> {
        let len_str = dt_str.len();
        if len_str < 4 {
            return Err(ParserError::ParseError("ISO string too short".to_string()));
        }

        let year = parse_int_slice(dt_str, 0, 4)? as i32;
        let has_sep = if len_str > 4 {
            dt_str[4] == b'-'
        } else {
            false
        };
        let mut pos = 4 + if has_sep { 1 } else { 0 };

        if pos < len_str && dt_str[pos] == b'W' {
            pos += 1;
            if len_str < pos + 2 {
                return Err(ParserError::ParseError("Invalid week number".to_string()));
            }

            let weekno = parse_int_slice(dt_str, pos, pos + 2)? as i32;
            pos += 2;

            let mut dayno = 1i32;
            if len_str > pos {
                let next_byte = dt_str[pos];
                if next_byte == b'T' || next_byte == b' ' || next_byte == b't' {
                    // No day, just time separator - leave dayno as 1
                    // (Monday)
                } else {
                    let day_has_sep = next_byte == b'-';
                    if day_has_sep != has_sep {
                        return Err(ParserError::ParseError(
                            "Inconsistent use of dash separator".to_string(),
                        ));
                    }
                    if day_has_sep {
                        pos += 1;
                    }
                    if pos < len_str && is_ascii_digit(dt_str[pos]) {
                        dayno = (dt_str[pos] - b'0') as i32;
                        pos += 1;
                    }
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

        if len_str - pos < 3 {
            return Err(ParserError::ParseError("Invalid ordinal day".to_string()));
        }

        let ordinal_day = parse_int_slice(dt_str, pos, pos + 3)? as i32;
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

    /// Parse a time in `timestr[start..start + len]`.
    ///
    /// # Returns
    ///
    /// The time, with hour 24 kept as 24, and the bytes it took counted
    /// from `start`.
    fn parse_isotime_internal_slice(
        &self,
        timestr: &[u8],
        start: usize,
        len: usize,
    ) -> Result<(ParseResult, usize), ParserError> {
        let end = start + len;
        let mut result = ParseResult::new();
        result.hour = Some(0);
        result.minute = Some(0);
        result.second = Some(0);
        result.microsecond = Some(0);

        let mut pos = start;
        let mut comp: i32 = -1;

        if len < 2 {
            return Err(ParserError::ParseError("ISO time too short".to_string()));
        }

        let mut has_sep = false;

        while pos < end && comp < 4 {
            comp += 1;

            if pos < end {
                let b = timestr[pos];
                if b == b'-' || b == b'+' || b == b'Z' || b == b'z' {
                    let tz_len = end - pos;
                    let tz_offset = self.parse_tzstr_internal_slice(timestr, pos, tz_len, true)?;
                    result.tzoffset = tz_offset;
                    if tz_offset == Some(0) {
                        result.tzname = Some("UTC".to_string());
                    }
                    pos = end;
                    break;
                }
            }

            if comp == 1 {
                if pos < end && timestr[pos] == b':' {
                    has_sep = true;
                    pos += 1;
                }
            } else if comp == 2 && has_sep {
                if pos < end {
                    if timestr[pos] == b':' {
                        pos += 1;
                    } else {
                        break;
                    }
                }
            }

            if comp < 3 {
                if pos + 2 > end {
                    break;
                }
                if !is_ascii_digit(timestr[pos]) {
                    break;
                }
                let value = parse_int_slice(timestr, pos, pos + 2)?;
                match comp {
                    0 => result.hour = Some(value),
                    1 => result.minute = Some(value),
                    2 => result.second = Some(value),
                    _ => {}
                }
                pos += 2;
            } else if comp == 3 {
                if pos < end {
                    let b = timestr[pos];
                    if b == b'.' || b == b',' {
                        pos += 1;
                        let frac_start = pos;
                        while pos < end && is_ascii_digit(timestr[pos]) {
                            pos += 1;
                        }
                        if pos > frac_start {
                            let frac_end = if pos - frac_start > 6 {
                                frac_start + 6
                            } else {
                                pos
                            };
                            let frac_len = frac_end - frac_start;
                            let frac_val = parse_int_slice(timestr, frac_start, frac_end)?;
                            let mut multiplier = 1u32;
                            let mut k = 0usize;
                            while k < (6 - frac_len) {
                                multiplier *= 10;
                                k += 1;
                            }
                            let us = frac_val * multiplier;
                            result.microsecond = Some(us);
                        }
                    }
                }
            }
        }

        if result.hour == Some(24)
            && (result.minute != Some(0)
                || result.second != Some(0)
                || result.microsecond != Some(0))
        {
            return Err(ParserError::ParseError(
                "Hour may only be 24 at 24:00:00.000".to_string(),
            ));
        }

        Ok((result, pos - start))
    }

    /// Parse a UTC offset in `tzstr[start..start + len]`, as `parse_tzstr`
    /// does.
    fn parse_tzstr_internal_slice(
        &self,
        tzstr: &[u8],
        start: usize,
        len: usize,
        zero_as_utc: bool,
    ) -> Result<Option<i32>, ParserError> {
        if len == 0 {
            return Ok(None);
        }

        if len == 1 && (tzstr[start] == b'Z' || tzstr[start] == b'z') {
            return Ok(Some(0));
        }

        if len != 3 && len != 5 && len != 6 {
            return Err(ParserError::InvalidTimezone(format!(
                "Time zone offset must be 1, 3, 5 or 6 characters, got {}",
                len
            )));
        }

        let mult: i32 = match tzstr[start] {
            b'-' => -1,
            b'+' => 1,
            _ => {
                return Err(ParserError::InvalidTimezone(
                    "Time zone offset requires sign".to_string(),
                ))
            }
        };

        let hours = parse_int_slice(tzstr, start + 1, start + 3)? as i32;
        let minutes = if len == 3 {
            0
        } else if tzstr[start + 3] == b':' {
            parse_int_slice(tzstr, start + 4, start + len)? as i32
        } else {
            parse_int_slice(tzstr, start + 3, start + len)? as i32
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

/// True for a byte in `b'0'..=b'9'`.
fn is_ascii_digit(b: u8) -> bool {
    b >= b'0' && b <= b'9'
}

/// Parse the unsigned decimal digits in `bytes[start..end]`. An empty
/// range gives 0.
fn parse_int_slice(bytes: &[u8], start: usize, end: usize) -> Result<u32, ParserError> {
    let mut result = 0u32;
    let mut i = start;
    while i < end {
        let b = bytes[i];
        if b >= b'0' && b <= b'9' {
            result = result * 10 + (b - b'0') as u32;
        } else {
            return Err(ParserError::ParseError(format!(
                "Invalid integer: {:?}",
                slice_to_str(bytes, start, end)
            )));
        }
        i += 1;
    }
    Ok(result)
}

/// Copy `bytes[start..end]` into a String, one char per byte.
fn slice_to_str(bytes: &[u8], start: usize, end: usize) -> String {
    let len = end - start;
    let mut result = String::with_capacity(len);
    let mut i = start;
    while i < end {
        result.push(bytes[i] as char);
        i += 1;
    }
    result
}

/// True for a Gregorian leap year.
fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}

/// Days in `month` of `year`. An out-of-range month gives 0.
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

/// Month and day of a 1-based day of the year.
///
/// # Errors
///
/// `ParserError::ParseError` when `ordinal` falls past the year's end.
fn ordinal_to_month_day(year: i32, ordinal: i32) -> Result<(u32, u32), ParserError> {
    let mut remaining = ordinal;
    let mut month = 1u32;
    while month <= 12 {
        let days = days_in_month(year, month) as i32;
        if remaining <= days {
            return Ok((month, remaining as u32));
        }
        remaining -= days;
        month += 1;
    }
    Err(ParserError::ParseError(format!(
        "Invalid ordinal day {}",
        ordinal
    )))
}

/// Calculate the date from ISO year-week-day, where week 1 is the week
/// that holds January 4.
///
/// # Errors
///
/// `ParserError::ParseError` when `week` is outside 1-53 or `day` is
/// outside 1-7.
fn calculate_weekdate(year: i32, week: i32, day: i32) -> Result<(i32, u32, u32), ParserError> {
    if week < 1 || week > 53 {
        return Err(ParserError::ParseError(format!("Invalid week: {}", week)));
    }
    if day < 1 || day > 7 {
        return Err(ParserError::ParseError(format!("Invalid weekday: {}", day)));
    }

    let jan_4_dow = day_of_week(year, 1, 4);
    let days_from_jan4 = -(jan_4_dow as i32) + (week - 1) * 7 + (day - 1);

    let mut y = year;
    let mut m = 1u32;
    let mut d = 4i32 + days_from_jan4;

    while d < 1 {
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

/// Calculate day of week (0=Monday, 6=Sunday) using Zeller's congruence
/// variant.
fn day_of_week(year: i32, month: u32, day: u32) -> u32 {
    let (y, m) = if month <= 2 {
        (year - 1, month + 12)
    } else {
        (year, month)
    };

    let q = day as i32;
    let k = y % 100;
    let j = y / 100;
    let h = (q + (13 * (m as i32 + 1)) / 5 + k + k / 4 + j / 4 - 2 * j) % 7;
    (h + 5).rem_euclid(7) as u32
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Verify each calendar date form, and day 1 or month 1 where absent.
    ///
    /// Mutation: dropping the day default in the `YYYY-MM` branch, or
    /// advancing past a dash that `YYYYMMDD` lacks.
    /// Oracle: hand-read components of each input.
    #[test]
    fn test_parse_iso_date() {
        let parser = IsoParser::new();

        let r = parser.parse_isodate("2024-01-15").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(15));

        let r = parser.parse_isodate("20240115").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(15));

        let r = parser.parse_isodate("2024-01").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));

        let r = parser.parse_isodate("2024").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));
    }

    /// Verify isoparse() joins a date and a time across the `T`.
    ///
    /// Mutation: starting the time at the separator byte instead of the
    /// byte after it.
    /// Oracle: hand-read components of the input.
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

    /// Verify hour, minute and second forms, with absent parts as 0.
    ///
    /// Mutation: not setting has_sep at the first colon, or leaving an
    /// absent second as None.
    /// Oracle: hand-read components of each input.
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

    /// Verify a fraction scales to microseconds after `.` or `,`.
    ///
    /// Mutation: dropping the power-of-ten scale for a fraction shorter
    /// than six digits, or accepting only `.`.
    /// Oracle: hand-computed .123 -> 123000 and ,5 -> 500000.
    #[test]
    fn test_parse_iso_time_with_microseconds() {
        let parser = IsoParser::new();

        let r = parser.parse_isotime("14:30:45.123456").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(30));
        assert_eq!(r.second, Some(45));
        assert_eq!(r.microsecond, Some(123456));

        let r = parser.parse_isotime("14:30:45.123").unwrap();
        assert_eq!(r.microsecond, Some(123000));

        let r = parser.parse_isotime("14:30:45,5").unwrap();
        assert_eq!(r.microsecond, Some(500000));
    }

    /// Verify each offset form converts to signed seconds east of UTC.
    ///
    /// Mutation: a flipped sign multiplier, or reading `+HHMM` minutes
    /// one byte late as for `+HH:MM`.
    /// Oracle: hand-computed seconds, 5:30 -> 19800.
    #[test]
    fn test_parse_iso_timezone() {
        let parser = IsoParser::new();

        let r = parser.isoparse("2024-01-15T10:30:00Z").unwrap();
        assert_eq!(r.tzoffset, Some(0));

        let r = parser.isoparse("2024-01-15T10:30:00+05:30").unwrap();
        assert_eq!(r.tzoffset, Some(5 * 3600 + 30 * 60));

        let r = parser.isoparse("2024-01-15T10:30:00-05:00").unwrap();
        assert_eq!(r.tzoffset, Some(-5 * 3600));

        let r = parser.isoparse("2024-01-15T10:30:00+0530").unwrap();
        assert_eq!(r.tzoffset, Some(5 * 3600 + 30 * 60));

        let r = parser.isoparse("2024-01-15T10:30:00-05").unwrap();
        assert_eq!(r.tzoffset, Some(-5 * 3600));
    }

    /// Verify ordinal days map to month and day, through day 366.
    ///
    /// Mutation: `<` for `<=` in ordinal_to_month_day, or a leap test
    /// that rejects 2024.
    /// Oracle: calendar, 2024-032 = Feb 1 and 2024-366 = Dec 31.
    #[test]
    fn test_parse_ordinal_date() {
        let parser = IsoParser::new();

        let r = parser.parse_isodate("2024-001").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));

        let r = parser.parse_isodate("2024-032").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(2));
        assert_eq!(r.day, Some(1));

        let r = parser.parse_isodate("2024-366").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(12));
        assert_eq!(r.day, Some(31));
    }

    /// Verify a week date, dashed and compact, lands on its Monday.
    ///
    /// Mutation: an off-by-one week 1 start from the January 4 weekday.
    /// Oracle: calendar, 2024-W01-1 = Monday 2024-01-01.
    #[test]
    fn test_parse_week_date() {
        let parser = IsoParser::new();

        let r = parser.parse_isodate("2024-W01-1").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));

        let r = parser.parse_isodate("2024W011").unwrap();
        assert_eq!(r.year, Some(2024));
        assert_eq!(r.month, Some(1));
        assert_eq!(r.day, Some(1));
    }

    /// Verify parse_isotime() returns 24:00:00 as hour 0.
    ///
    /// Mutation: dropping the hour 24 -> 0 step in parse_isotime.
    /// Oracle: the documented contract, hour 0 for 24:00:00.
    #[test]
    fn test_midnight_24() {
        let parser = IsoParser::new();

        let r = parser.parse_isotime("24:00:00").unwrap();
        assert_eq!(r.hour, Some(0));
        assert_eq!(r.minute, Some(0));
        assert_eq!(r.second, Some(0));
    }

    /// Verify day_of_week() numbers Monday 0 through Sunday 6.
    ///
    /// Mutation: a wrong Zeller-to-ISO shift, such as `h + 6` for `h + 5`.
    /// Oracle: calendar, 2024-01-01 Monday, 01-04 Thursday, 01-07 Sunday.
    #[test]
    fn test_day_of_week() {
        assert_eq!(day_of_week(2024, 1, 1), 0);
        assert_eq!(day_of_week(2024, 1, 7), 6);
        assert_eq!(day_of_week(2024, 1, 4), 3);
    }

    /// Verify is_leap_year() applies the century rules.
    ///
    /// Mutation: dropping the `% 100` or the `% 400` term.
    /// Oracle: Gregorian rule, 1900 common and 2000 leap.
    #[test]
    fn test_leap_year() {
        assert!(is_leap_year(2024));
        assert!(!is_leap_year(2023));
        assert!(is_leap_year(2000));
        assert!(!is_leap_year(1900));
    }

    /// Verify parse_isotime() rejects a stray trailing digit or letter.
    ///
    /// Mutation: dropping the unconsumed-input check in parse_isotime.
    /// Oracle: `09301` and `143045X` match no ISO time form.
    #[test]
    fn test_invalid_time_trailing_digit() {
        let parser = IsoParser::new();

        assert!(parser.parse_isotime("09301").is_err());
        assert!(parser.parse_isotime("143045X").is_err());
    }

    /// Verify parse_isotime() rejects an AM/PM suffix or trailing text.
    ///
    /// Mutation: treating any trailing text as whitespace in
    /// parse_isotime.
    /// Oracle: ISO 8601 has no AM/PM suffix.
    #[test]
    fn test_invalid_time_trailing_text() {
        let parser = IsoParser::new();

        assert!(parser.parse_isotime("0930 pm").is_err());
        assert!(parser.parse_isotime("09:30 pm").is_err());
        assert!(parser.parse_isotime("09:30am").is_err());

        assert!(parser.parse_isotime("14:30extra").is_err());
        assert!(parser.parse_isotime("14:30:45.123extra").is_err());
    }

    /// Verify isoparse() rejects text after the time.
    ///
    /// Mutation: dropping the unconsumed-input check in isoparse.
    /// Oracle: `extra` and `X` match no ISO time or offset form.
    #[test]
    fn test_invalid_datetime_trailing_text() {
        let parser = IsoParser::new();

        assert!(parser.isoparse("2024-01-15T09:30extra").is_err());
        assert!(parser.isoparse("2024-01-15T093015X").is_err());
    }

    /// Verify parse_isotime() accepts a trailing space or tab.
    ///
    /// Mutation: rejecting all trailing input, or allowing only spaces.
    /// Oracle: hand-read components of each input.
    #[test]
    fn test_valid_time_trailing_whitespace() {
        let parser = IsoParser::new();

        let r = parser.parse_isotime("14:30 ").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(30));

        let r = parser.parse_isotime("14:30:45\t").unwrap();
        assert_eq!(r.hour, Some(14));
        assert_eq!(r.minute, Some(30));
        assert_eq!(r.second, Some(45));
    }

    /// Verify isoparse() reads a digit after the date as the separator.
    ///
    /// Mutation: skipping the time when the byte after the date is a
    /// digit.
    /// Oracle: dateutil.parser.isoparse, which raises "ISO time too
    /// short" for the first two and gives 12:30 for `2024011511230`.
    #[test]
    fn test_isoparse_digit_separator() {
        let parser = IsoParser::new();

        assert!(parser.isoparse("2024-01-155").is_err());
        assert!(parser.isoparse("2024-0115").is_err());

        let r = parser.isoparse("2024011511230").unwrap();
        assert_eq!((r.year, r.month, r.day), (Some(2024), Some(1), Some(15)));
        assert_eq!((r.hour, r.minute), (Some(12), Some(30)));
    }

    /// Verify isoparse() moves 24:00 to 00:00 on the next day.
    ///
    /// Mutation: keeping the parsed date, or adding a day without
    /// carrying into the month or year.
    /// Oracle: dateutil.parser.isoparse, 2024-12-31T24:00 = 2025-01-01
    /// 00:00 and 2023-02-28T24:00 = 2023-03-01 00:00.
    #[test]
    fn test_isoparse_hour_24_next_day() {
        let parser = IsoParser::new();
        let cases = [
            ("2024-01-15T24:00", (2024, 1, 16)),
            ("2024-02-28T24:00", (2024, 2, 29)),
            ("2023-02-28T24:00", (2023, 3, 1)),
            ("2024-12-31T24:00", (2025, 1, 1)),
        ];
        for (text, (year, month, day)) in cases {
            let r = parser.isoparse(text).unwrap();
            assert_eq!(
                (r.year, r.month, r.day, r.hour),
                (Some(year), Some(month), Some(day), Some(0)),
                "{text}"
            );
        }
    }

    /// Verify isoparse() leaves an invalid date as parsed at 24:00.
    ///
    /// Mutation: rolling over without the year, month and day range
    /// check, which turns month 0 day 0 into January 1.
    /// Oracle: dateutil.parser.isoparse raises on each input ('month
    /// must be in 1..12', 'day is out of range', 'year 0 is out of
    /// range'), so the date must stay invalid for the caller to reject.
    #[test]
    fn test_isoparse_hour_24_invalid_date_not_rolled() {
        let parser = IsoParser::new();
        let cases = [
            ("2024-00-00T24:00", (0, 2024, 0, 0)),
            ("2024-01-00T24:00", (0, 2024, 1, 0)),
            ("0000-12-31T24:00", (0, 0, 12, 31)),
        ];
        for (text, (hour, year, month, day)) in cases {
            let r = parser.isoparse(text).unwrap();
            assert_eq!(
                (r.hour, r.year, r.month, r.day),
                (Some(hour), Some(year), Some(month), Some(day)),
                "{text}"
            );
        }
    }

    /// Verify a week date where the Zeller sum is negative.
    ///
    /// Mutation: `%` for `rem_euclid` in day_of_week, which wraps -1 to
    /// u32::MAX.
    /// Oracle: Python date.fromisocalendar(2601, 1, 1) = 2600-12-29,
    /// and date(2601, 1, 4).isoweekday() = 7 (Sunday).
    #[test]
    fn test_week_date_negative_zeller_sum() {
        assert_eq!(day_of_week(2601, 1, 4), 6);

        let r = IsoParser::new().parse_isodate("2601-W01-1").unwrap();
        assert_eq!((r.year, r.month, r.day), (Some(2600), Some(12), Some(29)));
    }
}
