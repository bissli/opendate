//! Parser configuration for locale-specific datetime parsing.
//!
//! Port of dateutil.parser.parserinfo to Rust.

use std::collections::HashMap;

/// Parser configuration with locale-specific date/time names.
#[derive(Debug, Clone)]
pub struct ParserInfo {
    /// Whether to interpret first value in ambiguous date as day
    pub dayfirst: bool,
    /// Whether to interpret first value in ambiguous date as year
    pub yearfirst: bool,

    /// Jump tokens (ignored separators and connectors)
    jump: HashMap<String, bool>,
    /// Weekday names -> 0-6 (Monday=0)
    weekdays: HashMap<String, u32>,
    /// Month names -> 1-12
    months: HashMap<String, u32>,
    /// Hour/Minute/Second indicators -> 0-2
    hms: HashMap<String, u32>,
    /// AM/PM indicators -> 0/1
    ampm: HashMap<String, u32>,
    /// UTC zone names
    utczone: HashMap<String, bool>,
    /// Pertain words (like "of" in "Jan of 01")
    pertain: HashMap<String, bool>,
    /// Custom timezone offsets
    tzoffset: HashMap<String, i32>,

    /// Current year for two-digit year conversion
    year: i32,
    /// Current century (year // 100 * 100)
    century: i32,
}

impl Default for ParserInfo {
    fn default() -> Self {
        Self::new(false, false)
    }
}

impl ParserInfo {
    /// Default jump words (skippable tokens)
    const JUMP: &'static [&'static str] = &[
        " ", ".", ",", ";", "-", "/", "'", "at", "on", "and", "ad", "m", "t", "of", "st", "nd",
        "rd", "th",
    ];

    /// Default weekday names
    const WEEKDAYS: &'static [&'static [&'static str]] = &[
        &["mon", "monday"],
        &["tue", "tuesday"],
        &["wed", "wednesday"],
        &["thu", "thursday"],
        &["fri", "friday"],
        &["sat", "saturday"],
        &["sun", "sunday"],
    ];

    /// Default month names
    const MONTHS: &'static [&'static [&'static str]] = &[
        &["jan", "january"],
        &["feb", "february"],
        &["mar", "march"],
        &["apr", "april"],
        &["may"],
        &["jun", "june"],
        &["jul", "july"],
        &["aug", "august"],
        &["sep", "sept", "september"],
        &["oct", "october"],
        &["nov", "november"],
        &["dec", "december"],
    ];

    /// Hour/Minute/Second indicators
    const HMS: &'static [&'static [&'static str]] = &[
        &["h", "hour", "hours"],
        &["m", "minute", "minutes"],
        &["s", "second", "seconds"],
    ];

    /// AM/PM indicators
    const AMPM: &'static [&'static [&'static str]] = &[&["am", "a"], &["pm", "p"]];

    /// UTC zone names
    const UTCZONE: &'static [&'static str] = &["utc", "gmt", "z"];

    /// Pertain words
    const PERTAIN: &'static [&'static str] = &["of"];

    /// Create a new ParserInfo with the given settings.
    pub fn new(dayfirst: bool, yearfirst: bool) -> Self {
        let now = chrono_lite_year();
        let century = (now / 100) * 100;

        ParserInfo {
            dayfirst,
            yearfirst,
            jump: name_set(Self::JUMP),
            weekdays: name_index(Self::WEEKDAYS, 0),
            months: name_index(Self::MONTHS, 1),
            hms: name_index(Self::HMS, 0),
            ampm: name_index(Self::AMPM, 0),
            utczone: name_set(Self::UTCZONE),
            pertain: name_set(Self::PERTAIN),
            tzoffset: HashMap::new(),
            year: now,
            century,
        }
    }

    /// Check if a token is a jump token (should be skipped).
    pub fn jump(&self, name: &str) -> bool {
        self.jump.contains_key(&to_lowercase(name))
    }

    /// Get weekday number (0=Monday, 6=Sunday) from name.
    pub fn weekday(&self, name: &str) -> Option<u32> {
        match self.weekdays.get(&to_lowercase(name)) {
            Some(&v) => Some(v),
            None => None,
        }
    }

    /// Get month number (1-12) from name.
    pub fn month(&self, name: &str) -> Option<u32> {
        match self.months.get(&to_lowercase(name)) {
            Some(&v) => Some(v),
            None => None,
        }
    }

    /// Get HMS indicator (0=hour, 1=minute, 2=second) from name.
    pub fn hms(&self, name: &str) -> Option<u32> {
        match self.hms.get(&to_lowercase(name)) {
            Some(&v) => Some(v),
            None => None,
        }
    }

    /// Get AM/PM indicator (0=AM, 1=PM) from name.
    pub fn ampm(&self, name: &str) -> Option<u32> {
        match self.ampm.get(&to_lowercase(name)) {
            Some(&v) => Some(v),
            None => None,
        }
    }

    /// Check if name is a UTC zone name.
    pub fn utczone(&self, name: &str) -> bool {
        self.utczone.contains_key(&to_lowercase(name))
    }

    /// Check if name is a pertain word (like "of").
    pub fn pertain(&self, name: &str) -> bool {
        self.pertain.contains_key(&to_lowercase(name))
    }

    /// Get timezone offset for a name, if defined.
    pub fn tzoffset(&self, name: &str) -> Option<i32> {
        if self.utczone(name) {
            return Some(0);
        }
        match self.tzoffset.get(name) {
            Some(&v) => Some(v),
            None => None,
        }
    }

    /// Add a custom timezone offset.
    #[allow(dead_code)]
    pub fn add_tzoffset(&mut self, name: &str, offset_seconds: i32) {
        self.tzoffset.insert(name.to_string(), offset_seconds);
    }

    /// Convert a two-digit year to a four-digit year.
    ///
    /// Years are converted to be within [-50, +49] range of the current year.
    ///
    /// # Arguments
    /// * `year` - Parsed year. A value of 100 or more returns unchanged.
    /// * `century_specified` - True when the input wrote the century, which
    ///   returns `year` unchanged.
    pub fn convertyear(&self, year: i32, century_specified: bool) -> i32 {
        if year < 100 && !century_specified {
            let mut converted = year + self.century;

            if converted >= self.year + 50 {
                converted -= 100;
            } else if converted < self.year - 50 {
                converted += 100;
            }

            converted
        } else {
            year
        }
    }

    /// Same as `convertyear`.
    #[allow(dead_code)]
    pub fn validate_year(&self, year: i32, century_specified: bool) -> i32 {
        self.convertyear(year, century_specified)
    }

    /// Normalize UTC timezone info.
    #[allow(dead_code)]
    pub fn normalize_tzinfo(
        &self,
        tzoffset: Option<i32>,
        tzname: Option<&str>,
    ) -> (Option<i32>, Option<String>) {
        match (tzoffset, tzname) {
            (Some(0), None) | (None, Some("Z" | "z")) | (Some(0), Some("Z" | "z")) => {
                (Some(0), Some("UTC".to_string()))
            }
            (Some(offset), Some(name)) if offset != 0 && self.utczone(name) => {
                (Some(0), Some("UTC".to_string()))
            }
            (offset, name) => (offset, name.map(String::from)),
        }
    }
}

