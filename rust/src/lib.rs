// Allow simple, readable code patterns over idiomatic Rust
#![allow(clippy::manual_range_contains)]
#![allow(clippy::len_zero)]
#![allow(clippy::redundant_pattern_matching)]
#![allow(clippy::manual_map)]
#![allow(clippy::collapsible_else_if)]
#![allow(clippy::nonminimal_bool)]
#![allow(clippy::manual_swap)]
#![allow(clippy::while_let_loop)]

mod calendar;
mod parser;
mod python;

pub use python::_opendate;
