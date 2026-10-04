//! Year/Month/Day disambiguation logic.
//!
//! Port of dateutil.parser._ymd to Rust.

use super::errors::ParserError;
use std::collections::{HashMap, HashSet};

/// Type alias for resolved Y/M/D result (year, month, day).
type YmdResult = Result<(Option<i32>, Option<i32>, Option<i32>), ParserError>;

/// Holds parsed Y/M/D values and tracks which position is which.
#[derive(Debug, Clone, Default)]
pub struct Ymd {
    /// The numeric values (up to 3)
    values: Vec<i32>,
    /// Whether the century was explicitly specified (4-digit year)
    pub century_specified: bool,
    /// Index of day value, if known
    dstridx: Option<usize>,
    /// Index of month value, if known
    mstridx: Option<usize>,
    /// Index of year value, if known
    ystridx: Option<usize>,
}

impl Ymd {
    /// Create a new empty Ymd.
    pub fn new() -> Self {
        Self::default()
    }

    /// Number of values stored.
    pub fn len(&self) -> usize {
        self.values.len()
    }

    /// Check if empty.
    pub fn is_empty(&self) -> bool {
        self.values.len() == 0
    }

    /// Check if year is known.
    pub fn has_year(&self) -> bool {
        self.ystridx.is_some()
    }

    /// Check if month is known.
    pub fn has_month(&self) -> bool {
        self.mstridx.is_some()
    }

    /// Check if day is known.
    pub fn has_day(&self) -> bool {
        self.dstridx.is_some()
    }

    /// Check if a value could be a valid day. With the month known and the
    /// year unknown, February allows 29.
    pub fn could_be_day(&self, value: i32) -> bool {
        if self.has_day() {
            return false;
        }

        if !self.has_month() {
            return value >= 1 && value <= 31;
        }

        let month_idx = match self.mstridx {
            Some(idx) => idx,
            None => return false,
        };
        let month = self.values[month_idx] as u32;
        let year = if self.has_year() {
            let year_idx = match self.ystridx {
                Some(idx) => idx,
                None => return false,
            };
            self.values[year_idx]
        } else {
            2000
        };

        let max_day = days_in_month(year, month);
        value >= 1 && value <= max_day as i32
    }

    /// Append a value with an optional label.
    ///
    /// # Arguments
    ///
    /// * `value` - A value above 100 takes the year slot and marks the
    ///   century as specified.
    /// * `label` - 'Y' (year), 'M' (month), 'D' (day), or `None` for an
    ///   unknown slot.
    ///
    /// # Errors
    ///
    /// `ParserError::ParseError` when a value above 100 carries a label
    /// other than 'Y', when the label's slot is already set, or for any
    /// other label. A duplicate or unknown label leaves the value
    /// appended.
    pub fn append(&mut self, value: i32, label: Option<char>) -> Result<(), ParserError> {
        let mut actual_label = label;

        if value > 100 {
            self.century_specified = true;
            if actual_label.is_none() || actual_label == Some('Y') {
                actual_label = Some('Y');
            } else {
                return Err(ParserError::ParseError(format!(
                    "Value {} too large for label {:?}",
                    value, actual_label
                )));
            }
        }

        self.values.push(value);
        let idx = self.values.len() - 1;

        match actual_label {
            Some('M') => {
                if self.has_month() {
                    return Err(ParserError::ParseError("Month is already set".to_string()));
                }
                self.mstridx = Some(idx);
            }
            Some('D') => {
                if self.has_day() {
                    return Err(ParserError::ParseError("Day is already set".to_string()));
                }
                self.dstridx = Some(idx);
            }
            Some('Y') => {
                if self.has_year() {
                    return Err(ParserError::ParseError("Year is already set".to_string()));
                }
                self.ystridx = Some(idx);
            }
            None => {}
            Some(c) => {
                return Err(ParserError::ParseError(format!("Invalid label: {}", c)));
            }
        }

        Ok(())
    }

    /// Append a value that is known to be a string token (for century
    /// detection).
    ///
    /// # Arguments
    ///
    /// * `s` - A token of three or more unsigned digits marks the century
    ///   as specified, so `"0024"` counts as a four-digit year.
    /// * `label` - As for `append`.
    ///
    /// # Errors
    ///
    /// `ParserError::ParseError` when `s` is not an optionally signed
    /// decimal integer, or on any error `append` gives.
    pub fn append_str(&mut self, s: &str, label: Option<char>) -> Result<(), ParserError> {
        let value: i32 = parse_i32(s)?;

        if s.len() > 2 && s.bytes().all(|c| c.is_ascii_digit()) {
            self.century_specified = true;
        }

        self.append(value, label)
    }

