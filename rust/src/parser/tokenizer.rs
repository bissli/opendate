//! Tokenizer for datetime strings.
//!
//! Port of dateutil.parser._timelex to Rust.

/// State machine states for tokenization.
#[derive(Debug, Clone, Copy, PartialEq)]
enum State {
    Initial,
    /// 'a' - reading a word
    Word,
    /// '0' - reading a number
    Number,
    /// 'a.' - word followed by dot
    WordDot,
    /// '0.' - number followed by dot
    NumberDot,
}

/// Tokenizer for datetime strings.
///
/// Breaks strings into lexical units: words, numbers, whitespace, and
/// separators.
pub struct Tokenizer {
    chars: Vec<char>,
    pos: usize,
    charstack: Vec<(usize, char)>,
    tokenstack: Vec<String>,
    eof: bool,
}

impl Tokenizer {
    /// Create a new tokenizer for the given input string.
    pub fn new(input: &str) -> Self {
        Tokenizer {
            chars: input.chars().collect(),
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
            if self.pos >= self.chars.len() {
                return None;
            }
            let idx = self.pos;
            let c = self.chars[self.pos];
            self.pos += 1;
            if c == '\0' {
                continue;
            }
            return Some((idx, c));
        }
    }

    /// Push a character back onto the stack.
    fn push_char(&mut self, item: (usize, char)) {
        self.charstack.push(item);
    }

    /// Get the next token.
    pub fn get_token(&mut self) -> Option<String> {
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
                        break;
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

        let dot_count = count_char(&token, '.');
        if (state == State::WordDot || state == State::NumberDot)
            && (seen_letters
                || dot_count > 1
                || ends_with_char(&token, '.')
                || ends_with_char(&token, ','))
        {
            let original = token.clone();

            let parts = split_on_delims(&original);

            if !parts.is_empty() {
                token = parts[0].clone();

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

                if pos < orig_len {
                    let trailing_sep = orig_bytes[pos] as char;
                    if trailing_sep == '.' || trailing_sep == ',' {
                        self.tokenstack.push(trailing_sep.to_string());
                    }
                }
            }
        }

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
    c.is_alphabetic()
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
    let chars: Vec<char> = s.chars().collect();
    let n = chars.len();
    let mut result = String::with_capacity(s.len());
    let mut i = 0usize;
    while i < n {
        let c = chars[i];
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
    let chars: Vec<char> = s.chars().collect();
    let n = chars.len();
    let mut parts: Vec<String> = Vec::new();
    let mut current = String::new();
    let mut i = 0usize;
    while i < n {
        let c = chars[i];
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

    /// Verify a dashed date splits into numbers and dash separators.
    ///
    /// Mutation: the Number state absorbing '-' into the number token.
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_simple_date() {
        let tokens = Tokenizer::split("2024-01-15");
        assert_eq!(tokens, vec!["2024", "-", "01", "-", "15"]);
    }

    /// Verify the ISO 'T' splits from the digits around it.
    ///
    /// Mutation: the Word state absorbing digits, giving "T10".
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_datetime_with_t() {
        let tokens = Tokenizer::split("2024-01-15T10:30:00");
        assert_eq!(
            tokens,
            vec!["2024", "-", "01", "-", "15", "T", "10", ":", "30", ":", "00"]
        );
    }

    /// Verify "15," yields the number and a separate comma.
    ///
    /// Mutation: dropping the trailing-separator push, which loses the
    ///   comma after a two-digit number.
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_named_month() {
        let tokens = Tokenizer::split("Jan 15, 2024");
        assert_eq!(tokens, vec!["Jan", " ", "15", ",", " ", "2024"]);
    }

    /// Verify a dotted word-number run splits with its dots kept.
    ///
    /// Mutation: dropping the separator push between split parts.
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_month_with_dot() {
        let tokens = Tokenizer::split("Sep.20.2009");
        assert_eq!(tokens, vec!["Sep", ".", "20", ".", "2009"]);
    }

    /// Verify fractional seconds stay one token after a separator.
    ///
    /// Mutation: splitting every NumberDot token, without the
    ///   one-dot, digits-only exception.
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_decimal_time() {
        let tokens = Tokenizer::split("4:30:21.447");
        assert_eq!(tokens, vec!["4", ":", "30", ":", "21.447"]);
    }

    /// Verify a negative UTC offset splits into sign, hours and minutes.
    ///
    /// Mutation: the Initial state folding '-' into the next number,
    ///   giving "-05".
    /// Oracle: dateutil.parser._timelex.split on the same input.
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

    /// Verify each whitespace character becomes its own " " token.
    ///
    /// Mutation: the Initial state merging a whitespace run into one
    ///   token.
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_whitespace() {
        let tokens = Tokenizer::split("January   15,  2024");
        assert_eq!(
            tokens,
            vec!["January", " ", " ", " ", "15", ",", " ", " ", "2024"]
        );
    }

    /// Verify a word at end of input is still emitted.
    ///
    /// Mutation: returning None at end of input before the pending
    ///   token, which drops "AM".
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_am_pm() {
        let tokens = Tokenizer::split("9:30 AM");
        assert_eq!(tokens, vec!["9", ":", "30", " ", "AM"]);
    }

    /// Verify an ordinal suffix splits from its number.
    ///
    /// Mutation: the Number state accepting letters, giving "15th".
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_ordinal() {
        let tokens = Tokenizer::split("January 15th, 2024");
        assert_eq!(tokens, vec!["January", " ", "15", "th", ",", " ", "2024"]);
    }

    /// Verify a whole-input decimal number stays one token.
    ///
    /// Mutation: splitting a NumberDot token on its single dot.
    /// Oracle: dateutil.parser._timelex.split on the same input.
    #[test]
    fn test_decimal_number() {
        let tokens = Tokenizer::split("100.264400");
        assert_eq!(tokens, vec!["100.264400"]);
    }

    /// Verify a comma reads as a decimal point only after 2+ digits.
    ///
    /// Mutation: the `token.len() >= 2` guard relaxed to 1, or the
    ///   comma-to-dot conversion dropped.
    /// Oracle: dateutil.parser._timelex.split on the same input, at the
    ///   one- and two-digit threshold.
    #[test]
    fn test_european_decimal() {
        let tokens = Tokenizer::split("3,14159");
        assert_eq!(tokens, vec!["3", ",", "14159"]);

        let tokens = Tokenizer::split("30,14159");
        assert_eq!(tokens, vec!["30.14159"]);
    }

    /// Verify a non-ASCII character stays one char and a run of Unicode
    /// letters stays one word.
    ///
    /// Mutation: reading one char per UTF-8 byte, or an ASCII-only
    ///   letter test that splits "\u{e9}t\u{e9}" at each "\u{e9}".
    /// Oracle: dateutil.parser._timelex.split on the same inputs, which
    ///   keeps the en dash as one token and the accented word whole.
    #[test]
    fn test_non_ascii() {
        let tokens = Tokenizer::split("25 \u{2013} ok");
        assert_eq!(tokens, vec!["25", " ", "\u{2013}", " ", "ok"]);

        let tokens = Tokenizer::split("\u{e9}t\u{e9} 5 Jan");
        assert_eq!(tokens, vec!["\u{e9}t\u{e9}", " ", "5", " ", "Jan"]);

        let tokens = Tokenizer::split("\u{e9}t\u{e9}.20.2009");
        assert_eq!(tokens, vec!["\u{e9}t\u{e9}", ".", "20", ".", "2009"]);
    }
}
