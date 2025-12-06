//! Year/Month/Day disambiguation logic.
//!
//! Port of dateutil.parser._ymd to Rust.

use super::errors::ParserError;

/// Holds parsed Y/M/D values and tracks which position is which.
#[derive(Debug, Clone, Default)]
pub struct YMD {
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

impl YMD {
    /// Create a new empty YMD.
    pub fn new() -> Self {
        Self::default()
    }

    /// Number of values stored.
    pub fn len(&self) -> usize {
        self.values.len()
    }

    /// Check if empty.
    pub fn is_empty(&self) -> bool {
        self.values.is_empty()
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

    /// Check if a value could be a valid day.
    pub fn could_be_day(&self, value: i32) -> bool {
        if self.has_day() {
            return false;
        }

        if !self.has_month() {
            return (1..=31).contains(&value);
        }

        let month = self.values[self.mstridx.unwrap()] as u32;
        let year = if self.has_year() {
            self.values[self.ystridx.unwrap()]
        } else {
            2000 // Assume leap year if year unknown
        };

        let max_day = days_in_month(year, month);
        (1..=max_day as i32).contains(&value)
    }

    /// Append a value with an optional label.
    ///
    /// Label can be 'Y' (year), 'M' (month), or 'D' (day).
    pub fn append(&mut self, value: i32, label: Option<char>) -> Result<(), ParserError> {
        // Check for century specification (4+ digit number)
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

    /// Append a value that is known to be a string token (for century detection).
    pub fn append_str(&mut self, s: &str, label: Option<char>) -> Result<(), ParserError> {
        let value: i32 = s
            .parse()
            .map_err(|_| ParserError::ParseError(format!("Invalid number: {}", s)))?;

        // Check for century specification based on string length
        if s.len() > 2 && s.chars().all(|c| c.is_ascii_digit()) {
            self.century_specified = true;
        }

        self.append(value, label)
    }

    /// Get value at index.
    pub fn get(&self, idx: usize) -> Option<i32> {
        self.values.get(idx).copied()
    }

    /// Resolve the Y/M/D values based on yearfirst and dayfirst settings.
    ///
    /// Returns (year, month, day) where any may be None if not determined.
    pub fn resolve(
        &self,
        yearfirst: bool,
        dayfirst: bool,
    ) -> Result<(Option<i32>, Option<i32>, Option<i32>), ParserError> {
        let len_ymd = self.len();

        if len_ymd == 0 {
            return Ok((None, None, None));
        }

        if len_ymd > 3 {
            return Err(ParserError::ParseError(
                "More than three YMD values".to_string(),
            ));
        }

        // If we have enough stride indices, use them
        let strids_count =
            self.ystridx.is_some() as usize + self.mstridx.is_some() as usize + self.dstridx.is_some() as usize;

        if (len_ymd == strids_count && strids_count > 0) || (len_ymd == 3 && strids_count == 2) {
            return self.resolve_from_stridxs();
        }

        let mstridx = self.mstridx;

        match len_ymd {
            1 => {
                // One value
                if mstridx.is_some() {
                    // Single month value
                    let month = self.values[mstridx.unwrap()];
                    Ok((None, Some(month), None))
                } else {
                    // Ambiguous single value - could be year or day
                    let val = self.values[0];
                    if val > 31 {
                        Ok((Some(val), None, None))
                    } else {
                        Ok((None, None, Some(val)))
                    }
                }
            }
            2 if mstridx.is_some() => {
                // Two values with month string
                let month = self.values[mstridx.unwrap()];
                let other_idx = if mstridx.unwrap() == 0 { 1 } else { 0 };
                let other = self.values[other_idx];

                if other > 31 {
                    Ok((Some(other), Some(month), None))
                } else {
                    Ok((None, Some(month), Some(other)))
                }
            }
            2 => {
                // Two numeric values
                let (v0, v1) = (self.values[0], self.values[1]);

                if v0 > 31 {
                    // 99-01: year-month
                    Ok((Some(v0), Some(v1), None))
                } else if v1 > 31 {
                    // 01-99: month-year
                    Ok((Some(v1), Some(v0), None))
                } else if dayfirst && v1 <= 12 {
                    // 13-01: day-month
                    Ok((None, Some(v1), Some(v0)))
                } else {
                    // 01-13: month-day
                    Ok((None, Some(v0), Some(v1)))
                }
            }
            3 => {
                // Three values
                let (v0, v1, v2) = (self.values[0], self.values[1], self.values[2]);

                if let Some(midx) = mstridx {
                    // Month is known
                    match midx {
                        0 => {
                            // Month first: M-?-?
                            if v1 > 31 {
                                // Apr-2003-25: month-year-day
                                Ok((Some(v1), Some(v0), Some(v2)))
                            } else {
                                // Apr-25-2003: month-day-year
                                Ok((Some(v2), Some(v0), Some(v1)))
                            }
                        }
                        1 => {
                            // Month second: ?-M-?
                            if v0 > 31 || (yearfirst && v2 <= 31) {
                                // 99-Jan-01: year-month-day
                                Ok((Some(v0), Some(v1), Some(v2)))
                            } else {
                                // 01-Jan-01: day-month-year
                                Ok((Some(v2), Some(v1), Some(v0)))
                            }
                        }
                        2 => {
                            // Month third: ?-?-M (unusual!)
                            if v1 > 31 {
                                // 01-99-Jan: day-year-month
                                Ok((Some(v1), Some(v2), Some(v0)))
                            } else {
                                // 99-01-Jan: year-day-month
                                Ok((Some(v0), Some(v2), Some(v1)))
                            }
                        }
                        _ => Err(ParserError::ParseError("Invalid month index".to_string())),
                    }
                } else {
                    // No month identified - pure numeric disambiguation
                    if v0 > 31 || self.ystridx == Some(0) || (yearfirst && v1 <= 12 && v2 <= 31) {
                        // Year first: 99-01-01
                        if dayfirst && v2 <= 12 {
                            // 99-31-01: year-day-month
                            Ok((Some(v0), Some(v2), Some(v1)))
                        } else {
                            // 99-01-31: year-month-day
                            Ok((Some(v0), Some(v1), Some(v2)))
                        }
                    } else if v0 > 12 || (dayfirst && v1 <= 12) {
                        // Day first: 13-01-01
                        Ok((Some(v2), Some(v1), Some(v0)))
                    } else {
                        // Month first: 01-13-01
                        Ok((Some(v2), Some(v0), Some(v1)))
                    }
                }
            }
            _ => unreachable!(),
        }
    }

    /// Resolve using known stride indices.
    fn resolve_from_stridxs(&self) -> Result<(Option<i32>, Option<i32>, Option<i32>), ParserError> {
        let mut strids: std::collections::HashMap<char, usize> = std::collections::HashMap::new();

        if let Some(idx) = self.ystridx {
            strids.insert('y', idx);
        }
        if let Some(idx) = self.mstridx {
            strids.insert('m', idx);
        }
        if let Some(idx) = self.dstridx {
            strids.insert('d', idx);
        }

        // If we have 3 values and 2 known strides, we can infer the third
        if self.len() == 3 && strids.len() == 2 {
            let used: std::collections::HashSet<usize> = strids.values().copied().collect();
            let missing_idx = (0..3).find(|i| !used.contains(i)).unwrap();
            let missing_key = ['y', 'm', 'd']
                .into_iter()
                .find(|k| !strids.contains_key(k))
                .unwrap();
            strids.insert(missing_key, missing_idx);
        }

        let year = strids.get(&'y').map(|&idx| self.values[idx]);
        let month = strids.get(&'m').map(|&idx| self.values[idx]);
        let day = strids.get(&'d').map(|&idx| self.values[idx]);

        Ok((year, month, day))
    }
}

/// Get number of days in a month.
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
        _ => 31, // Default fallback
    }
}

/// Check if a year is a leap year.
fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ymd_empty() {
        let ymd = YMD::new();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (None, None, None));
    }

    #[test]
    fn test_ymd_single_day() {
        let mut ymd = YMD::new();
        ymd.append(15, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (None, None, Some(15)));
    }

    #[test]
    fn test_ymd_single_year() {
        let mut ymd = YMD::new();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), None, None));
    }

    #[test]
    fn test_ymd_month_day() {
        let mut ymd = YMD::new();
        ymd.append(1, Some('M')).unwrap();
        ymd.append(15, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (None, Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_us_format() {
        // MM/DD/YYYY (US format, default)
        let mut ymd = YMD::new();
        ymd.append(1, None).unwrap();
        ymd.append(15, None).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_european_format() {
        // DD/MM/YYYY (European format, dayfirst=true)
        let mut ymd = YMD::new();
        ymd.append(15, None).unwrap();
        ymd.append(1, None).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, true).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_iso_format() {
        // YYYY/MM/DD (ISO format, yearfirst=true)
        let mut ymd = YMD::new();
        ymd.append(2024, None).unwrap();
        ymd.append(1, None).unwrap();
        ymd.append(15, None).unwrap();
        let (y, m, d) = ymd.resolve(true, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_named_month() {
        // Jan 15, 2024
        let mut ymd = YMD::new();
        ymd.append(1, Some('M')).unwrap(); // January
        ymd.append(15, None).unwrap();
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_day_month_year() {
        // 15 Jan 2024
        let mut ymd = YMD::new();
        ymd.append(15, None).unwrap();
        ymd.append(1, Some('M')).unwrap(); // January
        ymd.append(2024, None).unwrap();
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        assert_eq!((y, m, d), (Some(2024), Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_two_digit_year() {
        // 01/15/24 with month/day inference
        let mut ymd = YMD::new();
        ymd.append(1, None).unwrap();
        ymd.append(15, None).unwrap();
        ymd.append(24, None).unwrap();
        assert!(!ymd.century_specified);
        let (y, m, d) = ymd.resolve(false, false).unwrap();
        // 24 is not > 31, so it goes to year position by process of elimination
        assert_eq!((y, m, d), (Some(24), Some(1), Some(15)));
    }

    #[test]
    fn test_ymd_century_specified() {
        let mut ymd = YMD::new();
        ymd.append_str("2024", None).unwrap();
        assert!(ymd.century_specified);
    }

    #[test]
    fn test_ymd_too_many_values() {
        let mut ymd = YMD::new();
        ymd.append(1, None).unwrap();
        ymd.append(2, None).unwrap();
        ymd.append(3, None).unwrap();
        ymd.append(4, None).unwrap();
        let result = ymd.resolve(false, false);
        assert!(result.is_err());
    }

    #[test]
    fn test_could_be_day() {
        let mut ymd = YMD::new();
        assert!(ymd.could_be_day(1));
        assert!(ymd.could_be_day(31));
        assert!(!ymd.could_be_day(32));
        assert!(!ymd.could_be_day(0));

        // With February month
        ymd.append(2, Some('M')).unwrap();
        assert!(ymd.could_be_day(28));
        assert!(ymd.could_be_day(29)); // Assume leap year
        assert!(!ymd.could_be_day(30));
    }
}