    /// Get value at index.
    #[allow(dead_code)]
    pub fn get(&self, idx: usize) -> Option<i32> {
        if idx < self.values.len() {
            Some(self.values[idx])
        } else {
            None
        }
    }

    /// Resolve the Y/M/D values based on yearfirst and dayfirst settings.
    ///
    /// # Returns
    ///
    /// (year, month, day), each `None` where undetermined.
    ///
    /// # Errors
    ///
    /// `ParserError::ParseError` when more than three values are stored.
    pub fn resolve(&self, yearfirst: bool, dayfirst: bool) -> YmdResult {
        let len_ymd = self.len();

        if len_ymd == 0 {
            return Ok((None, None, None));
        }

        if len_ymd > 3 {
            return Err(ParserError::ParseError(
                "More than three Ymd values".to_string(),
            ));
        }

        let mut strids_count = 0usize;
        if self.ystridx.is_some() {
            strids_count += 1;
        }
        if self.mstridx.is_some() {
            strids_count += 1;
        }
        if self.dstridx.is_some() {
            strids_count += 1;
        }

        if (len_ymd == strids_count && strids_count > 0) || (len_ymd == 3 && strids_count == 2) {
            return self.resolve_from_stridxs();
        }

        match len_ymd {
            1 => {
                if let Some(idx) = self.mstridx {
                    let month = self.values[idx];
                    Ok((None, Some(month), None))
                } else {
                    let val = self.values[0];
                    if val > 31 {
                        Ok((Some(val), None, None))
                    } else {
                        Ok((None, None, Some(val)))
                    }
                }
            }
            2 => {
                if self.mstridx.is_some() {
                    let m_idx = match self.mstridx {
                        Some(idx) => idx,
                        None => return Err(ParserError::ParseError("No month index".to_string())),
                    };
                    let month = self.values[m_idx];
                    let other_idx = if m_idx == 0 { 1 } else { 0 };
                    let other = self.values[other_idx];

                    if other > 31 {
                        Ok((Some(other), Some(month), None))
                    } else {
                        Ok((None, Some(month), Some(other)))
                    }
                } else {
                    let v0 = self.values[0];
                    let v1 = self.values[1];

                    if v0 > 31 {
                        Ok((Some(v0), Some(v1), None))
                    } else if v1 > 31 {
                        Ok((Some(v1), Some(v0), None))
                    } else if dayfirst && v1 <= 12 {
                        Ok((None, Some(v1), Some(v0)))
                    } else {
                        Ok((None, Some(v0), Some(v1)))
                    }
                }
            }
            3 => {
                let v0 = self.values[0];
                let v1 = self.values[1];
                let v2 = self.values[2];

                if let Some(midx) = self.mstridx {
                    match midx {
                        0 => {
                            if v1 > 31 {
                                Ok((Some(v1), Some(v0), Some(v2)))
                            } else {
                                Ok((Some(v2), Some(v0), Some(v1)))
                            }
                        }
                        1 => {
                            if v0 > 31 || (yearfirst && v2 <= 31) {
                                Ok((Some(v0), Some(v1), Some(v2)))
                            } else {
                                Ok((Some(v2), Some(v1), Some(v0)))
                            }
                        }
                        2 => {
                            if v1 > 31 {
                                Ok((Some(v1), Some(v2), Some(v0)))
                            } else {
                                Ok((Some(v0), Some(v2), Some(v1)))
                            }
                        }
                        _ => Err(ParserError::ParseError("Invalid month index".to_string())),
                    }
                } else {
                    let ystridx_is_zero = match self.ystridx {
                        Some(idx) => idx == 0,
                        None => false,
                    };
                    if v0 > 31 || ystridx_is_zero || (yearfirst && v1 <= 12 && v2 <= 31) {
                        if dayfirst && v2 <= 12 {
                            Ok((Some(v0), Some(v2), Some(v1)))
                        } else {
                            Ok((Some(v0), Some(v1), Some(v2)))
                        }
                    } else if v0 > 12 || (dayfirst && v1 <= 12) {
                        Ok((Some(v2), Some(v1), Some(v0)))
                    } else {
                        Ok((Some(v2), Some(v0), Some(v1)))
                    }
                }
            }
            _ => unreachable!(),
        }
    }

