//! Tokenizer for datetime strings.
//!
//! Port of dateutil.parser._timelex to Rust.

/// State machine states for tokenization.
#[derive(Debug, Clone, Copy, PartialEq)]
enum State {
    Initial,
    Word,      // 'a' - reading a word
    Number,    // '0' - reading a number
    WordDot,   // 'a.' - word followed by dot
    NumberDot, // '0.' - number followed by dot
}

/// Tokenizer for datetime strings.
///
/// Breaks strings into lexical units: words, numbers, whitespace, and separators.
pub struct Tokenizer {
    bytes: Vec<u8>,
    pos: usize,
    charstack: Vec<(usize, char)>,
    tokenstack: Vec<String>,
    eof: bool,
}

impl Tokenizer {
    /// Create a new tokenizer for the given input string.
    pub fn new(input: &str) -> Self {
        Tokenizer {
            bytes: input.as_bytes().to_vec(),
            pos: 0,
            charstack: Vec::new(),
            tokenstack: Vec::new(),
            eof: false,
        }
    }

    /// Split a string into tokens.
    pub fn split(input: &str) -> Vec<String> {
        let mut tokenizer = Tokenizer::new(input);
        let mut result = Vec::new();
        loop {
            match tokenizer.get_token() {
                Some(t) => result.push(t),
                None => break,
            }
        }
        result
    }

    /// Get the next character, filtering null bytes.
    fn next_char(&mut self) -> Option<(usize, char)> {
        if !self.charstack.is_empty() {
            let last_idx = self.charstack.len() - 1;
            let item = self.charstack[last_idx];
            self.charstack.pop();
            return Some(item);
        }

        loop {
            if self.pos >= self.bytes.len() {
                return None;
            }
            let idx = self.pos;
            let b = self.bytes[self.pos];
            self.pos += 1;
            // Filter null bytes
            if b == 0 {
                continue;
            }
            // Simple ASCII to char conversion for common cases
            let c = b as char;
            return Some((idx, c));
        }
    }

    /// Push a character back onto the stack.
    fn push_char(&mut self, item: (usize, char)) {
        self.charstack.push(item);
    }