/// Copy of `s` with ASCII A-Z lowercased; every other byte maps to one
/// char unchanged.
fn to_lowercase(s: &str) -> String {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut result = String::with_capacity(n);
    let mut i = 0usize;
    while i < n {
        let c = bytes[i];
        if c >= b'A' && c <= b'Z' {
            result.push((c + 32) as char);
        } else {
            result.push(c as char);
        }
        i += 1;
    }
    result
}

/// Lowercased name -> true, for membership tests.
fn name_set(names: &[&str]) -> HashMap<String, bool> {
    let mut set = HashMap::with_capacity(names.len());
    let mut i = 0usize;
    while i < names.len() {
        set.insert(to_lowercase(names[i]), true);
        i += 1;
    }
    set
}

/// Lowercased name -> value, where every name in `groups[i]` maps to
/// `first + i`.
fn name_index(groups: &[&[&str]], first: u32) -> HashMap<String, u32> {
    let mut index = HashMap::new();
    let mut i = 0usize;
    while i < groups.len() {
        let names = groups[i];
        let mut j = 0usize;
        while j < names.len() {
            index.insert(to_lowercase(names[j]), first + i as u32);
            j += 1;
        }
        i += 1;
    }
    index
}

/// Current year from the system clock, counting 365-day years. It ignores
/// leap days, so it can read one year ahead in late December.
fn chrono_lite_year() -> i32 {
    use std::time::{SystemTime, UNIX_EPOCH};

    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();

    let secs = duration.as_secs() as i64;
    let days = secs / 86400;
    let years = days / 365;
    (1970 + years) as i32
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Verify jump words match and an unknown word does not.
    ///
    /// Mutation: JUMP missing an entry such as "st", or jump() reading
    ///   the pertain table.
    /// Oracle: dateutil parserinfo.JUMP.
    #[test]
    fn test_jump() {
        let info = ParserInfo::default();
        assert!(info.jump(" "));
        assert!(info.jump("at"));
        assert!(info.jump("on"));
        assert!(info.jump("st"));
        assert!(!info.jump("foo"));
    }

    /// Verify weekday names map Monday=0 to Sunday=6, any case.
    ///
    /// Mutation: indexes starting at 1, or the lookup skipping the
    ///   lowercase step.
    /// Oracle: dateutil parserinfo.WEEKDAYS order.
    #[test]
    fn test_weekday() {
        let info = ParserInfo::default();
        assert_eq!(info.weekday("Monday"), Some(0));
        assert_eq!(info.weekday("mon"), Some(0));
        assert_eq!(info.weekday("MON"), Some(0));
        assert_eq!(info.weekday("Tuesday"), Some(1));
        assert_eq!(info.weekday("Sun"), Some(6));
        assert_eq!(info.weekday("foo"), None);
    }

    /// Verify month names map to 1-12, any case, with "sept" as September.
    ///
    /// Mutation: month indexes starting at 0, or "sept" dropped.
    /// Oracle: dateutil parserinfo.MONTHS.
    #[test]
    fn test_month() {
        let info = ParserInfo::default();
        assert_eq!(info.month("January"), Some(1));
        assert_eq!(info.month("jan"), Some(1));
        assert_eq!(info.month("JAN"), Some(1));
        assert_eq!(info.month("February"), Some(2));
        assert_eq!(info.month("Sep"), Some(9));
        assert_eq!(info.month("Sept"), Some(9));
        assert_eq!(info.month("September"), Some(9));
        assert_eq!(info.month("December"), Some(12));
        assert_eq!(info.month("foo"), None);
    }

    /// Verify hour, minute and second words map to 0, 1 and 2.
    ///
    /// Mutation: HMS groups reordered, or "hours" dropped.
    /// Oracle: dateutil parserinfo.HMS.
    #[test]
    fn test_hms() {
        let info = ParserInfo::default();
        assert_eq!(info.hms("h"), Some(0));
        assert_eq!(info.hms("hour"), Some(0));
        assert_eq!(info.hms("hours"), Some(0));
        assert_eq!(info.hms("m"), Some(1));
        assert_eq!(info.hms("minute"), Some(1));
        assert_eq!(info.hms("s"), Some(2));
        assert_eq!(info.hms("second"), Some(2));
        assert_eq!(info.hms("foo"), None);
    }

    /// Verify AM words map to 0 and PM words to 1, any case.
    ///
    /// Mutation: AMPM groups swapped, or the one-letter forms dropped.
    /// Oracle: dateutil parserinfo.AMPM.
    #[test]
    fn test_ampm() {
        let info = ParserInfo::default();
        assert_eq!(info.ampm("am"), Some(0));
        assert_eq!(info.ampm("AM"), Some(0));
        assert_eq!(info.ampm("a"), Some(0));
        assert_eq!(info.ampm("pm"), Some(1));
        assert_eq!(info.ampm("PM"), Some(1));
        assert_eq!(info.ampm("p"), Some(1));
        assert_eq!(info.ampm("foo"), None);
    }

    /// Verify UTC zone names match in any case and EST does not.
    ///
    /// Mutation: utczone() skipping the lowercase step, or "z" dropped.
    /// Oracle: dateutil parserinfo.UTCZONE.
    #[test]
    fn test_utczone() {
        let info = ParserInfo::default();
        assert!(info.utczone("UTC"));
        assert!(info.utczone("utc"));
        assert!(info.utczone("GMT"));
        assert!(info.utczone("Z"));
        assert!(!info.utczone("EST"));
    }

    /// Verify a four-digit year passes through and a two-digit one lands
    /// in the window around the current year.
    ///
    /// Mutation: the `year < 100` guard dropped, or the past and future
    ///   century shifts swapped.
    /// Oracle: hand-picked years 24 and 90 against the 50-year window.
    #[test]
    fn test_convertyear() {
        let info = ParserInfo::default();
        let _current_year = chrono_lite_year();

        assert_eq!(info.convertyear(2024, true), 2024);
        assert_eq!(info.convertyear(1990, true), 1990);

        let converted = info.convertyear(24, false);
        assert!(converted >= 2000 && converted < 2100);

        let converted = info.convertyear(90, false);
        assert!(converted >= 1900 && converted < 2000);
    }

    /// Verify "of" is a pertain word in any case.
    ///
    /// Mutation: pertain() skipping the lowercase step.
    /// Oracle: dateutil parserinfo.PERTAIN.
    #[test]
    fn test_pertain() {
        let info = ParserInfo::default();
        assert!(info.pertain("of"));
        assert!(info.pertain("OF"));
        assert!(!info.pertain("foo"));
    }

    /// Verify UTC names give offset 0, an added name its offset, and an
    /// unknown name None.
    ///
    /// Mutation: tzoffset() skipping the UTC-name check, or
    ///   add_tzoffset storing the offset under another key.
    /// Oracle: hand-computed -5 * 3600 for EST.
    #[test]
    fn test_tzoffset() {
        let mut info = ParserInfo::default();

        assert_eq!(info.tzoffset("UTC"), Some(0));
        assert_eq!(info.tzoffset("GMT"), Some(0));

        info.add_tzoffset("EST", -5 * 3600);
        assert_eq!(info.tzoffset("EST"), Some(-5 * 3600));

        assert_eq!(info.tzoffset("XYZ"), None);
    }
}