    /// Resolve using known stride indices.
    fn resolve_from_stridxs(&self) -> YmdResult {
        let mut strids: HashMap<char, usize> = HashMap::new();

        if let Some(idx) = self.ystridx {
            strids.insert('y', idx);
        }
        if let Some(idx) = self.mstridx {
            strids.insert('m', idx);
        }
        if let Some(idx) = self.dstridx {
            strids.insert('d', idx);
        }

        if self.len() == 3 && strids.len() == 2 {
            let mut used: HashSet<usize> = HashSet::new();
            if let Some(&v) = strids.get(&'y') {
                used.insert(v);
            }
            if let Some(&v) = strids.get(&'m') {
                used.insert(v);
            }
            if let Some(&v) = strids.get(&'d') {
                used.insert(v);
            }

            let mut missing_idx = 0usize;
            let mut i = 0usize;
            while i < 3 {
                if !used.contains(&i) {
                    missing_idx = i;
                    break;
                }
                i += 1;
            }

            let keys = ['y', 'm', 'd'];
            let mut missing_key = 'y';
            let mut k = 0usize;
            while k < 3 {
                if !strids.contains_key(&keys[k]) {
                    missing_key = keys[k];
                    break;
                }
                k += 1;
            }
            strids.insert(missing_key, missing_idx);
        }

        let year = match strids.get(&'y') {
            Some(&idx) => Some(self.values[idx]),
            None => None,
        };
        let month = match strids.get(&'m') {
            Some(&idx) => Some(self.values[idx]),
            None => None,
        };
        let day = match strids.get(&'d') {
            Some(&idx) => Some(self.values[idx]),
            None => None,
        };

        Ok((year, month, day))
    }
}

/// Days in `month` of `year`. An out-of-range month gives 31.
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
        _ => 31,
    }
}

/// Check if a year is a leap year.
fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}