    /// Get the next token.
    pub fn get_token(&mut self) -> Option<String> {
        // Return buffered tokens first
        if !self.tokenstack.is_empty() {
            let first = self.tokenstack[0].clone();
            let n = self.tokenstack.len();
            let mut i = 0usize;
            while i < n - 1 {
                self.tokenstack[i] = self.tokenstack[i + 1].clone();
                i += 1;
            }
            self.tokenstack.pop();
            return Some(first);
        }

        if self.eof {
            return None;
        }

        let mut seen_letters = false;
        let mut token = String::new();
        let mut state = State::Initial;

        while !self.eof {
            let (idx, nextchar) = match self.next_char() {
                Some(item) => item,
                None => {
                    self.eof = true;
                    break;
                }
            };

            match state {
                State::Initial => {
                    token.push(nextchar);
                    if is_alphabetic(nextchar) {
                        state = State::Word;
                    } else if is_ascii_digit(nextchar) {
                        state = State::Number;
                    } else if is_whitespace(nextchar) {
                        token = " ".to_string();
                        break;
                    } else {
                        break; // Single separator
                    }
                }
                State::Word => {
                    seen_letters = true;
                    if is_alphabetic(nextchar) {
                        token.push(nextchar);
                    } else if nextchar == '.' {
                        token.push(nextchar);
                        state = State::WordDot;
                    } else {
                        self.push_char((idx, nextchar));
                        break;
                    }
                }
                State::Number => {
                    if is_ascii_digit(nextchar) {
                        token.push(nextchar);
                    } else if nextchar == '.' || (nextchar == ',' && token.len() >= 2) {
                        token.push(nextchar);
                        state = State::NumberDot;
                    } else {
                        self.push_char((idx, nextchar));
                        break;
                    }
                }
                State::WordDot => {
                    seen_letters = true;
                    if nextchar == '.' || is_alphabetic(nextchar) {
                        token.push(nextchar);
                    } else if is_ascii_digit(nextchar) && ends_with_char(&token, '.') {
                        token.push(nextchar);
                        state = State::NumberDot;
                    } else {
                        self.push_char((idx, nextchar));
                        break;
                    }
                }
                State::NumberDot => {
                    if nextchar == '.' || is_ascii_digit(nextchar) {
                        token.push(nextchar);
                    } else if is_alphabetic(nextchar) && ends_with_char(&token, '.') {
                        token.push(nextchar);
                        state = State::WordDot;
                    } else {
                        self.push_char((idx, nextchar));
                        break;
                    }
                }
            }
        }

        // Handle compound tokens with dots
        let dot_count = count_char(&token, '.');
        if (state == State::WordDot || state == State::NumberDot)
            && (seen_letters
                || dot_count > 1
                || ends_with_char(&token, '.')
                || ends_with_char(&token, ','))
        {
            // Clone before splitting to avoid borrow issues
            let original = token.clone();

            // Split on dots and commas
            let parts = split_on_delims(&original);

            if !parts.is_empty() {
                token = parts[0].clone();

                // Find separators by walking the original string
                let mut pos = parts[0].len();
                let orig_bytes = original.as_bytes();
                let orig_len = orig_bytes.len();
                let mut part_idx = 1usize;
                while part_idx < parts.len() {
                    if pos < orig_len {
                        let sep = orig_bytes[pos] as char;
                        self.tokenstack.push(sep.to_string());
                        pos += 1;
                    }
                    self.tokenstack.push(parts[part_idx].clone());
                    pos += parts[part_idx].len();
                    part_idx += 1;
                }

                // Handle trailing separator
                if pos < orig_len {
                    let trailing_sep = orig_bytes[pos] as char;
                    if trailing_sep == '.' || trailing_sep == ',' {
                        self.tokenstack.push(trailing_sep.to_string());
                    }
                }
            }
        }

        // Convert comma decimal to dot for numbers
        if state == State::NumberDot && !contains_char(&token, '.') {
            token = replace_char(&token, ',', '.');
        }

        if token.is_empty() {
            None
        } else {
            Some(token)
        }
    }
}

impl Iterator for Tokenizer {
    type Item = String;

    fn next(&mut self) -> Option<Self::Item> {
        self.get_token()
    }
}

// Helper functions

