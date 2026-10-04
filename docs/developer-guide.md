# Developer Guide

## Prerequisites

- Python 3.10 or later
- Rust, installed by [rustup](https://rustup.rs/):
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  source ~/.cargo/env
  ```
- Poetry, installed by [pipx](https://python-poetry.org/docs/#installation):
  ```bash
  pipx install poetry
  ```
- Maturin, installed by pip:
  ```bash
  pip install maturin
  ```

## Setup

```bash
git clone https://github.com/bissli/opendate.git
cd opendate
make dev      # Install dependencies and build the native extension
make test     # Run the tests
```

`make dev` is the two manual steps below, and the last line confirms the
build:

```bash
poetry install --extras test
maturin develop --release
python -c "from opendate import Date; print(Date.today())"
```

## Makefile Targets

| Target             | Effect                                              |
| ------------------ | --------------------------------------------------- |
| `make dev`         | Install dependencies and build the native extension |
| `make build`       | Build the native extension only                     |
| `make test`        | Run all tests                                       |
| `make lint`        | Run all linters (Python + Rust)                     |
| `make lint-rust`   | Check Rust formatting and clippy                    |
| `make format-rust` | Format Rust code                                    |
| `make clean`       | Remove build artifacts                              |

## Workflow

### Python Changes

Python sources live in `src/opendate/`. A change there is visible to the
tests at once:

```bash
pytest -p no:cacheprovider
```

### Rust Changes

Rust sources live in `rust/src/`. A Rust change reaches the Python tests
only after `maturin develop --release` (`make build`), which rewrites the
shared extension `src/opendate/_opendate*.so`:

```bash
make build
make test
```

The Rust checks run from `rust/`:

```bash
cargo test
cargo clippy -- -D warnings
cargo fmt --all -- --check
```

`make lint-rust` runs the last two; `make format-rust` applies the
formatter.

### Tests

```bash
make test                            # pytest tests/ -v
pytest -p no:cacheprovider           # The suite, with no .pytest_cache
pytest tests/test_date.py            # One file
pytest tests/ --cov=opendate         # With coverage
```

## Builds

### Development Build

```bash
make build            # maturin develop --release
```

### Local Wheel

```bash
maturin build --release
ls rust/target/wheels/
```

`maturin build` makes a wheel for the current platform only. Release
wheels for every platform and Python version come from GitHub Actions
through the release process below; no wheel is uploaded to PyPI by hand.

### Clean Tree

```bash
make clean
```

## Version Management

`bump2version` owns the version string. Its configuration in `setup.cfg`
names the files it rewrites:

```bash
bump2version patch    # X.Y.Z -> X.Y.(Z+1)
bump2version minor    # X.Y.Z -> X.(Y+1).0
bump2version major    # X.Y.Z -> (X+1).0.0
```

One run rewrites the version in `pyproject.toml` and
`src/opendate/__init__.py`, commits with the message
`Bump version: OLD -> NEW`, and tags the commit `NEW`.

## Release Process

1. A clean tree, with `make test` and `make lint` passing.
2. `bump2version patch` (or `minor` / `major`).
3. `git push origin master --tags`.
4. GitHub Actions then:
   - checks that the tag matches the `pyproject.toml` version
   - skips the publish when that version already exists on PyPI
   - builds wheels for Linux (x86_64, aarch64; glibc and musl), macOS
     (x86_64, Apple Silicon) and Windows (x86_64), for Python 3.10
     through 3.13
   - creates a GitHub Release holding the wheels
   - publishes to PyPI
5. The build status is on
   [GitHub Actions](https://github.com/bissli/opendate/actions), the
   new version on [PyPI](https://pypi.org/project/opendate/), and
   `pip install opendate==X.Y.Z` installs it.

### GitHub Actions Setup

The release workflow needs two one-time settings:

- A `release` environment in the GitHub repository (Settings >
  Environments > New environment).
- A PyPI trusted publisher on the project (pypi.org > the project >
  Publishing) with owner `bissli`, repository `opendate`, workflow
  `release.yml`, environment `release`.

## Project Structure

```
opendate/
├── pyproject.toml          # Project config (maturin build-backend)
├── setup.cfg               # bump2version config
├── Makefile                # Development shortcuts
├── rust/
│   ├── Cargo.toml          # Rust package config
│   └── src/
│       ├── lib.rs          # Module exports
│       ├── calendar.rs     # BusinessCalendar implementation
│       ├── parser/         # Dateutil-compatible parser (Rust port)
│       │   ├── mod.rs      # Module exports
│       │   ├── core.rs     # Main Parser implementation
│       │   ├── iso.rs      # ISO-8601 parser (IsoParser)
│       │   ├── parserinfo.rs # Parser configuration
│       │   ├── tokenizer.rs  # String tokenization
│       │   ├── ymd.rs      # Year/Month/Day resolution
│       │   ├── result.rs   # ParseResult type
│       │   └── errors.rs   # Error types
│       └── python.rs       # PyO3 bindings
├── src/
│   └── opendate/
│       ├── __init__.py     # Public API and factory functions
│       ├── constants.py    # Timezone instances, normalization, WeekDay enum
│       ├── helpers.py      # Rust parser bridge, decade bounds
│       ├── decorators.py   # Type conversion decorators
│       ├── calendars.py    # Calendar classes (exchange, custom)
│       ├── metaclass.py    # Wraps pendulum methods to keep calendar context
│       ├── date_.py        # Date class
│       ├── time_.py        # Time class
│       ├── datetime_.py    # DateTime class
│       ├── interval.py     # Interval class
│       ├── extras.py       # Legacy compatibility functions
│       └── mixins/         # Shared behavior mixins
│           ├── business.py # Business day calculations
│           └── extras_.py  # Additional date utilities
├── tests/
├── docs/
│   └── developer-guide.md  # This file
└── .github/
    └── workflows/
        ├── release.yml     # Release pipeline
        └── tests.yml       # CI tests
```

The Python package follows pendulum's layout:

- One class per module. A module whose name would shadow a stdlib
  module takes a trailing underscore (`date_.py`, `datetime_.py`,
  `time_.py`).
- Shared behavior lives in mixins.
- A metaclass wraps the pendulum methods that return a new value, so
  the result keeps the calendar context of the value it came from.
- A module that needs `Date` or `DateTime` at run time without a
  circular import uses `import opendate as _date` and resolves the
  class at call time.

## Rust Native Extension

The `_opendate` module holds the native implementations.

### BusinessCalendar

Business day arithmetic over sorted date ordinals:

- `is_business_day(ordinal)`
- `add_business_days(ordinal, n)`, negative `n` moving back
- `next_business_day(ordinal)` / `prev_business_day(ordinal)`
- `count_business_days(start, end)`, 0 when `start` is after `end`

### Parser

A Rust port of `python-dateutil`'s parser:

- `Parser` - arbitrary datetime strings, dateutil-compatible
- `IsoParser` - ISO-8601 strings; `24:00` parses as `00:00` on the
  next day
- `TimeParser` - standalone time strings

The parser reads the formats dateutil reads, with fuzzy parsing,
`dayfirst` / `yearfirst` options and AM/PM handling.

## Rust Files in Version Control

Checked in: `rust/Cargo.toml` and everything under `rust/src/`.

Ignored by `.gitignore`: `rust/Cargo.lock`, `rust/target/`, and every
`*.so`. `Cargo.lock` is ignored because the crate is a library; each
build regenerates it with the latest compatible dependencies.

## Troubleshooting

### Missing `rustc`

Rust is not installed or not on `PATH`:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### Missing `maturin`

```bash
pip install maturin
```

### Missing `_opendate` module

The native extension is not built:

```bash
make build
```

### Stale extension after a Rust change

The Python tests load `src/opendate/_opendate*.so`, which only a
rebuild updates:

```bash
make build
make test
```

### PyPI publish fails with "version already exists"

That version is already published. A new version fixes it:

```bash
bump2version patch
git push origin master --tags
```
