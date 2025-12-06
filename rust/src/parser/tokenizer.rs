//! Tokenizer for datetime strings.
//!
//! Port of dateutil.parser._timelex to Rust.

/// Token type returned by the tokenizer.
#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    /// A word (letters only)
    Word(String),
    /// A number (digits only, may include decimal point)
    Number(String),
    /// Whitespace (normalized to single space)
    Space,
    /// Single separator character
    Separator(char),
}

impl Token {
    /// Get the string value of the token.
    pub fn as_str(&self) -> &str {
        match self {
            Token::Word(s) | Token::Number(s) => s,
            Token::Space => " ",
            Token::Separator(c) => {
                // This is a bit of a hack but works for single chars
                // In practice, callers should handle separators specially
                match c {
                    '.' => ".",
                    ',' => ",",
                    '-' => "-",
                    '/' => "/",
                    ':' => ":",
                    '+' => "+",
                    _ => "",
                }
            }
        }
    }

    /// Check if this token is a word.
    pub fn is_word(&self) -> bool {
        matches!(self, Token::Word(_))
    }

    /// Check if this token is a number.
    pub fn is_number(&self) -> bool {
        matches!(self, Token::Number(_))
    }
}

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
pub struct Tokenizer<'a> {
    input: &'a str,
    chars: std::iter::Peekable<std::str::CharIndices<'a>>,
    charstack: Vec<(usize, char)>,
    tokenstack: Vec<String>,
    eof: bool,
}

impl<'a> Tokenizer<'a> {
    /// Create a new tokenizer for the given input string.
    pub fn new(input: &'a str) -> Self {
        Tokenizer {
            input,
            chars: input.char_indices().peekable(),
            charstack: Vec::new(),
            tokenstack: Vec::new(),
            eof: false,
        }
    }

    /// Split a string into tokens.
    pub fn split(input: &str) -> Vec<String> {
        let tokenizer = Tokenizer::new(input);
        tokenizer.map(|t| t.to_string()).collect()
    }