fn is_alphabetic(c: char) -> bool {
    (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
}

fn is_ascii_digit(c: char) -> bool {
    c >= '0' && c <= '9'
}

fn is_whitespace(c: char) -> bool {
    c == ' ' || c == '\t' || c == '\n' || c == '\r'
}

fn ends_with_char(s: &str, c: char) -> bool {
    let bytes = s.as_bytes();
    let n = bytes.len();
    if n == 0 {
        return false;
    }
    bytes[n - 1] as char == c
}

fn count_char(s: &str, c: char) -> usize {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut count = 0usize;
    let mut i = 0usize;
    while i < n {
        if bytes[i] as char == c {
            count += 1;
        }
        i += 1;
    }
    count
}

fn contains_char(s: &str, c: char) -> bool {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut i = 0usize;
    while i < n {
        if bytes[i] as char == c {
            return true;
        }
        i += 1;
    }
    false
}

fn replace_char(s: &str, from: char, to: char) -> String {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut result = String::with_capacity(n);
    let mut i = 0usize;
    while i < n {
        let c = bytes[i] as char;
        if c == from {
            result.push(to);
        } else {
            result.push(c);
        }
        i += 1;
    }
    result
}

fn split_on_delims(s: &str) -> Vec<String> {
    let bytes = s.as_bytes();
    let n = bytes.len();
    let mut parts: Vec<String> = Vec::new();
    let mut current = String::new();
    let mut i = 0usize;
    while i < n {
        let c = bytes[i] as char;
        if c == '.' || c == ',' {
            if !current.is_empty() {
                parts.push(current);
                current = String::new();
            }
        } else {
            current.push(c);
        }
        i += 1;
    }
    if !current.is_empty() {
        parts.push(current);
    }
    parts
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Check if a string is a word (all alphabetic).
    fn is_word(s: &str) -> bool {
        if s.is_empty() {
            return false;
        }
        let bytes = s.as_bytes();
        let n = bytes.len();
        let mut i = 0usize;
        while i < n {
            if !is_alphabetic(bytes[i] as char) {
                return false;
            }
            i += 1;
        }
        true
    }

    /// Check if a string is a number (all digits, possibly with decimal point).
    fn is_number(s: &str) -> bool {
        if s.is_empty() {
            return false;
        }
        let bytes = s.as_bytes();
        let n = bytes.len();
        let mut has_digit = false;
        let mut has_dot = false;
        let mut i = 0usize;
        while i < n {
            let c = bytes[i] as char;
            if is_ascii_digit(c) {
                has_digit = true;
            } else if c == '.' && !has_dot {
                has_dot = true;
            } else {
                return false;
            }
            i += 1;
        }
        has_digit
    }

    #[test]
    fn test_simple_date() {
        let tokens = Tokenizer::split("2024-01-15");
        assert_eq!(tokens, vec!["2024", "-", "01", "-", "15"]);
    }

    #[test]
    fn test_datetime_with_t() {
        let tokens = Tokenizer::split("2024-01-15T10:30:00");
        assert_eq!(
            tokens,
            vec!["2024", "-", "01", "-", "15", "T", "10", ":", "30", ":", "00"]
        );
    }

    #[test]
    fn test_named_month() {
        let tokens = Tokenizer::split("Jan 15, 2024");
        assert_eq!(tokens, vec!["Jan", " ", "15", ",", " ", "2024"]);
    }

    #[test]
    fn test_month_with_dot() {
        let tokens = Tokenizer::split("Sep.20.2009");
        assert_eq!(tokens, vec!["Sep", ".", "20", ".", "2009"]);
    }

    #[test]
    fn test_decimal_time() {
        let tokens = Tokenizer::split("4:30:21.447");
        assert_eq!(tokens, vec!["4", ":", "30", ":", "21.447"]);
    }

    #[test]
    fn test_timezone() {
        let tokens = Tokenizer::split("2024-01-15T10:30:00-05:00");
        assert_eq!(
            tokens,
            vec![
                "2024", "-", "01", "-", "15", "T", "10", ":", "30", ":", "00", "-", "05", ":", "00"
            ]
        );
    }

    #[test]
    fn test_whitespace() {
        // dateutil keeps separate whitespace tokens (each space is a token)
        let tokens = Tokenizer::split("January   15,  2024");
        assert_eq!(
            tokens,
            vec!["January", " ", " ", " ", "15", ",", " ", " ", "2024"]
        );
    }

    #[test]
    fn test_am_pm() {
        let tokens = Tokenizer::split("9:30 AM");
        assert_eq!(tokens, vec!["9", ":", "30", " ", "AM"]);
    }

    #[test]
    fn test_ordinal() {
        let tokens = Tokenizer::split("January 15th, 2024");
        assert_eq!(tokens, vec!["January", " ", "15", "th", ",", " ", "2024"]);
    }

    #[test]
    fn test_is_word() {
        assert!(is_word("January"));
        assert!(is_word("AM"));
        assert!(!is_word("2024"));
        assert!(!is_word("15th"));
        assert!(!is_word(""));
    }

    #[test]
    fn test_is_number() {
        assert!(is_number("2024"));
        assert!(is_number("15"));
        assert!(is_number("21.447"));
        assert!(!is_number("January"));
        assert!(!is_number("15th"));
        assert!(!is_number(""));
    }

    #[test]
    fn test_decimal_number() {
        // Pure decimal number stays as single token
        let tokens = Tokenizer::split("100.264400");
        assert_eq!(tokens, vec!["100.264400"]);
    }

    #[test]
    fn test_european_decimal() {
        // European style comma decimal (only when token has 2+ digits before comma)
        // Single digit before comma - comma is separator
        let tokens = Tokenizer::split("3,14159");
        assert_eq!(tokens, vec!["3", ",", "14159"]);

        // 2+ digits before comma - comma is decimal point
        let tokens = Tokenizer::split("30,14159");
        assert_eq!(tokens, vec!["30.14159"]);
    }
}
