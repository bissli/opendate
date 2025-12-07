# Developer Guide

## Prerequisites

- **Python 3.9+**
- **Rust** - Install via [rustup](https://rustup.rs/):
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  source ~/.cargo/env
  ```
- **Poetry** - Install via [pipx](https://python-poetry.org/docs/#installation):
  ```bash
  pipx install poetry
  ```
- **Maturin** - Install via pip:
  ```bash
  pip install maturin
  ```

## Quick Start

```bash
git clone https://github.com/bissli/opendate.git
cd opendate
make dev      # Install dependencies and build native extension
make test     # Run tests
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make dev` | Install dependencies and build native extension |
| `make build` | Build native extension only |
| `make test` | Run all tests |
| `make lint` | Run all linters (Python + Rust) |
| `make lint-rust` | Check Rust formatting and clippy |
| `make format-rust` | Auto-format Rust code |
| `make clean` | Remove build artifacts |

## Setting Up the Development Environment

```bash
# Clone the repository
git clone https://github.com/bissli/opendate.git
cd opendate

# Option 1: Use make (recommended)
make dev

# Option 2: Manual steps
poetry install --extras test
maturin develop --release

# Verify installation
python -c "from date import Date; print(Date.today())"
```

## Development Workflow

### Making Changes to Python Code

```bash
# Edit Python files in src/date/
# Then run tests
make test
```

### Making Changes to Rust Code

```bash
# Edit Rust files in rust/src/
# Rebuild and test
make build
make test
```

### Running Tests

```bash
# Run all tests (recommended)
make test

# Or use pytest directly for more options:
pytest tests/              # Run all tests
pytest tests/test_date.py  # Run specific test file
pytest tests/ -v           # Verbose output
pytest tests/ --cov=date   # With coverage
```

### Linting

```bash
# Check Rust formatting and lints
make lint-rust

# Auto-format Rust code
make format-rust
```

## Building

### Development Build

```bash
# Recommended
make build

# Or manually
maturin develop --release
```

### Local Wheel Build (for testing)

```bash
# Build a wheel for your current platform only
maturin build --release

# Wheel is created in rust/target/wheels/
ls rust/target/wheels/
```

> **Note:** For releases, GitHub Actions automatically builds wheels for all platforms
> (Linux, macOS, Windows) and Python versions (3.9-3.13). Do not manually upload
> wheels to PyPI—use the release process below instead.

### Clean Build Artifacts

```bash
make clean
```

## Version Management

The project uses `bump2version` for version management:

```bash
# Bump patch version (0.1.23 → 0.1.24)
bump2version patch

# Bump minor version (0.1.24 → 0.2.0)
bump2version minor

# Bump major version (0.2.0 → 1.0.0)
bump2version major
```

This automatically:
- Updates version in `pyproject.toml`
- Creates a git commit with message "Bump version: X.Y.Z → X.Y.W"
- Creates a git tag `X.Y.W`

## Releasing

### Release Process

1. **Ensure all changes are committed and tests pass:**
   ```bash
   git status    # Should be clean
   make test     # Should pass
   make lint     # Should pass
   ```

2. **Bump the version:**
   ```bash
   bump2version patch  # or minor/major
   ```

3. **Push commit and tag to GitHub:**
   ```bash
   git push origin master --tags
   ```

4. **GitHub Actions automatically:**
   - Verifies tag matches pyproject.toml version
   - Checks if version already exists on PyPI (skips if exists)
   - Builds wheels for all platforms:
     - Linux (x86_64, aarch64) - glibc and musl
     - macOS (x86_64, Apple Silicon)
     - Windows (x86_64)
   - Builds for Python 3.9, 3.10, 3.11, 3.12, 3.13
   - Creates a GitHub Release with all wheel artifacts
   - Publishes to PyPI

5. **Verify the release:**
   - Check [GitHub Actions](https://github.com/bissli/opendate/actions) for build status
   - Check [PyPI](https://pypi.org/project/opendate/) for the new version
   - Test installation: `pip install opendate==X.Y.Z`

### GitHub Actions Setup (One-time)

1. **Create a "release" environment** in your GitHub repository:
   - Go to Settings → Environments → New environment
   - Name it `release`

2. **Configure PyPI Trusted Publishing:**
   - Go to [pypi.org](https://pypi.org) → Your Project → Publishing
   - Add a new trusted publisher:
     - Owner: `bissli`
     - Repository: `opendate`
     - Workflow: `release.yml`
     - Environment: `release`

## Project Structure

```
opendate/
├── pyproject.toml          # Project config (maturin build-backend)
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
│   └── date/
│       ├── __init__.py     # Public API and factory functions
│       ├── constants.py    # Timezone instances, WeekDay enum
│       ├── helpers.py      # Utility functions, Rust parser bridge
│       ├── decorators.py   # Type conversion decorators
│       ├── calendars.py    # Calendar classes (NYSE, custom)
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

The Python code follows a modular architecture inspired by Pendulum:
- Core classes in separate files (`date_.py`, `datetime_.py`, etc.)
- Shared behavior via mixins
- Circular imports avoided using `import date` at module level

## Rust Native Extension

The `_opendate` module provides high-performance native implementations:

### BusinessCalendar

Efficient business day calculations using ordinal-based lookups:
- `is_business_day(ordinal)` - Check if date is a business day
- `add_business_days(ordinal, n)` - Add/subtract business days
- `next_business_day(ordinal)` / `prev_business_day(ordinal)` - Find adjacent business days
- `count_business_days(start, end)` - Count business days in range

### Parser (dateutil port)

A Rust port of `python-dateutil`'s parser for fast datetime parsing:
- `parse(timestr, ...)` - Parse arbitrary datetime strings (dateutil-compatible)
- `isoparse(dt_str)` - Parse ISO-8601 datetime strings
- `parse_time(timestr)` - Parse standalone time strings

The parser supports the same formats as dateutil including fuzzy parsing,
dayfirst/yearfirst options, and AM/PM handling.

## Rust Files: What to Commit

**Check in (source files):**
```
rust/
├── Cargo.toml              # ✓ Rust package config
└── src/
    ├── lib.rs              # ✓ Module exports
    ├── calendar.rs         # ✓ BusinessCalendar implementation
    ├── parser/             # ✓ Dateutil-compatible parser
    │   ├── mod.rs
    │   ├── core.rs
    │   ├── iso.rs
    │   ├── parserinfo.rs
    │   ├── tokenizer.rs
    │   ├── ymd.rs
    │   ├── result.rs
    │   └── errors.rs
    └── python.rs           # ✓ PyO3 bindings
```

**Ignored (build artifacts in .gitignore):**
```
rust/
├── Cargo.lock              # ✗ Dependency lock (regenerated on build)
└── target/                 # ✗ Build output directory
*.so                        # ✗ Compiled shared libraries
```

The `Cargo.lock` is ignored because this is a library crate. For libraries, the lock file
is regenerated when building to use the latest compatible dependencies.

## Troubleshooting

### "command not found: rustc"
Rust is not installed or not in PATH:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### "command not found: maturin"
Install maturin:
```bash
pip install maturin
```

### "No module named '_opendate'"
The native extension is not built. Run:
```bash
make build
```

### Tests fail after changing Rust code
Rebuild the extension:
```bash
make build
make test
```

### PyPI publish fails with "version already exists"
The version was already published. Bump to a new version:
```bash
bump2version patch
git push origin master --tags
```
