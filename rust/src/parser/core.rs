//! Core datetime parser - port of dateutil.parser.parser.
//!
//! This module provides the main parsing logic that tokenizes input strings
//! and extracts datetime components.

use super::errors::ParserError;
use super::parserinfo::ParserInfo;
use super::result::ParseResult;
use super::tokenizer::Tokenizer;
use super::ymd::Ymd;

/// Main datetime parser.
#[derive(Debug, Clone)]
pub struct Parser {
    info: ParserInfo,
}

impl Default for Parser {
    fn default() -> Self {
        Self::new(false, false)
    }
}

/// Check if character is ASCII digit.
fn is_ascii_digit(c: u8) -> bool {
    c >= b'0' && c <= b'9'
}

/// Check if all bytes in slice are ASCII digits.
fn all_ascii_digits(bytes: &[u8], start: usize, end: usize) -> bool {
    let mut i = start;
    while i < end {
        if !is_ascii_digit(bytes[i]) {
            return false;
        }
        i += 1;
    }
    true
}

/// Check if string contains only ASCII digits.
fn str_all_digits(s: &str) -> bool {
    let bytes = s.as_bytes();
    let n = bytes.len();
    all_ascii_digits(bytes, 0, n)
}

/// Check if all chars are ASCII uppercase letters.
fn all_ascii_uppercase(s: &str) -> bool {
    let bytes = s.as_bytes();
    let n = bytes.len();
    if n == 0 {
        return false;
    }
    let mut has_letter = false;
    let mut i = 0usize;
    while i < n {
        let c = bytes[i];
        if c >= b'A' && c <= b'Z' {
            has_letter = true;
        } else if c >= b'a' && c <= b'z' {
            // Lowercase letter - not all uppercase
            return false;
        }
        // Skip non-letter characters (digits, symbols, etc.)
        i += 1;
    }
    // Must have at least one uppercase letter
    has_letter
}

/// Parse a slice of bytes as u32.
fn parse_u32_slice(bytes: &[u8], start: usize, end: usize) -> Result<u32, ParserError> {
    let mut result = 0u32;
    let mut i = start;
    while i < end {
        let c = bytes[i];
        if c >= b'0' && c <= b'9' {
            result = result * 10 + (c - b'0') as u32;
        } else {
            return Err(ParserError::ParseError("Invalid digit".to_string()));
        }
        i += 1;
    }
    Ok(result)
}

/// Parse string as u32.
fn parse_str_u32(s: &str) -> Result<u32, ParserError> {
    let bytes = s.as_bytes();
    parse_u32_slice(bytes, 0, bytes.len())
}

/// Parse string as i32.
fn parse_str_i32(s: &str) -> Result<i32, ParserError> {
    let bytes = s.as_bytes();
    let n = bytes.len();
    if n == 0 {
        return Err(ParserError::ParseError("Empty string".to_string()));
    }

    let mut i = 0usize;
    let negative = bytes[0] == b'-';
    let positive_sign = bytes[0] == b'+';
    if negative || positive_sign {
        i = 1;
    }

    let mut result = 0i32;
    while i < n {
        let c = bytes[i];
        if c >= b'0' && c <= b'9' {
            result = result * 10 + (c - b'0') as i32;
        } else {
            return Err(ParserError::ParseError(format!("Invalid digit in: {}", s)));
        }
        i += 1;
    }

    if negative {
        result = -result;
    }
    Ok(result)
}

/// Parse string as f64.
fn parse_str_f64(s: &str) -> Result<f64, ParserError> {
    // Use standard library for floating point (complex to implement manually)
    s.parse::<f64>()
        .map_err(|_| ParserError::ParseError(format!("Invalid number: {}", s)))
}

/// Find character position in string.
fn find_char(s: &str, c: char) -> Option<usize> {
    let bytes = s.as_bytes();
    let target = c as u8;
    let n = bytes.len();
    let mut i = 0usize;
    while i < n {
        if bytes[i] == target {
            return Some(i);
        }
        i += 1;
    }
    None
}

/// Find any of multiple characters.
fn find_any_char(s: &str, chars: &[char]) -> Option<usize> {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let nc = chars.len();
    let mut i = 0usize;
    while i < n {
        let mut j = 0usize;
        while j < nc {
            if bytes[i] == chars[j] as u8 {
                return Some(i);
            }
            j += 1;
        }
        i += 1;
    }
    None
}

/// Check if string contains character.
fn contains_char(s: &str, c: char) -> bool {
    find_char(s, c).is_some()
}

/// Check if string starts with character.
fn starts_with_char(s: &str, c: char) -> bool {
    let bytes = s.as_bytes();
    bytes.len() > 0 && bytes[0] == c as u8
}

/// Check if string ends with substring.
fn ends_with_str(s: &str, suffix: &str) -> bool {
    let s_bytes = s.as_bytes();
    let suffix_bytes = suffix.as_bytes();
    let sn = s_bytes.len();
    let sufn = suffix_bytes.len();
    if sufn > sn {
        return false;
    }
    let start = sn - sufn;
    let mut i = 0usize;
    while i < sufn {
        if s_bytes[start + i] != suffix_bytes[i] {
            return false;
        }
        i += 1;
    }
    true
}

/// Check if string starts with prefix.
fn starts_with_str(s: &str, prefix: &str) -> bool {
    let s_bytes = s.as_bytes();
    let prefix_bytes = prefix.as_bytes();
    let sn = s_bytes.len();
    let pn = prefix_bytes.len();
    if pn > sn {
        return false;
    }
    let mut i = 0usize;
    while i < pn {
        if s_bytes[i] != prefix_bytes[i] {
            return false;
        }
        i += 1;
    }
    true
}

/// Convert string to uppercase.
fn to_uppercase(s: &str) -> String {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut result = String::with_capacity(n);
    let mut i = 0usize;
    while i < n {
        let c = bytes[i];
        if c >= b'a' && c <= b'z' {
            result.push((c - 32) as char);
        } else {
            result.push(c as char);
        }
        i += 1;
    }
    result
}

