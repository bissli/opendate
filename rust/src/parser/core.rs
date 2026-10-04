//! Core datetime parser - port of dateutil.parser.parser.

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

/// True when every byte in `bytes[start..end]` is an ASCII digit, and for an
/// empty range.
fn all_ascii_digits(bytes: &[u8], start: usize, end: usize) -> bool {
    let mut i = start;
    while i < end {
        if !(bytes[i] >= b'0' && bytes[i] <= b'9') {
            return false;
        }
        i += 1;
    }
    true
}

/// True when every byte of `s` is an ASCII digit, and for an empty string.
fn str_all_digits(s: &str) -> bool {
    let bytes = s.as_bytes();
    let n = bytes.len();
    all_ascii_digits(bytes, 0, n)
}

/// True when `s` holds at least one ASCII uppercase letter, no ASCII
/// lowercase letter and no non-ASCII byte. Other ASCII bytes are ignored,
/// so "GMT3" is true and "\u{c9}ST" is false.
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
        } else if (c >= b'a' && c <= b'z') || !c.is_ascii() {
            return false;
        }
        i += 1;
    }
    has_letter
}

/// Decimal value of `s`, which holds only ASCII digits. An empty string
/// gives 0.
///
/// # Errors
/// `ParserError::ParseError` when `s` holds any other byte, a sign included,
/// or its value is past `u32::MAX`.
fn parse_str_u32(s: &str) -> Result<u32, ParserError> {
    let bytes = s.as_bytes();
    let mut result = 0u32;
    let mut i = 0usize;
    while i < bytes.len() {
        let c = bytes[i];
        if c >= b'0' && c <= b'9' {
            result = result
                .checked_mul(10)
                .and_then(|r| r.checked_add((c - b'0') as u32))
                .ok_or_else(|| ParserError::ParseError(format!("Out of range: {}", s)))?;
        } else {
            return Err(ParserError::ParseError("Invalid digit".to_string()));
        }
        i += 1;
    }
    Ok(result)
}

/// Decimal value of `s` after one optional leading '+' or '-'. A lone sign
/// gives 0.
///
/// # Errors
/// `ParserError::ParseError` when `s` is empty, holds a non-digit after the
/// sign, or its value is outside the `i32` range.
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
            let digit = (c - b'0') as i32;
            let signed_digit = if negative { -digit } else { digit };
            result = result
                .checked_mul(10)
                .and_then(|r| r.checked_add(signed_digit))
                .ok_or_else(|| ParserError::ParseError(format!("Out of range: {}", s)))?;
        } else {
            return Err(ParserError::ParseError(format!("Invalid digit in: {}", s)));
        }
        i += 1;
    }

    Ok(result)
}

/// Value of `s` as `str::parse::<f64>` reads it, so "inf", "NaN" and "1e3"
/// count as numbers too.
///
/// # Errors
/// `ParserError::ParseError` when `s` is not a float literal.
fn parse_str_f64(s: &str) -> Result<f64, ParserError> {
    s.parse::<f64>()
        .map_err(|_| ParserError::ParseError(format!("Invalid number: {}", s)))
}

/// Byte index of the first `c` in `s`, or None. `c` must be ASCII, since
/// the match uses only its low byte.
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

/// Byte index of the first byte of `s` that equals any of `chars`, or None.
/// Each of `chars` must be ASCII.
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

/// True when `s` holds the ASCII char `c`.
fn contains_char(s: &str, c: char) -> bool {
    find_char(s, c).is_some()
}

/// True when the last bytes of `s` equal `suffix`.
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

/// Copy of `s` with ASCII a-z mapped to A-Z. Every other byte becomes the
/// char of that code point, so a non-ASCII `s` changes byte length.
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

/// `s[start..end]` by byte offset, with `end` clamped to `s.len()` and
/// `start` to `end`. An offset inside a multibyte char gives "".
fn substr_range(s: &str, start: usize, end: usize) -> &str {
    let bytes = s.as_bytes();
    let actual_end = if end > bytes.len() { bytes.len() } else { end };
    let actual_start = if start > actual_end {
        actual_end
    } else {
        start
    };
    s.get(actual_start..actual_end).unwrap_or("")
}

/// Fields of `s` between each `delim`, empty fields kept, so "" gives [""].
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

    if start <= n {
        result.push(substr_range(s, start, n));
    }

    result
}

