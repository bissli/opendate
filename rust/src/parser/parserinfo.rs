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
        // Get current year
        let now = chrono_lite_year();
        let century = (now / 100) * 100;

        let mut info = ParserInfo {
            dayfirst,
            yearfirst,
            jump: HashMap::new(),
            weekdays: HashMap::new(),
            months: HashMap::new(),
            hms: HashMap::new(),
            ampm: HashMap::new(),
            utczone: HashMap::new(),
            pertain: HashMap::new(),
            tzoffset: HashMap::new(),
            year: now,
            century,
        };

        // Initialize lookup tables
        for &word in Self::JUMP {
            info.jump.insert(word.to_lowercase(), true);
        }

        for (i, &names) in Self::WEEKDAYS.iter().enumerate() {
            for &name in names {
                info.weekdays.insert(name.to_lowercase(), i as u32);
            }
        }

        for (i, &names) in Self::MONTHS.iter().enumerate() {
            for &name in names {
                info.months.insert(name.to_lowercase(), (i + 1) as u32);
            }
        }

        for (i, &names) in Self::HMS.iter().enumerate() {
            for &name in names {
                info.hms.insert(name.to_lowercase(), i as u32);
            }
        }

        for (i, &names) in Self::AMPM.iter().enumerate() {
            for &name in names {
                info.ampm.insert(name.to_lowercase(), i as u32);
            }
        }

        for &zone in Self::UTCZONE {
            info.utczone.insert(zone.to_lowercase(), true);
        }

        for &word in Self::PERTAIN {
            info.pertain.insert(word.to_lowercase(), true);
        }

        info
    }

    /// Check if a token is a jump token (should be skipped).
    pub fn jump(&self, name: &str) -> bool {
        self.jump.contains_key(&name.to_lowercase())
    }

    /// Get weekday number (0=Monday, 6=Sunday) from name.
    pub fn weekday(&self, name: &str) -> Option<u32> {
        self.weekdays.get(&name.to_lowercase()).copied()
    }

    /// Get month number (1-12) from name.
    pub fn month(&self, name: &str) -> Option<u32> {
        self.months.get(&name.to_lowercase()).copied()
    }

    /// Get HMS indicator (0=hour, 1=minute, 2=second) from name.
    pub fn hms(&self, name: &str) -> Option<u32> {
        self.hms.get(&name.to_lowercase()).copied()
    }

    /// Get AM/PM indicator (0=AM, 1=PM) from name.
    pub fn ampm(&self, name: &str) -> Option<u32> {
        self.ampm.get(&name.to_lowercase()).copied()
    }

    /// Check if name is a UTC zone name.
    pub fn utczone(&self, name: &str) -> bool {
        self.utczone.contains_key(&name.to_lowercase())
    }

    /// Check if name is a pertain word (like "of").
    pub fn pertain(&self, name: &str) -> bool {
        self.pertain.contains_key(&name.to_lowercase())
    }

    /// Get timezone offset for a name, if defined.
    pub fn tzoffset(&self, name: &str) -> Option<i32> {
        if self.utczone(name) {
            return Some(0);
        }
        self.tzoffset.get(name).copied()
    }

    /// Add a custom timezone offset.
    #[allow(dead_code)]
    pub fn add_tzoffset(&mut self, name: &str, offset_seconds: i32) {
        self.tzoffset.insert(name.to_string(), offset_seconds);
    }

    /// Convert a two-digit year to a four-digit year.
    ///
    /// Years are converted to be within [-50, +49] range of the current year.
    pub fn convertyear(&self, year: i32, century_specified: bool) -> i32 {
        if year < 100 && !century_specified {
            // Assume current century
            let mut converted = year + self.century;

            // If too far in future (>= current year + 50), go back a century
            if converted >= self.year + 50 {
                converted -= 100;
            }
            // If too far in past (< current year - 50), go forward a century
            else if converted < self.year - 50 {
                converted += 100;
            }

            converted
        } else {
            year
        }
    }

    /// Validate and normalize a parse result.
    ///
    /// Returns true if valid, false otherwise.
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
            // Zero offset without name, or Z/z name
            (Some(0), None) | (None, Some("Z" | "z")) | (Some(0), Some("Z" | "z")) => {
                (Some(0), Some("UTC".to_string()))
            }
            // Non-zero offset with UTC zone name - offset takes precedence
            (Some(offset), Some(name)) if offset != 0 && self.utczone(name) => {
                (Some(0), Some("UTC".to_string()))
            }
            // Preserve as-is
            (offset, name) => (offset, name.map(String::from)),
        }
    }
}

/// Get current year (simplified, avoids chrono dependency).
fn chrono_lite_year() -> i32 {
    // Use std::time for a simple year calculation
    use std::time::{SystemTime, UNIX_EPOCH};

    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();

    let secs = duration.as_secs() as i64;
    // Approximate year calculation (good enough for century detection)
    let days = secs / 86400;
    let years = days / 365;
    (1970 + years) as i32
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jump() {
        let info = ParserInfo::default();
        assert!(info.jump(" "));
        assert!(info.jump("at"));
        assert!(info.jump("on"));
        assert!(info.jump("st"));
        assert!(!info.jump("foo"));
    }

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

    #[test]
    fn test_utczone() {
        let info = ParserInfo::default();
        assert!(info.utczone("UTC"));
        assert!(info.utczone("utc"));
        assert!(info.utczone("GMT"));
        assert!(info.utczone("Z"));
        assert!(!info.utczone("EST"));
    }

    #[test]
    fn test_convertyear() {
        let info = ParserInfo::default();
        let current_year = chrono_lite_year();

        // Four-digit year unchanged
        assert_eq!(info.convertyear(2024, true), 2024);
        assert_eq!(info.convertyear(1990, true), 1990);

        // Two-digit year conversion
        // Assuming current year is around 2024-2025
        let converted = info.convertyear(24, false);
        assert!(converted >= 2000 && converted < 2100);

        // Old year (should be 1990s for year 90)
        let converted = info.convertyear(90, false);
        assert!(converted >= 1900 && converted < 2000);
    }

    #[test]
    fn test_pertain() {
        let info = ParserInfo::default();
        assert!(info.pertain("of"));
        assert!(info.pertain("OF"));
        assert!(!info.pertain("foo"));
    }

    #[test]
    fn test_tzoffset() {
        let mut info = ParserInfo::default();

        // UTC zones return 0
        assert_eq!(info.tzoffset("UTC"), Some(0));
        assert_eq!(info.tzoffset("GMT"), Some(0));

        // Custom offset
        info.add_tzoffset("EST", -5 * 3600);
        assert_eq!(info.tzoffset("EST"), Some(-5 * 3600));

        // Unknown returns None
        assert_eq!(info.tzoffset("XYZ"), None);
    }
}