    /// Get the next character, filtering null bytes.
    fn next_char(&mut self) -> Option<(usize, char)> {
        if let Some(item) = self.charstack.pop() {
            return Some(item);
        }

        loop {
            match self.chars.next() {
                Some((_, '\0')) => continue, // Filter null bytes
                Some(item) => return Some(item),
                None => return None,
            }
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
            return Some(self.tokenstack.remove(0));
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
                    if nextchar.is_alphabetic() {
                        state = State::Word;
                    } else if nextchar.is_ascii_digit() {
                        state = State::Number;
                    } else if nextchar.is_whitespace() {
                        token = " ".to_string();
                        break;
                    } else {
                        break; // Single separator
                    }
                }
                State::Word => {
                    seen_letters = true;
                    if nextchar.is_alphabetic() {
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
                    if nextchar.is_ascii_digit() {
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
                    if nextchar == '.' || nextchar.is_alphabetic() {
                        token.push(nextchar);
                    } else if nextchar.is_ascii_digit() && token.ends_with('.') {
                        token.push(nextchar);
                        state = State::NumberDot;
                    } else {
                        self.push_char((idx, nextchar));
                        break;
                    }
                }
                State::NumberDot => {
                    if nextchar == '.' || nextchar.is_ascii_digit() {
                        token.push(nextchar);
                    } else if nextchar.is_alphabetic() && token.ends_with('.') {
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
        if (state == State::WordDot || state == State::NumberDot)
            && (seen_letters || token.matches('.').count() > 1 || token.ends_with(['.', ',']))
        {
            // Clone before splitting to avoid borrow issues
            let original = token.clone();

            // Split on dots and commas
            let parts: Vec<&str> = original
                .split(|c| c == '.' || c == ',')
                .filter(|s| !s.is_empty())
                .collect();

            if !parts.is_empty() {
                token = parts[0].to_string();

                // Find separators by walking the original string
                let mut pos = parts[0].len();
                for part in parts.iter().skip(1) {
                    if pos < original.len() {
                        let sep = original.chars().nth(pos).unwrap_or('.');
                        self.tokenstack.push(sep.to_string());
                        pos += 1;
                    }
                    self.tokenstack.push((*part).to_string());
                    pos += part.len();
                }

                // Handle trailing separator
                if pos < original.len() {
                    let trailing_sep = original.chars().nth(pos).unwrap_or('.');
                    if trailing_sep == '.' || trailing_sep == ',' {
                        self.tokenstack.push(trailing_sep.to_string());
                    }
                }
            }
        }

        // Convert comma decimal to dot for numbers
        if state == State::NumberDot && !token.contains('.') {
            token = token.replace(',', ".");
        }

        if token.is_empty() {
            None
        } else {
            Some(token)
        }
    }
}

impl<'a> Iterator for Tokenizer<'a> {
    type Item = String;

    fn next(&mut self) -> Option<Self::Item> {
        self.get_token()
    }
}

/// Check if a string is a word (all alphabetic).
pub fn is_word(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_alphabetic())
}

/// Check if a string is a number (all digits, possibly with decimal point).
pub fn is_number(s: &str) -> bool {
    if s.is_empty() {
        return false;
    }
    let mut has_digit = false;
    let mut has_dot = false;
    for c in s.chars() {
        if c.is_ascii_digit() {
            has_digit = true;
        } else if c == '.' && !has_dot {
            has_dot = true;
        } else {
            return false;
        }
    }
    has_digit
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_date() {
        let tokens: Vec<_> = Tokenizer::split("2024-01-15");
        assert_eq!(tokens, vec!["2024", "-", "01", "-", "15"]);
    }

    #[test]
    fn test_datetime_with_t() {
        let tokens: Vec<_> = Tokenizer::split("2024-01-15T10:30:00");
        assert_eq!(
            tokens,
            vec!["2024", "-", "01", "-", "15", "T", "10", ":", "30", ":", "00"]
        );
    }

    #[test]
    fn test_named_month() {
        let tokens: Vec<_> = Tokenizer::split("Jan 15, 2024");
        assert_eq!(tokens, vec!["Jan", " ", "15", ",", " ", "2024"]);
    }

    #[test]
    fn test_month_with_dot() {
        let tokens: Vec<_> = Tokenizer::split("Sep.20.2009");
        assert_eq!(tokens, vec!["Sep", ".", "20", ".", "2009"]);
    }

    #[test]
    fn test_decimal_time() {
        let tokens: Vec<_> = Tokenizer::split("4:30:21.447");
        assert_eq!(tokens, vec!["4", ":", "30", ":", "21.447"]);
    }

    #[test]
    fn test_timezone() {
        let tokens: Vec<_> = Tokenizer::split("2024-01-15T10:30:00-05:00");
        assert_eq!(
            tokens,
            vec!["2024", "-", "01", "-", "15", "T", "10", ":", "30", ":", "00", "-", "05", ":", "00"]
        );
    }

    #[test]
    fn test_whitespace() {
        // dateutil keeps separate whitespace tokens (each space is a token)
        let tokens: Vec<_> = Tokenizer::split("January   15,  2024");
        assert_eq!(
            tokens,
            vec!["January", " ", " ", " ", "15", ",", " ", " ", "2024"]
        );
    }

    #[test]
    fn test_am_pm() {
        let tokens: Vec<_> = Tokenizer::split("9:30 AM");
        assert_eq!(tokens, vec!["9", ":", "30", " ", "AM"]);
    }

    #[test]
    fn test_ordinal() {
        let tokens: Vec<_> = Tokenizer::split("January 15th, 2024");
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
        let tokens: Vec<_> = Tokenizer::split("100.264400");
        assert_eq!(tokens, vec!["100.264400"]);
    }

    #[test]
    fn test_european_decimal() {
        // European style comma decimal (only when token has 2+ digits before comma)
        // Single digit before comma - comma is separator
        let tokens: Vec<_> = Tokenizer::split("3,14159");
        assert_eq!(tokens, vec!["3", ",", "14159"]);

        // 2+ digits before comma - comma is decimal point
        let tokens: Vec<_> = Tokenizer::split("30,14159");
        assert_eq!(tokens, vec!["30.14159"]);
    }
}