/// Substring from start to end.
fn substr_range(s: &str, start: usize, end: usize) -> &str {
    let bytes = s.as_bytes();
    let actual_end = if end > bytes.len() { bytes.len() } else { end };
    let actual_start = if start > actual_end {
        actual_end
    } else {
        start
    };
    unsafe { std::str::from_utf8_unchecked(&bytes[actual_start..actual_end]) }
}

/// Split string by character.
fn split_char(s: &str, delim: char) -> Vec<&str> {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let d = delim as u8;
    let mut result: Vec<&str> = Vec::new();
    let mut start = 0usize;
    let mut i = 0usize;

    while i < n {
        if bytes[i] == d {
            if i > start {
                result.push(substr_range(s, start, i));
            } else {
                result.push("");
            }
            start = i + 1;
        }
        i += 1;
    }

    // Add remaining part
    if start <= n {
        result.push(substr_range(s, start, n));
    }

    result
}

/// Split string by whitespace.
fn split_whitespace_vec(s: &str) -> Vec<&str> {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut result: Vec<&str> = Vec::new();
    let mut start = 0usize;
    let mut in_word = false;
    let mut i = 0usize;

    while i < n {
        let c = bytes[i];
        let is_ws = c == b' ' || c == b'\t' || c == b'\n' || c == b'\r';

        if is_ws {
            if in_word {
                result.push(substr_range(s, start, i));
                in_word = false;
            }
        } else {
            if !in_word {
                start = i;
                in_word = true;
            }
        }
        i += 1;
    }

    if in_word {
        result.push(substr_range(s, start, n));
    }

    result
}

/// Trim whitespace from string.
fn trim_str(s: &str) -> &str {
    let bytes = s.as_bytes();
    let n = bytes.len();
    if n == 0 {
        return s;
    }

    // Find start (skip leading whitespace)
    let mut start = 0usize;
    while start < n {
        let c = bytes[start];
        if c != b' ' && c != b'\t' && c != b'\n' && c != b'\r' {
            break;
        }
        start += 1;
    }

    // Find end (skip trailing whitespace)
    let mut end = n;
    while end > start {
        let c = bytes[end - 1];
        if c != b' ' && c != b'\t' && c != b'\n' && c != b'\r' {
            break;
        }
        end -= 1;
    }

    substr_range(s, start, end)
}

/// Pad string with zeros on right.
fn pad_right_zeros(s: &str, target_len: usize) -> String {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut result = String::with_capacity(target_len);

    let mut i = 0usize;
    while i < n && i < target_len {
        result.push(bytes[i] as char);
        i += 1;
    }

    while i < target_len {
        result.push('0');
        i += 1;
    }

    result
}

impl Parser {
    /// Create a new parser with the given settings.
    pub fn new(dayfirst: bool, yearfirst: bool) -> Self {
        Parser {
            info: ParserInfo::new(dayfirst, yearfirst),
        }
    }

    /// Create a new parser with custom ParserInfo.
    #[allow(dead_code)]
    pub fn with_info(info: ParserInfo) -> Self {
        Parser { info }
    }

    /// Parse a standalone time string.
    ///
    /// Handles formats:
    /// - HHMM: "0930" → 09:30
    /// - HHMMSS: "093015" → 09:30:15
    /// - HHMMSS with fraction: "093015.751" or "093015,751" → 09:30:15.751
    /// - Separated: "9:30", "9.30", "9:30:15", "9.30.15"
    /// - With AM/PM: "0930 PM", "9:30 AM", "12:00 PM"
    ///
    /// Returns None for invalid inputs (e.g., hour > 23, minute > 59).
    pub fn parse_time_only(&self, timestr: &str) -> Result<ParseResult, ParserError> {
        let s = trim_str(timestr);
        if s.len() == 0 {
            return Err(ParserError::ParseError("Empty time string".to_string()));
        }

        // Extract optional AM/PM suffix
        let (time_part, ampm) = self.extract_ampm_suffix(s);

        // Try compact format first (HHMM, HHMMSS)
        if let Some(result) = self.try_parse_compact_time(time_part, ampm)? {
            return Ok(result);
        }

        // Try separated format (H:MM, HH:MM, H.MM, HH.MM, with optional seconds)
        if let Some(result) = self.try_parse_separated_time(time_part, ampm)? {
            return Ok(result);
        }

        Err(ParserError::ParseError(format!(
            "Invalid time format: {}",
            timestr
        )))
    }