/// `s` without leading and trailing space, tab, CR and LF bytes.
fn trim_str(s: &str) -> &str {
    let bytes = s.as_bytes();
    let n = bytes.len();
    if n == 0 {
        return s;
    }

    let mut start = 0usize;
    while start < n {
        let c = bytes[start];
        if c != b' ' && c != b'\t' && c != b'\n' && c != b'\r' {
            break;
        }
        start += 1;
    }

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

/// The first `target_len` bytes of `s`, right-padded with '0' to that
/// length.
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
    /// Parser whose `dayfirst` and `yearfirst` apply when `parse` gets None.
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
    /// - HHMM: "0930" -> 09:30
    /// - HHMMSS: "093015" -> 09:30:15
    /// - HHMMSS with fraction: "093015.751" or "093015,751" -> 09:30:15.751
    /// - Separated: "9:30", "9.30", "9:30:15", "9.30.15"
    /// - With AM/PM: "0930 PM", "9:30 AM", "12:00 PM"
    ///
    /// # Returns
    /// Hour, minute, second and microsecond set, and the date fields None.
    ///
    /// # Errors
    /// `ParserError::ParseError` for an empty or unknown format, an hour past
    /// 23 (12 with AM/PM), or a minute or second past 59, all-digit seconds
    /// past `u32::MAX` included.
    pub fn parse_time_only(&self, timestr: &str) -> Result<ParseResult, ParserError> {
        let s = trim_str(timestr);
        if s.len() == 0 {
            return Err(ParserError::ParseError("Empty time string".to_string()));
        }

        let (time_part, ampm) = self.extract_ampm_suffix(s);

        if let Some(result) = self.try_parse_compact_time(time_part, ampm)? {
            return Ok(result);
        }

        if let Some(result) = self.try_parse_separated_time(time_part, ampm)? {
            return Ok(result);
        }

        Err(ParserError::ParseError(format!(
            "Invalid time format: {}",
            timestr
        )))
    }

    /// `s` without a trailing " AM" or " PM" in any case, and Some(0) for AM,
    /// Some(1) for PM, or None when neither ends `s`.
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

    /// Read HHMM or HHMMSS, with an optional '.' or ',' fraction of a second.
    ///
    /// # Arguments
    /// * `s` - Time text without its AM/PM suffix
    /// * `ampm` - Some(0) for AM, Some(1) for PM. Either caps the hour at 12.
    ///
    /// # Returns
    /// `Ok(None)` when `s` is not 4 or 6 digits before the fraction. A
    /// fraction that is not all digits gives 0 microseconds.
    ///
    /// # Errors
    /// `ParserError::ParseError` when the hour is past 23 (12 with `ampm`),
    /// or the minute or second past 59.
    fn try_parse_compact_time(
        &self,
        s: &str,
        ampm: Option<u32>,
    ) -> Result<Option<ParseResult>, ParserError> {
        let delims: [char; 2] = ['.', ','];
        let (digits_part, frac_part) = if let Some(pos) = find_any_char(s, &delims) {
            (
                substr_range(s, 0, pos),
                Some(substr_range(s, pos + 1, s.len())),
            )
        } else {
            (s, None)
        };

        if !str_all_digits(digits_part) {
            return Ok(None);
        }

        let len = digits_part.len();
        if len != 4 && len != 6 {
            return Ok(None);
        }

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

        let max_hour = if ampm.is_some() { 12 } else { 23 };
        if hour > max_hour || minute > 59 || second > 59 {
            return Err(ParserError::ParseError(format!(
                "Time values out of range: {:02}:{:02}:{:02}",
                hour, minute, second
            )));
        }

        let microsecond = if let Some(frac) = frac_part {
            let frac_len = frac.len();
            let take_len = if frac_len < 6 { frac_len } else { 6 };
            let padded = pad_right_zeros(substr_range(frac, 0, take_len), 6);
            parse_str_u32(&padded).unwrap_or(0)
        } else {
            0
        };

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

    /// Read H:MM or H.MM, with a one- or two-digit hour, an optional :SS or
    /// .SS, and a fraction of a second.
    ///
    /// # Arguments
    /// * `s` - Time text without its AM/PM suffix
    /// * `ampm` - Some(0) for AM, Some(1) for PM. Either caps the hour at 12.
    ///
    /// # Returns
    /// `Ok(None)` when `s` does not have that shape.
    ///
    /// # Errors
    /// `ParserError::ParseError` when the hour is past 23 (12 with `ampm`),
    /// or the minute or second past 59, all-digit seconds past `u32::MAX`
    /// included.
    fn try_parse_separated_time(
        &self,
        s: &str,
        ampm: Option<u32>,
    ) -> Result<Option<ParseResult>, ParserError> {
        let tokens: Vec<String> = Tokenizer::split(s);

        let tokens_len = tokens.len();
        if tokens_len == 0 {
            return Ok(None);
        }

        let hour: u32;
        let minute: u32;
        let mut second: u32 = 0;
        let mut microsecond: u32 = 0;

        // The tokenizer keeps H.MM, such as "9.30", as one token.
        if contains_char(&tokens[0], '.') && tokens[0].as_bytes()[0] != b'.' {
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

                    if parts_len >= 3 {
                        let (sec, micro) = self.parsems(parts[2])?;
                        second = sec;
                        microsecond = micro;
                    }

                    let max_hour = if ampm.is_some() { 12 } else { 23 };
                    if hour > max_hour || minute > 59 || second > 59 {
                        return Err(ParserError::ParseError(format!(
                            "Time values out of range: {:02}:{:02}:{:02}",
                            hour, minute, second
                        )));
                    }

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

        if tokens_len < 3 {
            return Ok(None);
        }

        let hour_str = &tokens[0];
        let hour_str_len = hour_str.len();
        if !str_all_digits(hour_str) || hour_str_len > 2 {
            return Ok(None);
        }

        let sep = &tokens[1];
        if sep != ":" && sep != "." {
            return Ok(None);
        }

        let min_str = &tokens[2];
        let min_str_len = min_str.len();
        if !str_all_digits(min_str) || min_str_len != 2 {
            return Ok(None);
        }

        hour = parse_str_u32(hour_str).unwrap_or(0);
        minute = parse_str_u32(min_str).unwrap_or(0);

        if tokens_len >= 5 && (tokens[3] == ":" || tokens[3] == ".") {
            let sec_str = &tokens[4];
            let (sec, micro) = self.parsems(sec_str)?;
            second = sec;
            microsecond = micro;
        }

        let max_hour = if ampm.is_some() { 12 } else { 23 };
        if hour > max_hour || minute > 59 || second > 59 {
            return Err(ParserError::ParseError(format!(
                "Time values out of range: {:02}:{:02}:{:02}",
                hour, minute, second
            )));
        }

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
    /// * `fuzzy` - Skip a token that fits no field instead of failing
    /// * `fuzzy_with_tokens` - If true, return skipped tokens. Implies
    ///   `fuzzy`.
    ///
    /// # Returns
    /// The parsed fields, and the skipped tokens when `fuzzy_with_tokens` is
    /// true, else None.
    ///
    /// # Errors
    /// `ParserError::ParseError` for a token that fits no field outside fuzzy
    /// mode, a bad timezone offset, a date that does not resolve, or an
    /// all-digit seconds value past `u32::MAX`.
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

    /// Fields of `timestr` and the tokens fuzzy mode skipped, with the
    /// `parse` overrides already resolved.
    ///
    /// # Errors
    /// As `parse`.
    fn parse_inner(
        &self,
        timestr: &str,
        dayfirst: bool,
        yearfirst: bool,
        fuzzy: bool,
    ) -> Result<(ParseResult, Vec<String>), ParserError> {
        if Self::looks_like_iso(timestr) {
            if let Ok(result) = super::IsoParser::new().isoparse(timestr) {
                return Ok((result, Vec::new()));
            }
        }

        let mut res = ParseResult::default();
        let tokens: Vec<String> = Tokenizer::split(timestr);
        let mut skipped_idxs: Vec<usize> = Vec::new();
        let mut ymd = Ymd::new();
        let mut flip_next_sign = false;

        let len_l = tokens.len();
        let mut i = 0usize;

        while i < len_l {
            let token = &tokens[i];

            if parse_str_f64(token).is_ok() {
                i = self.parse_numeric_token(&tokens, i, &mut ymd, &mut res, fuzzy)?;
            } else if let Some(weekday) = self.info.weekday(token) {
                res.weekday = Some(weekday);
            } else if let Some(month) = self.info.month(token) {
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
            } else if let Some(ampm_val) = self.info.ampm(token) {
                let val_is_ampm = self.ampm_valid(res.hour, res.ampm, fuzzy);

                if val_is_ampm {
                    if let Some(hour) = res.hour {
                        res.hour = Some(self.adjust_ampm(hour, ampm_val));
                    }
                    res.ampm = Some(ampm_val);
                } else if fuzzy {
                    skipped_idxs.push(i);
                }
            } else if self.could_be_tzname(res.hour, &res.tzname, res.tzoffset, token) {
                res.tzname = Some(token.clone());
                res.tzoffset = self.info.tzoffset(token);

                // "GMT+3" means "my time +3 is GMT", so the sign of
                // the offset that follows is reversed.
                if i + 1 < len_l && (tokens[i + 1] == "+" || tokens[i + 1] == "-") {
                    flip_next_sign = true;
                    res.tzoffset = None;
                    if self.info.utczone(token) {
                        // In GMT+3 the zone itself is not GMT.
                        res.tzname = None;
                    }
                }
            } else if res.hour.is_some() && (token == "+" || token == "-") {
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

                    // -0300 (BRST)
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
            } else if self.info.jump(token) || fuzzy {
                skipped_idxs.push(i);
            } else {
                return Err(ParserError::ParseError(format!(
                    "Unknown string format: {}",
                    timestr
                )));
            }

            i += 1;
        }

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

        if let Some(y) = res.year {
            res.year = Some(self.info.convertyear(y, res.century_specified));
        }

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

        let skipped_tokens = self.recombine_skipped(&tokens, &skipped_idxs);

        Ok((res, skipped_tokens))
    }

    /// True for the unambiguous ISO 8601 shapes the ISO parser tries first:
    /// - YYYY-...
    /// - YYYYMMDD exactly
    /// - YYYYMMDDT...
    ///
    /// False for:
    /// - YYYY alone (needs default filling from general parser)
    /// - 12/14 digit compact formats without T (general parser handles these)
    fn looks_like_iso(s: &str) -> bool {
        let bytes = s.as_bytes();
        let n = bytes.len();

        if n < 5 {
            return false;
        }

        if !all_ascii_digits(bytes, 0, 4) {
            return false;
        }

        if bytes[4] == b'-' {
            return true;
        }

        if n >= 8 && all_ascii_digits(bytes, 0, 8) {
            if n == 8 {
                return true;
            }
            if n > 8 && bytes[8] == b'T' {
                return true;
            }
        }

        false
    }

    /// Place the number at `tokens[idx]` in a date or time field, reading
    /// the separators and labels that follow it.
    ///
    /// # Arguments
    /// * `tokens` - All tokens of the input
    /// * `idx` - Index of the numeric token
    /// * `ymd` - Date members found so far, appended to
    /// * `res` - Time fields found so far, set in place
    /// * `fuzzy` - Skip a number that fits no field instead of failing
    ///
    /// # Returns
    /// Index of the last token consumed. The caller resumes one past it.
    ///
    /// # Errors
    /// `ParserError::ParseError` for a number that fits no field outside
    /// fuzzy mode, a word after a date separator that is not a month name,
    /// a date member `ymd` rejects, or an all-digit seconds value past
    /// `u32::MAX`.
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
                let (sec, micro) = self.parsems(substr_range(s, 4, s.len()))?;
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
                let (sec, micro) = self.parsems(&tokens[idx + 4])?;
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
                let int_val = value as i32;
                let could_be_date_component =
                    (int_val >= 0 && int_val <= 99) || (int_val >= 1000 && int_val <= 9999);

                if could_be_date_component {
                    ymd.append(value as i32, None)?;
                } else if !fuzzy {
                    return Err(ParserError::ParseError(format!(
                        "Invalid date component: {}",
                        value_repr
                    )));
                }
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

    /// Index of the h/m/s label beside the number at `idx`, or None.
    /// `allow_jump` also accepts a label one space after the number.
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
            Some(idx - 2)
        } else {
            None
        }
    }

    /// Index of the last token consumed, and the field code of the number
    /// at `idx`: 0 hour, 1 minute, 2 second. A code of 3 names no field.
    fn parse_hms(&self, idx: usize, tokens: &[String], hms_idx: usize) -> (usize, Option<u32>) {
        let hms = self.info.hms(&tokens[hms_idx]);
        let new_idx = if hms_idx > idx { hms_idx } else { idx };

        // A label behind idx names the number before, so step up one.
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

    /// Set the field `hms` names (0 hour, 1 minute, 2 second) from
    /// `value_repr`, its fraction going to the next smaller field. Any
    /// other code changes nothing.
    ///
    /// # Errors
    /// `ParserError::ParseError` when an all-digit seconds value is past
    /// `u32::MAX`.
    fn assign_hms(
        &self,
        res: &mut ParseResult,
        value_repr: &str,
        hms: u32,
    ) -> Result<(), ParserError> {
        let value: f64 = parse_str_f64(value_repr).unwrap_or(0.0);

        match hms {
            0 => {
                res.hour = Some(value as u32);
                let fract = value - (value as u32) as f64;
                if fract != 0.0 {
                    res.minute = Some((60.0 * fract) as u32);
                }
            }
            1 => {
                let (minute, second) = self.parse_min_sec(value);
                res.minute = Some(minute);
                if let Some(s) = second {
                    res.second = Some(s);
                }
            }
            2 => {
                let (sec, micro) = self.parsems(value_repr)?;
                res.second = Some(sec);
                res.microsecond = Some(micro);
            }
            _ => {}
        }

        Ok(())
    }

    /// True when `token` can name the zone of a time with no zone yet: an
    /// hour is set, no name or offset is set, and `token` is at most 5
    /// bytes and either uppercase or a UTC alias.
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

    /// True when an AM/PM token can apply: an hour of 0 to 12 is set, and
    /// in fuzzy mode no AM/PM is set yet.
    ///
    /// Outside fuzzy mode a missing hour or one past 12 gives false where
    /// dateutil raises, so the token is dropped without an error.
    fn ampm_valid(&self, hour: Option<u32>, ampm: Option<u32>, fuzzy: bool) -> bool {
        if fuzzy && ampm.is_some() {
            return false;
        }

        match hour {
            None => false,
            Some(h) => h <= 12,
        }
    }

    /// 24-hour value of `hour`, with `ampm` 0 for AM and 1 for PM. 12 AM
    /// gives 0, and an hour past 12 passes through.
    fn adjust_ampm(&self, hour: u32, ampm: u32) -> u32 {
        if hour < 12 && ampm == 1 {
            hour + 12
        } else if hour == 12 && ampm == 0 {
            0
        } else {
            hour
        }
    }

    /// Whole minutes of `value`, and its fraction as whole seconds
    /// (truncated), or None when it has no fraction.
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

    /// Seconds and microseconds of "SS[.ffffff]". The fraction is cut or
    /// zero-padded to 6 digits, and a part that is not all digits reads 0.
    ///
    /// # Errors
    /// `ParserError::ParseError` when the seconds are all digits but past
    /// `u32::MAX`.
    fn parsems(&self, value: &str) -> Result<(u32, u32), ParserError> {
        let parse_seconds = |s: &str| match parse_str_u32(s) {
            Err(e) if str_all_digits(s) => Err(e),
            parsed => Ok(parsed.unwrap_or(0)),
        };
        if !contains_char(value, '.') {
            Ok((parse_seconds(value)?, 0))
        } else {
            let parts: Vec<&str> = split_char(value, '.');
            let parts_len = parts.len();
            let seconds: u32 = parse_seconds(parts[0])?;
            let frac = if parts_len > 1 { parts[1] } else { "0" };
            let padded = pad_right_zeros(frac, 6);
            let microseconds: u32 = parse_str_u32(substr_range(&padded, 0, 6)).unwrap_or(0);
            Ok((seconds, microseconds))
        }
    }

    /// Skipped tokens in input order, each run of adjacent indices joined
    /// into one string.
    fn recombine_skipped(&self, tokens: &[String], skipped_idxs: &[usize]) -> Vec<String> {
        let mut skipped_tokens: Vec<String> = Vec::new();
        let mut sorted_idxs: Vec<usize> = Vec::with_capacity(skipped_idxs.len());

        let n = skipped_idxs.len();
        let mut i = 0usize;
        while i < n {
            sorted_idxs.push(skipped_idxs[i]);
            i += 1;
        }

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

    /// Verify a hyphenated ISO date yields its year, month and day.
    ///
    /// Mutation: month and day swapped in the ISO result.
    /// Oracle: hand-read fields of "2024-01-15".
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

    /// Verify a slash date reads month first by default.
    ///
    /// Mutation: '/' dropped from the date separators in parse_numeric_token.
    /// Oracle: hand-read US order of "01/15/2024".
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

    /// Verify a slash date with a day past 12 parses under dayfirst.
    ///
    /// Mutation: the member after the second '/' dropped, leaving no year.
    /// Oracle: hand-read fields of "15/01/2024".
    #[test]
    fn test_parse_european_date() {
        let parser = Parser::new(true, false);
        let (res, _) = parser
            .parse("15/01/2024", None, None, false, false)
            .unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    /// Verify a month name fills the month and the numbers fill day and year.
    ///
    /// Mutation: the month name appended without its 'M' label, so the
    ///   resolver misplaces it.
    /// Oracle: hand-read fields of "Jan 15, 2024".
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

    /// Verify a space-separated ISO datetime keeps its time fields.
    ///
    /// Mutation: seconds dropped from the ISO result.
    /// Oracle: hand-read fields of "2024-01-15 10:30:45".
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

    /// Verify PM moves an hour before noon into the afternoon.
    ///
    /// Mutation: adjust_ampm adding 12 for AM in place of PM.
    /// Oracle: 10:30 PM is 22:30.
    #[test]
    fn test_parse_time_with_ampm() {
        let parser = Parser::default();
        let (res, _) = parser.parse("10:30 PM", None, None, false, false).unwrap();
        assert_eq!(res.hour, Some(22));
        assert_eq!(res.minute, Some(30));
    }

    /// Verify a trailing UTC name sets the name and a zero offset.
    ///
    /// Mutation: a UTC alias left with no offset.
    /// Oracle: UTC is offset 0 by definition.
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

    /// Verify a -05:00 suffix gives a negative offset in seconds.
    ///
    /// Mutation: the offset sign flipped, or minutes read as hours.
    /// Oracle: hand-computed -5 * 3600.
    #[test]
    fn test_parse_timezone_offset() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("2024-01-15 10:30:00-05:00", None, None, false, false)
            .unwrap();
        assert_eq!(res.hour, Some(10));
        assert_eq!(res.tzoffset, Some(-5 * 3600));
    }

    /// Verify an 8-digit compact date splits into year, month and day.
    ///
    /// Mutation: month and day byte slices swapped.
    /// Oracle: hand-read fields of "20240115".
    #[test]
    fn test_parse_yyyymmdd() {
        let parser = Parser::default();
        let (res, _) = parser.parse("20240115", None, None, false, false).unwrap();
        assert_eq!(res.year, Some(2024));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
    }

    /// Verify a six-digit fraction of a second becomes microseconds.
    ///
    /// Mutation: parsems cutting the fraction short or padding it to the
    ///   wrong width.
    /// Oracle: 0.123456 s is 123456 microseconds.
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

    /// Verify a word with a non-ASCII letter is not read as a zone name.
    ///
    /// Mutation: all_ascii_uppercase skipping non-ASCII bytes, so
    /// "\u{c9}ST" counts as all upper case.
    /// Oracle: dateutil's could_be_tzname requires every char in
    /// string.ascii_uppercase; dateutil.parser.parse raises 'Unknown
    /// string format' on "Jan 15 2024 10:30 \u{c9}ST".
    #[test]
    fn test_parse_rejects_non_ascii_zone_name() {
        let parser = Parser::default();
        assert!(parser
            .parse("Jan 15 2024 10:30 \u{c9}ST", None, None, false, false)
            .is_err());
        let (res, _) = parser
            .parse("Jan 15 2024 10:30 EST", None, None, false, false)
            .unwrap();
        assert_eq!(res.tzname.as_deref(), Some("EST"));
    }

    /// Verify a seconds token past u32 is an error.
    ///
    /// Mutation: `unwrap_or(0)` on the overflowed seconds in parsems,
    /// which reads them as :00.
    /// Oracle: dateutil.parser.parse raises OverflowError on
    /// "10:30:4294967297" and "2024-01-15 10:30:99999999999".
    #[test]
    fn test_parse_seconds_overflow_is_error() {
        let parser = Parser::default();
        for text in ["10:30:4294967297", "2024-01-15 10:30:99999999999"] {
            assert!(
                parser.parse(text, None, None, false, false).is_err(),
                "{text}"
            );
        }
    }

    /// Verify a weekday name sets the weekday next to the date fields.
    ///
    /// Mutation: weekday index off by one, Monday read as 1.
    /// Oracle: Python weekday numbering, where Monday is 0.
    #[test]
    fn test_parse_weekday() {
        let parser = Parser::default();
        let (res, _) = parser
            .parse("Monday Jan 15, 2024", None, None, false, false)
            .unwrap();
        assert_eq!(res.weekday, Some(0));
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
        assert_eq!(res.year, Some(2024));
    }

    /// Verify fuzzy mode skips words and still reads the date and time.
    ///
    /// Mutation: a skipped word raising in fuzzy mode, or fuzzy_with_tokens
    ///   returning no tokens.
    /// Oracle: hand-read fields of the sentence.
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

    /// Verify a two-digit year lands in the current century window.
    ///
    /// Mutation: convertyear skipped, leaving the year at 24.
    /// Oracle: the window places 24 at 2024, so any year at or past 2000.
    #[test]
    fn test_two_digit_year() {
        let parser = Parser::default();
        let (res, _) = parser.parse("01/15/24", None, None, false, false).unwrap();
        assert_eq!(res.month, Some(1));
        assert_eq!(res.day, Some(15));
        assert!(res.year.unwrap() >= 2000);
    }

    /// Verify h, m and s labels fill hour, minute and second.
    ///
    /// Mutation: the minute and second field codes swapped in assign_hms.
    /// Oracle: hand-read fields of "2h30m45s".
    #[test]
    fn test_parse_hms_format() {
        let parser = Parser::default();
        let (res, _) = parser.parse("2h30m45s", None, None, false, false).unwrap();
        assert_eq!(res.hour, Some(2));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(45));
    }

    // Tests for parse_time_only()

    /// Verify HHMM splits into hour and minute with second 0.
    ///
    /// Mutation: minute sliced from bytes 0..2 in place of 2..4.
    /// Oracle: hand-read fields of "0930".
    #[test]
    fn test_time_only_compact_hhmm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("0930").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(0));
    }

    /// Verify HHMMSS reads the last two digits as seconds.
    ///
    /// Mutation: seconds read from the wrong byte slice.
    /// Oracle: hand-read fields of "093015".
    #[test]
    fn test_time_only_compact_hhmmss() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
    }

    /// Verify a '.' fraction on HHMMSS is right-padded to microseconds.
    ///
    /// Mutation: the fraction not padded to 6 digits, giving 751.
    /// Oracle: 0.751 s is 751000 microseconds.
    #[test]
    fn test_time_only_compact_with_dot_fraction() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015.751").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    /// Verify a ',' fraction on HHMMSS reads the same as a '.' fraction.
    ///
    /// Mutation: ',' dropped from the fraction delimiters.
    /// Oracle: 0.751 s is 751000 microseconds.
    #[test]
    fn test_time_only_compact_with_comma_fraction() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015,751").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    /// Verify PM applies to a compact HHMM time.
    ///
    /// Mutation: the compact path ignoring its ampm argument.
    /// Oracle: 9:30 PM is 21:30.
    #[test]
    fn test_time_only_compact_pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("0930 PM").unwrap();
        assert_eq!(res.hour, Some(21));
        assert_eq!(res.minute, Some(30));
    }

    /// Verify the PM suffix comes off before the fraction is read.
    ///
    /// Mutation: " PM" left on the fraction, so microseconds read 0.
    /// Oracle: 9:30:15.751 PM is 21:30:15.751000.
    #[test]
    fn test_time_only_compact_with_fraction_pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("093015,751 PM").unwrap();
        assert_eq!(res.hour, Some(21));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    /// Verify 12 AM maps to hour 0.
    ///
    /// Mutation: the 12 AM to 0 rule dropped from adjust_ampm.
    /// Oracle: 12 AM is midnight, hour 0.
    #[test]
    fn test_time_only_12am_midnight() {
        let parser = Parser::default();
        let res = parser.parse_time_only("1200 AM").unwrap();
        assert_eq!(res.hour, Some(0));
        assert_eq!(res.minute, Some(0));
    }

    /// Verify 12 PM stays at hour 12.
    ///
    /// Mutation: adjust_ampm adding 12 to hour 12, giving 24.
    /// Oracle: 12 PM is noon, hour 12.
    #[test]
    fn test_time_only_12pm_noon() {
        let parser = Parser::default();
        let res = parser.parse_time_only("1200 PM").unwrap();
        assert_eq!(res.hour, Some(12));
        assert_eq!(res.minute, Some(0));
    }

    /// Verify H:MM accepts a one-digit hour.
    ///
    /// Mutation: the hour length check written as != 2.
    /// Oracle: hand-read fields of "9:30".
    #[test]
    fn test_time_only_separated_colon() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
    }

    /// Verify H.MM, kept as one token, reads as hour and minute.
    ///
    /// Mutation: the single-token H.MM branch dropped.
    /// Oracle: hand-read fields of "9.30".
    #[test]
    fn test_time_only_separated_dot() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9.30").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
    }

    /// Verify H:MM:SS reads the seconds.
    ///
    /// Mutation: the seconds check requiring more than 5 tokens.
    /// Oracle: hand-read fields of "9:30:15".
    #[test]
    fn test_time_only_separated_with_seconds() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30:15").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
    }

    /// Verify H.MM.SS reads the third dotted part as seconds.
    ///
    /// Mutation: parts[2] ignored in the H.MM branch.
    /// Oracle: hand-read fields of "9.30.15".
    #[test]
    fn test_time_only_separated_dot_seconds() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9.30.15").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
    }

    /// Verify a fraction on H:MM:SS becomes microseconds.
    ///
    /// Mutation: parsems not padding the fraction to 6 digits.
    /// Oracle: 0.751 s is 751000 microseconds.
    #[test]
    fn test_time_only_separated_with_microseconds() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30:15.751").unwrap();
        assert_eq!(res.hour, Some(9));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(15));
        assert_eq!(res.microsecond, Some(751000));
    }

    /// Verify PM applies to a separated H:MM time.
    ///
    /// Mutation: the separated path ignoring its ampm argument.
    /// Oracle: 9:30 PM is 21:30.
    #[test]
    fn test_time_only_separated_pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("9:30 PM").unwrap();
        assert_eq!(res.hour, Some(21));
        assert_eq!(res.minute, Some(30));
    }

    /// Verify 12:00 PM passes the 12-hour cap and stays at 12.
    ///
    /// Mutation: the AM/PM hour cap set to 11, or 12 PM turned into 24.
    /// Oracle: 12 PM is noon, at the cap of 12.
    #[test]
    fn test_time_only_separated_12pm() {
        let parser = Parser::default();
        let res = parser.parse_time_only("12:00 PM").unwrap();
        assert_eq!(res.hour, Some(12));
        assert_eq!(res.minute, Some(0));
    }

    /// Verify a compact hour past 23 raises.
    ///
    /// Mutation: the hour range check dropped.
    /// Oracle: hour 99 is past the 23 limit.
    #[test]
    fn test_time_only_invalid_hour() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("9930").is_err());
    }

    /// Verify a compact minute past 59 raises.
    ///
    /// Mutation: the minute range check dropped.
    /// Oracle: minute 70 is past the 59 limit.
    #[test]
    fn test_time_only_invalid_minute() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("0970").is_err());
    }

    /// Verify a 3-digit string is not a compact time.
    ///
    /// Mutation: the compact length check accepting 3 digits.
    /// Oracle: only 4 or 6 digits form HHMM or HHMMSS.
    #[test]
    fn test_time_only_invalid_3_digits() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("930").is_err());
    }

    /// Verify a 5-digit string is not a compact time.
    ///
    /// Mutation: the compact length check written as len < 4.
    /// Oracle: only 4 or 6 digits form HHMM or HHMMSS.
    #[test]
    fn test_time_only_invalid_5_digits() {
        let parser = Parser::default();
        assert!(parser.parse_time_only("09301").is_err());
    }

    /// Verify parse_str_u32() and parse_str_i32() reject a value past the
    /// type's range and accept each bound.
    ///
    /// Mutation: unchecked `result * 10 + digit`, which wraps or panics;
    /// or a negative value summed as positive, which rejects i32::MIN.
    /// Oracle: std `str::parse::<u32>` and `str::parse::<i32>`, which
    /// these replaced: Err past the range, Ok at u32::MAX, i32::MAX and
    /// i32::MIN.
    #[test]
    fn test_parse_str_int_overflow() {
        assert_eq!(parse_str_u32("4294967295").ok(), Some(u32::MAX));
        assert!(parse_str_u32("4294967296").is_err());
        assert!(parse_str_u32("99999999999").is_err());
        assert_eq!(parse_str_i32("2147483647").ok(), Some(i32::MAX));
        assert_eq!(parse_str_i32("-2147483648").ok(), Some(i32::MIN));
        assert!(parse_str_i32("2147483648").is_err());
        assert!(parse_str_i32("-2147483649").is_err());
    }

    /// Verify substr_range() never returns a str cut inside a multibyte
    /// char.
    ///
    /// Mutation: `from_utf8_unchecked` on the raw byte range.
    /// Oracle: std `str::from_utf8_unchecked` safety contract, which
    /// requires valid UTF-8; byte 6 of "12345\u{e9}" falls inside the
    /// two-byte char.
    #[test]
    fn test_substr_range_inside_multibyte_char() {
        let cut = substr_range("12345\u{e9}", 0, 6);
        assert!(std::str::from_utf8(cut.as_bytes()).is_ok());
        assert_eq!(substr_range("12345\u{e9}", 0, 7), "12345\u{e9}");
    }
}