/// Parse i32 from string.
fn parse_i32(s: &str) -> Result<i32, ParserError> {
    let bytes = s.as_bytes();
    let n = bytes.len();
    if n == 0 {
        return Err(ParserError::ParseError(format!("Invalid number: {}", s)));
    }

    let mut result: i32 = 0;
    let mut i = 0usize;
    let negative = bytes[0] == b'-';
    if negative || bytes[0] == b'+' {
        i = 1;
    }

    while i < n {
        let c = bytes[i];
        if c >= b'0' && c <= b'9' {
            result = result * 10 + (c - b'0') as i32;
        } else {
            return Err(ParserError::ParseError(format!("Invalid number: {}", s)));
        }
        i += 1;
    }

    if negative {
        result = -result;
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Verify resolve() gives no fields when nothing was appended.
    ///
    /// Mutation: dropping the empty early return, which reaches
    /// `unreachable!()`.
    /// Oracle: no values means no year, month or day.
    #[test]
    fn test_ymd_empty() {
        let ymd = Ymd::new();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (None, None, None));
    }

    /// Verify a lone value of 31 or less resolves as the day.
    ///
    /// Mutation: a lone-value year threshold of `> 12` for `> 31`.
    /// Oracle: 15 is a valid day and is read as no year.
    #[test]
    fn test_ymd_single_day() {
        let mut ymd = Ymd::new();
        ymd.append(15, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (None, None, Some(15)));
    }

    /// Verify a lone value above 31 resolves as the year.
    ///
    /// Mutation: swapping the year and day outputs of the lone-value
    /// branch.
    /// Oracle: no month has 2024 days.
    #[test]
    fn test_ymd_single_year() {
        let mut ymd = Ymd::new();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), None, None));
    }

    /// Verify a month token plus a value of 31 or less gives month-day.
    ///
    /// Mutation: taking the month's own index as the other value.
    /// Oracle: hand-read Jan 15.
    #[test]
    fn test_ymd_month_day() {
        let mut ymd = Ymd::new();
        ymd.append(1, Some('M')).unwrap();
        ymd.append(15, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (None, Some(1), Some(15)));
    }

    /// Verify MM/DD/YYYY resolves month first by default.
    ///
    /// Mutation: returning day-month-year from the month-first branch.
    /// Oracle: hand-read 01/15/2024 = Jan 15, 2024.
    #[test]
    fn test_ymd_us_format() {
        let mut ymd = Ymd::new();
        ymd.append(1, None).unwrap();
        ymd.append(15, None).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    /// Verify DD/MM/YYYY resolves day first with dayfirst set.
    ///
    /// Mutation: returning month-day-year from the day-first branch.
    /// Oracle: hand-read 15/01/2024 = Jan 15, 2024.
    #[test]
    fn test_ymd_european_format() {
        let mut ymd = Ymd::new();
        ymd.append(15, None).unwrap();
        ymd.append(1, None).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, true).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    /// Verify YYYY/MM/DD resolves year-month-day with yearfirst set.
    ///
    /// Mutation: returning year-day-month from the year-first branch
    /// without dayfirst.
    /// Oracle: hand-read 2024/01/15 = Jan 15, 2024.
    #[test]
    fn test_ymd_iso_format() {
        let mut ymd = Ymd::new();
        ymd.append(2024, None).unwrap();
        ymd.append(1, None).unwrap();
        ymd.append(15, None).unwrap();
        let (y, m, d) = ymd.resolve(true, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    /// Verify Jan 15, 2024 fills the day from the two known slots.
    ///
    /// Mutation: taking the first used index as the missing slot in
    /// resolve_from_stridxs.
    /// Oracle: hand-read Jan 15, 2024.
    #[test]
    fn test_ymd_named_month() {
        let mut ymd = Ymd::new();
        ymd.append(1, Some('M')).unwrap();
        ymd.append(15, None).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    /// Verify 15 Jan 2024 fills the day from the two known slots.
    ///
    /// Mutation: assigning the missing slot to 'y' whichever key is
    /// absent.
    /// Oracle: hand-read Jan 15, 2024.
    #[test]
    fn test_ymd_day_month_year() {
        let mut ymd = Ymd::new();
        ymd.append(15, None).unwrap();
        ymd.append(1, Some('M')).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    /// Verify 01/15/24 keeps the century unset and resolves month first.
    ///
    /// Mutation: a century threshold in append below 24.
    /// Oracle: hand-read 01/15/24 = Jan 15, year 24.
    #[test]
    fn test_ymd_two_digit_year() {
        let mut ymd = Ymd::new();
        ymd.append(1, None).unwrap();
        ymd.append(15, None).unwrap();
        ymd.append(24, None).unwrap();
        assert!(!ymd.century_specified);
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(24), Some(1), Some(15)));
    }

    /// Verify append_str() flags the century by token length and digits.
    ///
    /// Mutation: `> 3` for `> 2` in the length test, or `any` for `all`
    /// in the digit test.
    /// Oracle: "024" and "0024" hold three or more digits, "24" holds
    /// two, and "-24" holds a sign.
    #[test]
    fn test_ymd_century_from_token() {
        let cases = [
            ("2024", true),
            ("0024", true),
            ("024", true),
            ("24", false),
            ("-24", false),
        ];
        for (token, expected) in cases {
            let mut ymd = Ymd::new();
            ymd.append_str(token, None).unwrap();
            assert_eq!(ymd.century_specified, expected, "{token}");
        }
    }

    /// Verify resolve() rejects a fourth value.
    ///
    /// Mutation: dropping the more-than-three check, which reaches
    /// `unreachable!()`.
    /// Oracle: a date holds at most year, month and day.
    #[test]
    fn test_ymd_too_many_values() {
        let mut ymd = Ymd::new();
        ymd.append(1, None).unwrap();
        ymd.append(2, None).unwrap();
        ymd.append(3, None).unwrap();
        ymd.append(4, None).unwrap();
        let result = ymd.resolve(false, false);
        assert!(result.is_err());
    }

    /// Verify could_be_day() bounds, and Feb 29 with the year unknown.
    ///
    /// Mutation: `<` for `<=` at the day bound, or a non-leap stand-in
    /// year for an unknown year.
    /// Oracle: days run 1-31, and February has 29 days in a leap year.
    #[test]
    fn test_could_be_day() {
        let mut ymd = Ymd::new();
        assert!(ymd.could_be_day(1));
        assert!(ymd.could_be_day(31));
        assert!(!ymd.could_be_day(32));
        assert!(!ymd.could_be_day(0));

        ymd.append(2, Some('M')).unwrap();
        assert!(ymd.could_be_day(28));
        assert!(ymd.could_be_day(29));
        assert!(!ymd.could_be_day(30));
    }
}