    /// Extract AM/PM suffix from time string.
    fn extract_ampm_suffix<'a>(&self, s: &'a str) -> (&'a str, Option<u32>) {
        let s_upper = to_uppercase(s);
        if ends_with_str(&s_upper, " AM") {
            let end = s.len() - 3;
            (substr_range(s, 0, end), Some(0))
        } else if ends_with_str(&s_upper, " PM") {
            let end = s.len() - 3;
            (substr_range(s, 0, end), Some(1))
        } else {
            (s, None)
        }
    }

    /// Try to parse compact time format (HHMM or HHMMSS with optional fraction).
    fn try_parse_compact_time(
        &self,
        s: &str,
        ampm: Option<u32>,
    ) -> Result<Option<ParseResult>, ParserError> {
        // Find fraction separator position (. or ,)
        let delims: [char; 2] = ['.', ','];
        let (digits_part, frac_part) = if let Some(pos) = find_any_char(s, &delims) {
            (
                substr_range(s, 0, pos),
                Some(substr_range(s, pos + 1, s.len())),
            )
        } else {
            (s, None)
        };

        // Must be exactly 4 or 6 digits
        if !str_all_digits(digits_part) {
            return Ok(None);
        }

        let len = digits_part.len();
        if len != 4 && len != 6 {
            return Ok(None);
        }

        // Parse components
        let hour: u32 = parse_str_u32(substr_range(digits_part, 0, 2))
            .map_err(|_| ParserError::ParseError("Invalid hour".to_string()))?;
        let minute: u32 = parse_str_u32(substr_range(digits_part, 2, 4))
            .map_err(|_| ParserError::ParseError("Invalid minute".to_string()))?;
        let second: u32 = if len == 6 {
            parse_str_u32(substr_range(digits_part, 4, 6))
                .map_err(|_| ParserError::ParseError("Invalid second".to_string()))?
        } else {
            0
        };

        // Validate ranges (before AM/PM adjustment)
        let max_hour = if ampm.is_some() { 12 } else { 23 };
        if hour > max_hour || minute > 59 || second > 59 {
            return Err(ParserError::ParseError(format!(
                "Time values out of range: {:02}:{:02}:{:02}",
                hour, minute, second
            )));
        }

        // Parse microseconds
        let microsecond = if let Some(frac) = frac_part {
            let frac_len = frac.len();
            let take_len = if frac_len < 6 { frac_len } else { 6 };
            let padded = pad_right_zeros(substr_range(frac, 0, take_len), 6);
            parse_str_u32(&padded).unwrap_or(0)
        } else {
            0
        };

        // Build result
        let result = ParseResult {
            hour: Some(if let Some(ampm_val) = ampm {
                self.adjust_ampm(hour, ampm_val)
            } else {
                hour
            }),
            minute: Some(minute),
            second: Some(second),
            microsecond: Some(microsecond),
            ampm,
            ..Default::default()
        };

        Ok(Some(result))
    }

    /// Try to parse separated time format (H:MM, HH:MM, H.MM, HH.MM with optional seconds).
    fn try_parse_separated_time(
        &self,
        s: &str,
        ampm: Option<u32>,
    ) -> Result<Option<ParseResult>, ParserError> {
        // Pattern: H:MM or HH:MM or H.MM or HH.MM, optionally with :SS or .SS and fraction
        // Use tokenizer to split
        let tokens: Vec<String> = Tokenizer::split(s);

        let tokens_len = tokens.len();
        if tokens_len == 0 {
            return Ok(None);
        }

        let hour: u32;
        let minute: u32;
        let mut second: u32 = 0;
        let mut microsecond: u32 = 0;

        // Check if first token is a decimal like "9.30" (tokenizer keeps H.MM as one token)
        if contains_char(&tokens[0], '.') && !starts_with_char(&tokens[0], '.') {
            let parts: Vec<&str> = split_char(&tokens[0], '.');
            let parts_len = parts.len();
            if parts_len >= 2 {
                let hour_str = parts[0];
                let min_str = parts[1];

                let hour_len = hour_str.len();
                let min_len = min_str.len();

                if hour_len <= 2
                    && min_len == 2
                    && str_all_digits(hour_str)
                    && str_all_digits(min_str)
                {
                    hour = parse_str_u32(hour_str).unwrap_or(0);
                    minute = parse_str_u32(min_str).unwrap_or(0);

                    // Check for seconds in parts[2] if present
                    if parts_len >= 3 {
                        let (sec, micro) = self.parsems(parts[2]);
                        second = sec;
                        microsecond = micro;
                    }

                    // Validate ranges
                    let max_hour = if ampm.is_some() { 12 } else { 23 };
                    if hour > max_hour || minute > 59 || second > 59 {
                        return Err(ParserError::ParseError(format!(
                            "Time values out of range: {:02}:{:02}:{:02}",
                            hour, minute, second
                        )));
                    }

                    // Build result
                    let result = ParseResult {
                        hour: Some(if let Some(ampm_val) = ampm {
                            self.adjust_ampm(hour, ampm_val)
                        } else {
                            hour
                        }),
                        minute: Some(minute),
                        second: Some(second),
                        microsecond: Some(microsecond),
                        ampm,
                        ..Default::default()
                    };

                    return Ok(Some(result));
                }
            }
        }

        // Standard token-based parsing (H:MM, etc.)
        if tokens_len < 3 {
            return Ok(None);
        }

        // First token should be hour (1-2 digits)
        let hour_str = &tokens[0];
        let hour_str_len = hour_str.len();
        if !str_all_digits(hour_str) || hour_str_len > 2 {
            return Ok(None);
        }

        // Second token should be separator (: or .)
        let sep = &tokens[1];
        if sep != ":" && sep != "." {
            return Ok(None);
        }

        // Third token should be minute (2 digits)
        let min_str = &tokens[2];
        let min_str_len = min_str.len();
        if !str_all_digits(min_str) || min_str_len != 2 {
            return Ok(None);
        }

        hour = parse_str_u32(hour_str).unwrap_or(0);
        minute = parse_str_u32(min_str).unwrap_or(0);

        // Check for seconds: :SS or .SS
        if tokens_len >= 5 && (tokens[3] == ":" || tokens[3] == ".") {
            // Parse seconds (may include fraction like "45.123")
            let sec_str = &tokens[4];
            let (sec, micro) = self.parsems(sec_str);
            second = sec;
            microsecond = micro;
        }

        // Validate ranges
        let max_hour = if ampm.is_some() { 12 } else { 23 };
        if hour > max_hour || minute > 59 || second > 59 {
            return Err(ParserError::ParseError(format!(
                "Time values out of range: {:02}:{:02}:{:02}",
                hour, minute, second
            )));
        }

        // Build result
        let result = ParseResult {
            hour: Some(if let Some(ampm_val) = ampm {
                self.adjust_ampm(hour, ampm_val)
            } else {
                hour
            }),
            minute: Some(minute),
            second: Some(second),
            microsecond: Some(microsecond),
            ampm,
            ..Default::default()
        };

        Ok(Some(result))
    }

    /// Parse a datetime string.
    ///
    /// # Arguments
    /// * `timestr` - The datetime string to parse
    /// * `dayfirst` - Override dayfirst setting (None = use default)
    /// * `yearfirst` - Override yearfirst setting (None = use default)
    /// * `fuzzy` - Whether to allow fuzzy parsing
    /// * `fuzzy_with_tokens` - If true, return skipped tokens
    pub fn parse(
        &self,
        timestr: &str,
        dayfirst: Option<bool>,
        yearfirst: Option<bool>,
        fuzzy: bool,
        fuzzy_with_tokens: bool,
    ) -> Result<(ParseResult, Option<Vec<String>>), ParserError> {
        let fuzzy = fuzzy || fuzzy_with_tokens;

        let dayfirst = match dayfirst {
            Some(v) => v,
            None => self.info.dayfirst,
        };
        let yearfirst = match yearfirst {
            Some(v) => v,
            None => self.info.yearfirst,
        };

        let (res, skipped_tokens) = self.parse_inner(timestr, dayfirst, yearfirst, fuzzy)?;

        if fuzzy_with_tokens {
            Ok((res, Some(skipped_tokens)))
        } else {
            Ok((res, None))
        }
    }

    /// Internal parse implementation.
    fn parse_inner(
        &self,
        timestr: &str,
        dayfirst: bool,
        yearfirst: bool,
        fuzzy: bool,
    ) -> Result<(ParseResult, Vec<String>), ParserError> {
        // Try ISO format first if the string looks like ISO (starts with YYYY- or is YYYYMMDD format)
        if Self::looks_like_iso(timestr) {
            if let Ok(mut result) = super::IsoParser::new().isoparse(timestr) {
                // Check for trailing timezone name that ISO parser might have missed
                // This handles cases like "2024-01-15 10:30:00 UTC" or "2024-01-15T10:30:00 GMT+3"
                if result.tzoffset.is_none() && result.hour.is_some() {
                    result = self.extract_trailing_timezone(timestr, result);
                }
                return Ok((result, Vec::new()));
            }
        }

        let mut res = ParseResult::default();
        let tokens: Vec<String> = Tokenizer::split(timestr);
        let mut skipped_idxs: Vec<usize> = Vec::new();
        let mut ymd = Ymd::new();
        let mut flip_next_sign = false; // For GMT+3 style parsing

        let len_l = tokens.len();
        let mut i = 0usize;

        while i < len_l {
            let token = &tokens[i];

            // Try to parse as a number
            if parse_str_f64(token).is_ok() {
                i = self.parse_numeric_token(&tokens, i, &mut ymd, &mut res, fuzzy)?;
            }
            // Check weekday
            else if let Some(weekday) = self.info.weekday(token) {
                res.weekday = Some(weekday);
            }
            // Check month name
            else if let Some(month) = self.info.month(token) {
                ymd.append(month as i32, Some('M'))?;

                if i + 1 < len_l {
                    if tokens[i + 1] == "-" || tokens[i + 1] == "/" {
                        // Jan-01[-99]
                        let sep = &tokens[i + 1];
                        if i + 2 < len_l {
                            ymd.append_str(&tokens[i + 2], None)?;

                            if i + 3 < len_l && &tokens[i + 3] == sep {
                                // Jan-01-99
                                if i + 4 < len_l {
                                    ymd.append_str(&tokens[i + 4], None)?;
                                    i += 2;
                                }
                            }
                            i += 2;
                        }
                    } else if i + 4 < len_l
                        && tokens[i + 1] == " "
                        && tokens[i + 3] == " "
                        && self.info.pertain(&tokens[i + 2])
                    {
                        // Jan of 01
                        if str_all_digits(&tokens[i + 4]) {
                            let value: i32 = parse_str_i32(&tokens[i + 4]).unwrap_or(0);
                            let year = self.info.convertyear(value, false);
                            ymd.append(year, Some('Y'))?;
                            i += 4;
                        }
                    }
                }
            }
            // Check am/pm
            else if let Some(ampm_val) = self.info.ampm(token) {
                let val_is_ampm = self.ampm_valid(res.hour, res.ampm, fuzzy);

                if val_is_ampm {
                    if let Some(hour) = res.hour {
                        res.hour = Some(self.adjust_ampm(hour, ampm_val));
                    }
                    res.ampm = Some(ampm_val);
                } else if fuzzy {
                    skipped_idxs.push(i);
                }
            }
            // Check for a timezone name
            else if self.could_be_tzname(res.hour, &res.tzname, res.tzoffset, token) {
                res.tzname = Some(token.clone());
                res.tzoffset = self.info.tzoffset(token);

                // Check for something like GMT+3 or BRST+3
                // "GMT+3" means "my time +3 is GMT", so we need to reverse the sign
                if i + 1 < len_l && (tokens[i + 1] == "+" || tokens[i + 1] == "-") {
                    flip_next_sign = true;
                    res.tzoffset = None;
                    if self.info.utczone(token) {
                        // With something like GMT+3, the timezone is *not* GMT
                        res.tzname = None;
                    }
                }
            }
            // Check for a numbered timezone
            else if res.hour.is_some() && (token == "+" || token == "-") {
                // Apply sign flip if needed (for GMT+3 style)
                let mut signal: i32 = if token == "+" { 1 } else { -1 };
                if flip_next_sign {
                    signal = -signal;
                    flip_next_sign = false;
                }

                if i + 1 < len_l {
                    let len_li = tokens[i + 1].len();

                    let (hour_offset, min_offset, skip): (i32, i32, usize) = if len_li == 4 {
                        // -0300
                        let h: i32 = parse_str_i32(substr_range(&tokens[i + 1], 0, 2)).unwrap_or(0);
                        let m: i32 = parse_str_i32(substr_range(&tokens[i + 1], 2, 4)).unwrap_or(0);
                        (h, m, 0)
                    } else if i + 2 < len_l && tokens[i + 2] == ":" {
                        // -03:00
                        let h: i32 = parse_str_i32(&tokens[i + 1]).unwrap_or(0);
                        let m: i32 = if i + 3 < len_l {
                            parse_str_i32(&tokens[i + 3]).unwrap_or(0)
                        } else {
                            0
                        };
                        (h, m, 2)
                    } else if len_li <= 2 {
                        // -[0]3
                        let h: i32 = parse_str_i32(&tokens[i + 1]).unwrap_or(0);
                        (h, 0, 0)
                    } else {
                        return Err(ParserError::ParseError(format!(
                            "Invalid timezone offset: {}",
                            timestr
                        )));
                    };

                    res.tzoffset = Some(signal * (hour_offset * 3600 + min_offset * 60));

                    // Look for a timezone name between parenthesis
                    let base = i + 2 + skip;
                    if base + 3 < len_l
                        && self.info.jump(&tokens[base])
                        && tokens[base + 1] == "("
                        && tokens[base + 3] == ")"
                        && tokens[base + 2].len() >= 3
                        && self.could_be_tzname(res.hour, &None, None, &tokens[base + 2])
                    {
                        res.tzname = Some(tokens[base + 2].clone());
                        i += 4;
                    }

                    i += 1 + skip;
                }
            }
            // Check jumps or fuzzy mode
            else if self.info.jump(token) || fuzzy {
                skipped_idxs.push(i);
            } else {
                return Err(ParserError::ParseError(format!(
                    "Unknown string format: {}",
                    timestr
                )));
            }

            i += 1;
        }

        // Process year/month/day
        let (year, month, day) = ymd.resolve(yearfirst, dayfirst)?;

        res.century_specified = ymd.century_specified;
        res.year = year;
        res.month = match month {
            Some(m) => Some(m as u32),
            None => None,
        };
        res.day = match day {
            Some(d) => Some(d as u32),
            None => None,
        };

        // Validate and convert year
        if let Some(y) = res.year {
            res.year = Some(self.info.convertyear(y, res.century_specified));
        }

        // Normalize timezone info
        let tz_is_z = match &res.tzname {
            Some(name) => name == "Z" || name == "z",
            None => false,
        };
        let tz_is_utc_variant = match &res.tzname {
            Some(name) => self.info.utczone(name),
            None => false,
        };

        if (res.tzoffset == Some(0) && res.tzname.is_none()) || tz_is_z {
            res.tzname = Some("UTC".to_string());
            res.tzoffset = Some(0);
        } else if res.tzoffset.is_some() && res.tzoffset != Some(0) && tz_is_utc_variant {
            res.tzoffset = Some(0);
        }

        // Build skipped tokens
        let skipped_tokens = self.recombine_skipped(&tokens, &skipped_idxs);

        Ok((res, skipped_tokens))
    }

    /// Check if a string looks like ISO 8601 format.
    /// ISO format: YYYY-MM-DD, YYYYMMDD, YYYY-MM-DDTHH:MM:SS, etc.
    ///
    /// Be conservative - only use ISO parser for unambiguous ISO formats:
    /// - YYYY-... (hyphenated ISO)
    /// - YYYYMMDD exactly (8 digits)
    /// - YYYYMMDDT... (8 digits + T separator)
    ///
    /// Do NOT use ISO for:
    /// - YYYY alone (needs default filling from general parser)
    /// - 12/14 digit compact formats without T (general parser handles these)
    fn looks_like_iso(s: &str) -> bool {
        let bytes = s.as_bytes();
        let n = bytes.len();

        // Need at least 5 chars for meaningful ISO (YYYY- minimum)
        if n < 5 {
            return false;
        }

        // Must start with 4 digits (year)
        if !all_ascii_digits(bytes, 0, 4) {
            return false;
        }

        // Check for ISO separator pattern: YYYY-...
        if bytes[4] == b'-' {
            return true;
        }

        // YYYYMMDD format (exactly 8 digits, or 8 digits + T separator)
        if n >= 8 && all_ascii_digits(bytes, 0, 8) {
            // Exactly 8 digits (YYYYMMDD) - use ISO
            if n == 8 {
                return true;
            }
            // 8 digits + T separator (YYYYMMDDT...) - use ISO
            if n > 8 && bytes[8] == b'T' {
                return true;
            }
            // Other cases (e.g., 12/14 digit compact) - let general parser handle
        }

        false
    }

    /// Parse a numeric token.
    fn parse_numeric_token(
        &self,
        tokens: &[String],
        idx: usize,
        ymd: &mut Ymd,
        res: &mut ParseResult,
        fuzzy: bool,
    ) -> Result<usize, ParserError> {
        let value_repr = &tokens[idx];
        let value: f64 = parse_str_f64(value_repr).map_err(|_| {
            ParserError::ParseError(format!("Invalid numeric token: {}", value_repr))
        })?;

        let len_li = value_repr.len();
        let len_l = tokens.len();
        let mut idx = idx;

        if ymd.len() == 3
            && (len_li == 2 || len_li == 4)
            && res.hour.is_none()
            && (idx + 1 >= len_l
                || (tokens[idx + 1] != ":" && self.info.hms(&tokens[idx + 1]).is_none()))
        {
            // 19990101T23[59]
            let s = &tokens[idx];
            res.hour = Some(parse_str_u32(substr_range(s, 0, 2)).unwrap_or(0));

            if len_li == 4 {
                res.minute = Some(parse_str_u32(substr_range(s, 2, 4)).unwrap_or(0));
            }
        } else if len_li == 6 || (len_li > 6 && find_char(&tokens[idx], '.') == Some(6)) {
            // YYMMDD or HHMMSS[.ss]
            let s = &tokens[idx];

            if ymd.is_empty() && !contains_char(&tokens[idx], '.') {
                ymd.append_str(substr_range(s, 0, 2), None)?;
                ymd.append_str(substr_range(s, 2, 4), None)?;
                ymd.append_str(substr_range(s, 4, s.len()), None)?;
            } else {
                // 19990101T235959[.59]
                res.hour = Some(parse_str_u32(substr_range(s, 0, 2)).unwrap_or(0));
                res.minute = Some(parse_str_u32(substr_range(s, 2, 4)).unwrap_or(0));
                let (sec, micro) = self.parsems(substr_range(s, 4, s.len()));
                res.second = Some(sec);
                res.microsecond = Some(micro);
            }
        } else if len_li == 8 || len_li == 12 || len_li == 14 {
            // YYYYMMDD[HHMMSS]
            let s = &tokens[idx];
            ymd.append_str(substr_range(s, 0, 4), Some('Y'))?;
            ymd.append_str(substr_range(s, 4, 6), None)?;
            ymd.append_str(substr_range(s, 6, 8), None)?;

            if len_li > 8 {
                res.hour = Some(parse_str_u32(substr_range(s, 8, 10)).unwrap_or(0));
                res.minute = Some(parse_str_u32(substr_range(s, 10, 12)).unwrap_or(0));

                if len_li > 12 {
                    res.second = Some(parse_str_u32(substr_range(s, 12, s.len())).unwrap_or(0));
                }
            }
        } else if let Some(hms_idx) = self.find_hms_idx(idx, tokens, true) {
            // HH[ ]h or MM[ ]m or SS[.ss][ ]s
            let (new_idx, hms) = self.parse_hms(idx, tokens, hms_idx);
            idx = new_idx;
            if let Some(hms) = hms {
                self.assign_hms(res, value_repr, hms)?;
            }
        } else if idx + 2 < len_l && tokens[idx + 1] == ":" {
            // HH:MM[:SS[.ss]]
            res.hour = Some(value as u32);
            let min_val: f64 = parse_str_f64(&tokens[idx + 2]).unwrap_or(0.0);
            let (minute, second) = self.parse_min_sec(min_val);
            res.minute = Some(minute);
            if let Some(s) = second {
                res.second = Some(s);
            }

            if idx + 4 < len_l && tokens[idx + 3] == ":" {
                let (sec, micro) = self.parsems(&tokens[idx + 4]);
                res.second = Some(sec);
                res.microsecond = Some(micro);
                idx += 2;
            }

            idx += 2;
        } else if idx + 1 < len_l
            && (tokens[idx + 1] == "-" || tokens[idx + 1] == "/" || tokens[idx + 1] == ".")
        {
            let sep = &tokens[idx + 1];
            ymd.append_str(value_repr, None)?;

            if idx + 2 < len_l && !self.info.jump(&tokens[idx + 2]) {
                if str_all_digits(&tokens[idx + 2]) {
                    // 01-01[-01]
                    ymd.append_str(&tokens[idx + 2], None)?;
                } else {
                    // 01-Jan[-01]
                    if let Some(month) = self.info.month(&tokens[idx + 2]) {
                        ymd.append(month as i32, Some('M'))?;
                    } else {
                        return Err(ParserError::ParseError(format!(
                            "Unknown string format: {}",
                            tokens[idx + 2]
                        )));
                    }
                }

                if idx + 3 < len_l && &tokens[idx + 3] == sep {
                    // We have three members
                    if idx + 4 < len_l {
                        if let Some(month) = self.info.month(&tokens[idx + 4]) {
                            ymd.append(month as i32, Some('M'))?;
                        } else {
                            ymd.append_str(&tokens[idx + 4], None)?;
                        }
                        idx += 2;
                    }
                }

                idx += 1;
            }
            idx += 1;
        } else if idx + 1 >= len_l || self.info.jump(&tokens[idx + 1]) {
            if idx + 2 < len_l && self.info.ampm(&tokens[idx + 2]).is_some() {
                // 12 am
                let hour = value as u32;
                res.hour = Some(self.adjust_ampm(hour, self.info.ampm(&tokens[idx + 2]).unwrap()));
                idx += 1;
            } else {
                // Year, month or day - but only if it looks valid
                let int_val = value as i32;
                let could_be_date_component = (int_val >= 1 && int_val <= 31)  // day
                    || (int_val >= 1 && int_val <= 12)  // month
                    || (int_val >= 0 && int_val <= 99)  // 2-digit year
                    || (int_val >= 1000 && int_val <= 9999); // 4-digit year

                if could_be_date_component {
                    ymd.append(value as i32, None)?;
                } else if !fuzzy {
                    return Err(ParserError::ParseError(format!(
                        "Invalid date component: {}",
                        value_repr
                    )));
                }
                // In fuzzy mode with invalid date component, just skip it
            }
            idx += 1;
        } else if self.info.ampm(&tokens[idx + 1]).is_some() && value >= 0.0 && value < 24.0 {
            // 12am
            let hour = value as u32;
            res.hour = Some(self.adjust_ampm(hour, self.info.ampm(&tokens[idx + 1]).unwrap()));
            idx += 1;
        } else if ymd.could_be_day(value as i32) {
            ymd.append(value as i32, None)?;
        } else if !fuzzy {
            return Err(ParserError::ParseError(format!(
                "Unknown numeric format: {}",
                value_repr
            )));
        }

        Ok(idx)
    }

    /// Find HMS label index.
    fn find_hms_idx(&self, idx: usize, tokens: &[String], allow_jump: bool) -> Option<usize> {
        let len_l = tokens.len();

        if idx + 1 < len_l && self.info.hms(&tokens[idx + 1]).is_some() {
            // e.g. "12h"
            Some(idx + 1)
        } else if allow_jump
            && idx + 2 < len_l
            && tokens[idx + 1] == " "
            && self.info.hms(&tokens[idx + 2]).is_some()
        {
            // e.g. "12 h"
            Some(idx + 2)
        } else if idx > 0 && self.info.hms(&tokens[idx - 1]).is_some() {
            // e.g. the "04" in "12h04"
            Some(idx - 1)
        } else if idx > 1
            && idx == len_l - 1
            && tokens[idx - 1] == " "
            && self.info.hms(&tokens[idx - 2]).is_some()
        {
            // Final token with space before HMS
            Some(idx - 2)
        } else {
            None
        }
    }

    /// Parse HMS from tokens.
    fn parse_hms(&self, idx: usize, tokens: &[String], hms_idx: usize) -> (usize, Option<u32>) {
        let hms = self.info.hms(&tokens[hms_idx]);
        let new_idx = if hms_idx > idx { hms_idx } else { idx };

        // If looking backwards, increment by one (for the next component)
        let hms = if hms_idx < idx {
            match hms {
                Some(h) => Some(h + 1),
                None => None,
            }
        } else {
            hms
        };

        (new_idx, hms)
    }

    /// Assign HMS value to result.
    fn assign_hms(
        &self,
        res: &mut ParseResult,
        value_repr: &str,
        hms: u32,
    ) -> Result<(), ParserError> {
        let value: f64 = parse_str_f64(value_repr).unwrap_or(0.0);

        match hms {
            0 => {
                // Hour
                res.hour = Some(value as u32);
                let fract = value - (value as u32) as f64;
                if fract != 0.0 {
                    res.minute = Some((60.0 * fract) as u32);
                }
            }
            1 => {
                // Minute
                let (minute, second) = self.parse_min_sec(value);
                res.minute = Some(minute);
                if let Some(s) = second {
                    res.second = Some(s);
                }
            }
            2 => {
                // Second
                let (sec, micro) = self.parsems(value_repr);
                res.second = Some(sec);
                res.microsecond = Some(micro);
            }
            _ => {}
        }

        Ok(())
    }

    /// Check if a token could be a timezone name.
    fn could_be_tzname(
        &self,
        hour: Option<u32>,
        tzname: &Option<String>,
        tzoffset: Option<i32>,
        token: &str,
    ) -> bool {
        hour.is_some()
            && tzname.is_none()
            && tzoffset.is_none()
            && token.len() <= 5
            && (all_ascii_uppercase(token) || self.info.utczone(token))
    }

    /// Check if AM/PM is valid.
    fn ampm_valid(&self, hour: Option<u32>, ampm: Option<u32>, fuzzy: bool) -> bool {
        // If there's already an AM/PM flag, this one isn't one
        if fuzzy && ampm.is_some() {
            return false;
        }

        // If AM/PM is found and hour is not, it's not valid in fuzzy mode
        match hour {
            None => {
                if fuzzy {
                    return false;
                }
                // In non-fuzzy mode, we'd raise an error but we'll just return false here
                false
            }
            Some(h) => {
                if h > 12 {
                    if fuzzy {
                        return false;
                    }
                    false
                } else {
                    true
                }
            }
        }
    }

    /// Adjust hour for AM/PM.
    fn adjust_ampm(&self, hour: u32, ampm: u32) -> u32 {
        if hour < 12 && ampm == 1 {
            hour + 12
        } else if hour == 12 && ampm == 0 {
            0
        } else {
            hour
        }
    }

    /// Parse minute/second from fractional value.
    fn parse_min_sec(&self, value: f64) -> (u32, Option<u32>) {
        let minute = value as u32;
        let sec_remainder = value - (minute as f64);
        let second = if sec_remainder != 0.0 {
            Some((60.0 * sec_remainder) as u32)
        } else {
            None
        };
        (minute, second)
    }

    /// Parse seconds with microseconds.
    fn parsems(&self, value: &str) -> (u32, u32) {
        if !contains_char(value, '.') {
            (parse_str_u32(value).unwrap_or(0), 0)
        } else {
            let parts: Vec<&str> = split_char(value, '.');
            let parts_len = parts.len();
            let seconds: u32 = parse_str_u32(parts[0]).unwrap_or(0);
            let frac = if parts_len > 1 { parts[1] } else { "0" };
            // Pad to 6 digits and take first 6
            let padded = pad_right_zeros(frac, 6);
            let microseconds: u32 = parse_str_u32(substr_range(&padded, 0, 6)).unwrap_or(0);
            (seconds, microseconds)
        }
    }

    /// Extract trailing timezone name from a string after ISO parsing.
    ///
    /// Handles cases like "2024-01-15 10:30:00 UTC" or "2024-01-15T10:30:00 GMT+3"
    /// where the ISO parser parsed the datetime but not the timezone.
    fn extract_trailing_timezone(&self, timestr: &str, mut result: ParseResult) -> ParseResult {
        // Find the last space-separated token(s) that could be timezone info
        let parts: Vec<&str> = split_whitespace_vec(timestr);
        let parts_len = parts.len();
        if parts_len < 2 {
            return result;
        }

        // Check the last part for timezone name
        let last_part = parts[parts_len - 1];

        // Handle "UTC", "GMT", etc. (pure timezone name)
        if self.info.utczone(last_part) {
            result.tzname = Some(to_uppercase(last_part));
            result.tzoffset = Some(0);
            return result;
        }

        // Handle "EST", "PST", etc. (timezone abbreviation without defined offset)
        let last_part_len = last_part.len();
        if last_part_len <= 5 && all_ascii_uppercase(last_part) {
            result.tzname = Some(last_part.to_string());
            // No offset - user needs tzinfos to resolve
            return result;
        }

        // Handle "GMT+3", "GMT-5", etc.
        if last_part_len >= 4 {
            let upper = to_uppercase(last_part);
            if starts_with_str(&upper, "GMT") || starts_with_str(&upper, "UTC") {
                let rest = substr_range(last_part, 3, last_part_len);
                let rest_bytes = rest.as_bytes();
                let rest_len = rest_bytes.len();

                if rest_len > 0 {
                    let first_char = rest_bytes[0];
                    if first_char == b'+' || first_char == b'-' {
                        // GMT+N means "my time + N = GMT", so offset is -N
                        // GMT-N means "my time - N = GMT", so offset is +N
                        let sign: i32 = if first_char == b'+' { -1 } else { 1 };
                        let offset_str = substr_range(rest, 1, rest_len);
                        if let Ok(hours) = parse_str_i32(offset_str) {
                            result.tzoffset = Some(sign * hours * 3600);
                            // Don't set tzname for GMT+N since it's not actually GMT
                            return result;
                        }
                    }
                }
            }
        }

        result
    }

    /// Recombine skipped tokens.
    fn recombine_skipped(&self, tokens: &[String], skipped_idxs: &[usize]) -> Vec<String> {
        let mut skipped_tokens: Vec<String> = Vec::new();
        let mut sorted_idxs: Vec<usize> = Vec::with_capacity(skipped_idxs.len());

        // Copy indices
        let n = skipped_idxs.len();
        let mut i = 0usize;
        while i < n {
            sorted_idxs.push(skipped_idxs[i]);
            i += 1;
        }

        // Sort indices (simple bubble sort for small arrays)
        let m = sorted_idxs.len();
        let mut i = 0usize;
        while i < m {
            let mut j = 0usize;
            while j < m - 1 - i {
                if sorted_idxs[j] > sorted_idxs[j + 1] {
                    let tmp = sorted_idxs[j];
                    sorted_idxs[j] = sorted_idxs[j + 1];
                    sorted_idxs[j + 1] = tmp;
                }
                j += 1;
            }
            i += 1;
        }

        let mut i = 0usize;
        while i < m {
            let idx = sorted_idxs[i];
            if i > 0 && idx == sorted_idxs[i - 1] + 1 {
                // Adjacent to previous
                let last_idx = skipped_tokens.len() - 1;
                let token_str = &tokens[idx];
                skipped_tokens[last_idx].push_str(token_str);
            } else {
                skipped_tokens.push(tokens[idx].clone());
            }
            i += 1;
        }

        skipped_tokens
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_iso_date() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("2024-01-15", None, None, false, false)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    #[test]
    fn test_parse_us_date() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("01/15/2024", None, None, false, false)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    #[test]
    fn test_parse_european_date() {
        let parser = Parser::new(true, false); // dayfirst=true
        let (res, _) = parser
            .parse("15/01/2024", None, None, false, false)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    #[test]
    fn test_parse_named_month() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("Jan 15, 2024", None, None, false, false)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    #[test]
    fn test_parse_datetime() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("2024-01-15 10:30:45", None, None, false, false)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
        assert_eq!(res.hour, Some(10));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(45));
    }

    #[test]
    fn test_parse_time_with_ampm() {
        let parser = Parser::default();
        let (res, _) = parser.parse("10:30 PM", None, None, false, false).unwrap();
        assert_eq!(res.hour, Some(22));
        assert_eq!(res.minute, Some(30));
    }

    #[test]
    fn test_parse_timezone() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("2024-01-15 10:30:00 UTC", None, None, false, false)
            .unwrap();
        assert_eq!(res.hour, Some(10));
        assert_eq!(res.tzname, Some("UTC".to_string()));
        assert_eq!(res.tzoffset, Some(0));
    }

    #[test]
    fn test_parse_timezone_offset() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("2024-01-15 10:30:00-05:00", None, None, false, false)
            .unwrap();
        assert_eq!(res.hour, Some(10));
        assert_eq!(res.tzoffset, Some(-5 * 3600));
    }

    #[test]
    fn test_parse_yyyymmdd() {
        let parser = Parser::default();
        let (res, _) = parser.parse("20240115", None, None, false, false).unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    #[test]
    fn test_parse_microseconds() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("10:30:45.123456", None, None, false, false)
            .unwrap();
        assert_eq!(res.hour, Some(10));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(45));
        assert_eq!(res.microsecond, Some(123456));
    }

    #[test]
    fn test_parse_weekday() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("Monday Jan 15, 2024", None, None, false, false)
            .unwrap();
        assert_eq!(res.weekday, Some(0)); // Monday = 0
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
        assert_eq!(res.year, Some(2024));
    }

    #[test]
    fn test_fuzzy_parse() {
        let parser = Parser::default();
        let (res, tokens) = parser
            .parse("Today is January 15, 2024 at 10:30", None, None, true, true)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
        assert_eq!(res.hour, Some(10));
        assert_eq!(res.minute, Some(30));
        assert!(tokens.is_some());
    }

    #[test]
    fn test_two_digit_year() {
        let parser = Parser::default();
        let (res, _) = parser.parse("01/15/24", None, None, false, false).unwrap();
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
        // Year should be converted to 2024
        assert!(res.year.unwrap() >= 2000);
    }

    #[test]
    fn test_parse_hms_format() {
        let parser = Parser::default();
        let (res, _) = parser.parse("2h30m45s", None, None, false, false).unwrap();
        assert_eq!(res.hour, Some(2));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(45));
    }

    // Tests for parse_time_only()

    #[test]
    fn test_time_only_compact_hhmm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("0930").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(0));
    }

    #[test]
    fn test_time_only_compact_hhmmss() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
    }

    #[test]
    fn test_time_only_compact_with_dot_fraction() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015.751").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    #[test]
    fn test_time_only_compact_with_comma_fraction() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015,751").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    #[test]
    fn test_time_only_compact_pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("0930 PM").unwrap();
        assert_eq!(res.hour, Some(21));
        assert_eq!(res.minute, Some(30));
    }

    #[test]
    fn test_time_only_compact_with_fraction_pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015,751 PM").unwrap();
        assert_eq!(res.hour, Some(21));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    #[test]
    fn test_time_only_12am_midnight() {
        let parser = Parser::default();
        let res = parser.parse_time_only("1200 AM").unwrap();
        assert_eq!(res.hour, Some(0)); // 12 AM = midnight
        assert_eq!(res.minute, Some(0));
    }

    #[test]
    fn test_time_only_12pm_noon() {
        let parser = Parser::default();
        let res = parser.parse_time_only("1200 PM").unwrap();
        assert_eq!(res.hour, Some(12)); // 12 PM = noon
        assert_eq!(res.minute, Some(0));
    }

    #[test]
    fn test_time_only_separated_colon() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
    }

    #[test]
    fn test_time_only_separated_dot() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9.30").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
    }

    #[test]
    fn test_time_only_separated_with_seconds() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30:15").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
    }

    #[test]
    fn test_time_only_separated_dot_seconds() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9.30.15").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
    }

    #[test]
    fn test_time_only_separated_with_microseconds() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30:15.751").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    #[test]
    fn test_time_only_separated_pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30 PM").unwrap();
        assert_eq!(res.hour, Some(21));
        assert_eq!(res.minute, Some(30));
    }

    #[test]
    fn test_time_only_separated_12pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("12:00 PM").unwrap();
        assert_eq!(res.hour, Some(12)); // 12 PM = noon
        assert_eq!(res.minute, Some(0));
    }

    #[test]
    fn test_time_only_invalid_hour() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("9930").is_err());
    }

    #[test]
    fn test_time_only_invalid_minute() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("0970").is_err());
    }

    #[test]
    fn test_time_only_invalid_3_digits() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("930").is_err());
    }

    #[test]
    fn test_time_only_invalid_5_digits() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("09301").is_err());
    }
}
