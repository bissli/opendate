//! Core datetime parser - port of dateutil.parser.parser.
//!
//! This module provides the main parsing logic that tokenizes input strings
//! and extracts datetime components.

use super::errors::ParserError;
use super::parserinfo::ParserInfo;
use super::result::ParseResult;
use super::tokenizer::Tokenizer;
use super::ymd::YMD;

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

impl Parser {
    /// Create a new parser with the given settings.
    pub fn new(dayfirst: bool, yearfirst: bool) -> Self {
        Parser {
            info: ParserInfo::new(dayfirst, yearfirst),
        }
    }

    /// Create a new parser with custom ParserInfo.
    pub fn with_info(info: ParserInfo) -> Self {
        Parser { info }
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

        let dayfirst = dayfirst.unwrap_or(self.info.dayfirst);
        let yearfirst = yearfirst.unwrap_or(self.info.yearfirst);

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
        let mut ymd = YMD::new();
        let mut flip_next_sign = false; // For GMT+3 style parsing

        let len_l = tokens.len();
        let mut i = 0;

        while i < len_l {
            let token = &tokens[i];

            // Try to parse as a number
            if let Ok(_value) = token.parse::<f64>() {
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
                        if tokens[i + 4].chars().all(|c| c.is_ascii_digit()) {
                            let value: i32 = tokens[i + 4].parse().unwrap_or(0);
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
                        let h: i32 = tokens[i + 1][..2].parse().unwrap_or(0);
                        let m: i32 = tokens[i + 1][2..].parse().unwrap_or(0);
                        (h, m, 0)
                    } else if i + 2 < len_l && tokens[i + 2] == ":" {
                        // -03:00
                        let h: i32 = tokens[i + 1].parse().unwrap_or(0);
                        let m: i32 = if i + 3 < len_l {
                            tokens[i + 3].parse().unwrap_or(0)
                        } else {
                            0
                        };
                        (h, m, 2)
                    } else if len_li <= 2 {
                        // -[0]3
                        let h: i32 = tokens[i + 1].parse().unwrap_or(0);
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
            // Check jumps
            else if self.info.jump(token) {
                skipped_idxs.push(i);
            } else if fuzzy {
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
        res.month = month.map(|m| m as u32);
        res.day = day.map(|d| d as u32);

        // Validate and convert year
        if let Some(y) = res.year {
            res.year = Some(self.info.convertyear(y, res.century_specified));
        }

        // Normalize timezone info
        if (res.tzoffset == Some(0) && res.tzname.is_none())
            || res.tzname.as_deref() == Some("Z")
            || res.tzname.as_deref() == Some("z")
        {
            res.tzname = Some("UTC".to_string());
            res.tzoffset = Some(0);
        } else if res.tzoffset.is_some()
            && res.tzoffset != Some(0)
            && res.tzname.is_some()
            && self.info.utczone(res.tzname.as_deref().unwrap_or(""))
        {
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

        // Need at least 5 chars for meaningful ISO (YYYY- minimum)
        if bytes.len() < 5 {
            return false;
        }

        // Must start with 4 digits (year)
        if !bytes[0..4].iter().all(|b| b.is_ascii_digit()) {
            return false;
        }

        // Check for ISO separator pattern: YYYY-...
        if bytes[4] == b'-' {
            return true;
        }

        // YYYYMMDD format (exactly 8 digits, or 8 digits + T separator)
        if bytes.len() >= 8 && bytes[0..8].iter().all(|b| b.is_ascii_digit()) {
            // Exactly 8 digits (YYYYMMDD) - use ISO
            if bytes.len() == 8 {
                return true;
            }
            // 8 digits + T separator (YYYYMMDDT...) - use ISO
            if bytes.get(8) == Some(&b'T') {
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
        ymd: &mut YMD,
        res: &mut ParseResult,
        fuzzy: bool,
    ) -> Result<usize, ParserError> {
        let value_repr = &tokens[idx];
        let value: f64 = value_repr.parse().map_err(|_| {
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
            res.hour = Some(s[..2].parse().unwrap_or(0));

            if len_li == 4 {
                res.minute = Some(s[2..].parse().unwrap_or(0));
            }
        } else if len_li == 6 || (len_li > 6 && tokens[idx].find('.') == Some(6)) {
            // YYMMDD or HHMMSS[.ss]
            let s = &tokens[idx];

            if ymd.is_empty() && !tokens[idx].contains('.') {
                ymd.append_str(&s[..2], None)?;
                ymd.append_str(&s[2..4], None)?;
                ymd.append_str(&s[4..], None)?;
            } else {
                // 19990101T235959[.59]
                res.hour = Some(s[..2].parse().unwrap_or(0));
                res.minute = Some(s[2..4].parse().unwrap_or(0));
                let (sec, micro) = self.parsems(&s[4..]);
                res.second = Some(sec);
                res.microsecond = Some(micro);
            }
        } else if len_li == 8 || len_li == 12 || len_li == 14 {
            // YYYYMMDD[HHMMSS]
            let s = &tokens[idx];
            ymd.append_str(&s[..4], Some('Y'))?;
            ymd.append_str(&s[4..6], None)?;
            ymd.append_str(&s[6..8], None)?;

            if len_li > 8 {
                res.hour = Some(s[8..10].parse().unwrap_or(0));
                res.minute = Some(s[10..12].parse().unwrap_or(0));

                if len_li > 12 {
                    res.second = Some(s[12..].parse().unwrap_or(0));
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
            let min_val: f64 = tokens[idx + 2].parse().unwrap_or(0.0);
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
                if tokens[idx + 2].chars().all(|c| c.is_ascii_digit()) {
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
                let could_be_date_component = (1..=31).contains(&int_val)  // day
                    || (1..=12).contains(&int_val)  // month
                    || (0..=99).contains(&int_val)  // 2-digit year
                    || (1000..=9999).contains(&int_val);  // 4-digit year

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
        } else if self.info.ampm(&tokens[idx + 1]).is_some() && (0.0..24.0).contains(&value) {
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
            hms.map(|h| h + 1)
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
        let value: f64 = value_repr.parse().unwrap_or(0.0);

        match hms {
            0 => {
                // Hour
                res.hour = Some(value as u32);
                if value.fract() != 0.0 {
                    res.minute = Some((60.0 * value.fract()) as u32);
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
            && (token.chars().all(|c| c.is_ascii_uppercase()) || self.info.utczone(token))
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
            Some(h) if !(0..=12).contains(&h) => {
                if fuzzy {
                    return false;
                }
                false
            }
            _ => true,
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
        let sec_remainder = value.fract();
        let second = if sec_remainder != 0.0 {
            Some((60.0 * sec_remainder) as u32)
        } else {
            None
        };
        (minute, second)
    }

    /// Parse seconds with microseconds.
    fn parsems(&self, value: &str) -> (u32, u32) {
        if !value.contains('.') {
            (value.parse().unwrap_or(0), 0)
        } else {
            let parts: Vec<&str> = value.split('.').collect();
            let seconds: u32 = parts[0].parse().unwrap_or(0);
            let frac = parts.get(1).unwrap_or(&"0");
            // Pad to 6 digits and take first 6
            let padded = format!("{:0<6}", frac);
            let microseconds: u32 = padded[..6].parse().unwrap_or(0);
            (seconds, microseconds)
        }
    }

    /// Extract trailing timezone name from a string after ISO parsing.
    ///
    /// Handles cases like "2024-01-15 10:30:00 UTC" or "2024-01-15T10:30:00 GMT+3"
    /// where the ISO parser parsed the datetime but not the timezone.
    fn extract_trailing_timezone(&self, timestr: &str, mut result: ParseResult) -> ParseResult {
        // Find the last space-separated token(s) that could be timezone info
        let parts: Vec<&str> = timestr.split_whitespace().collect();
        if parts.len() < 2 {
            return result;
        }

        // Check the last part for timezone name
        let last_part = parts[parts.len() - 1];

        // Handle "UTC", "GMT", etc. (pure timezone name)
        if self.info.utczone(last_part) {
            result.tzname = Some(last_part.to_uppercase());
            result.tzoffset = Some(0);
            return result;
        }

        // Handle "EST", "PST", etc. (timezone abbreviation without defined offset)
        if last_part.len() <= 5 && last_part.chars().all(|c| c.is_ascii_uppercase()) {
            result.tzname = Some(last_part.to_string());
            // No offset - user needs tzinfos to resolve
            return result;
        }

        // Handle "GMT+3", "GMT-5", etc.
        if last_part.len() >= 4 {
            let upper = last_part.to_uppercase();
            if upper.starts_with("GMT") || upper.starts_with("UTC") {
                let rest = &last_part[3..];
                if let Some((sign, offset_str)) = rest.strip_prefix('+').map(|s| (-1i32, s))
                    .or_else(|| rest.strip_prefix('-').map(|s| (1i32, s)))
                {
                    // GMT+N means "my time + N = GMT", so offset is -N
                    // GMT-N means "my time - N = GMT", so offset is +N
                    if let Ok(hours) = offset_str.parse::<i32>() {
                        result.tzoffset = Some(sign * hours * 3600);
                        // Don't set tzname for GMT+N since it's not actually GMT
                        return result;
                    }
                }
            }
        }

        result
    }

    /// Recombine skipped tokens.
    fn recombine_skipped(&self, tokens: &[String], skipped_idxs: &[usize]) -> Vec<String> {
        let mut skipped_tokens: Vec<String> = Vec::new();
        let mut sorted_idxs: Vec<usize> = skipped_idxs.to_vec();
        sorted_idxs.sort();

        for (i, &idx) in sorted_idxs.iter().enumerate() {
            if i > 0 && idx == sorted_idxs[i - 1] + 1 {
                // Adjacent to previous
                if let Some(last) = skipped_tokens.last_mut() {
                    last.push_str(&tokens[idx]);
                }
            } else {
                skipped_tokens.push(tokens[idx].clone());
            }
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
        let (res, _) = parser
            .parse("10:30 PM", None, None, false, false)
            .unwrap();
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
        let (res, _) = parser
            .parse("2h30m45s", None, None, false, false)
            .unwrap();
        assert_eq!(res.hour, Some(2));
        assert_eq!(res.minute, Some(30));
        assert_eq!(res.second, Some(45));
    }
}
