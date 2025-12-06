//! Datetime parser module - port of dateutil.parser.
//!
//! This module provides a high-performance datetime parser that matches
//! dateutil's behavior exactly, supporting a wide variety of date/time formats.

mod core;
mod errors;
mod iso;
mod parserinfo;
mod result;
mod tokenizer;
mod ymd;

pub use core::Parser;
pub use errors::ParserError;
pub use iso::IsoParser;
pub use parserinfo::ParserInfo;
pub use result::{ParseResult, PyParseResult};
pub use tokenizer::Tokenizer;
pub use ymd::YMD;
