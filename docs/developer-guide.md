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

## Setting Up the Development Environment

```bash
# Clone the repository
git clone https://github.com/bissli/opendate.git
cd opendate

# Install dependencies with poetry
poetry install --extras test

# Build and install the native extension locally
maturin develop --release

# Verify installation
python -c "from date import Date; print(Date.today())"

# Run tests to confirm everything works
pytest tests/
```

## Development Workflow

### Making Changes to Python Code

```bash
# Edit Python files in src/date/
# Then run tests
pytest tests/
```

### Making Changes to Rust Code

```bash
# Edit Rust files in rust/src/
# Rebuild the native extension
maturin develop --release

# Run tests
pytest tests/
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_date.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=date
```

## Building

### Development Build

```bash
# Build and install in development mode (editable)
maturin develop --release
```

### Production Build

```bash
# Build a wheel for your current platform
maturin build --release

# Wheel is created in rust/target/wheels/
ls rust/target/wheels/
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

1. **Ensure all changes are committed:**
   ```bash
   git status  # Should be clean
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
├── rust/
│   ├── Cargo.toml          # Rust package config
│   ├── pyproject.toml      # Maturin build config
│   └── src/
│       ├── lib.rs          # Module exports
│       ├── calendar.rs     # BusinessCalendar implementation
│       └── python.rs       # PyO3 bindings
├── src/
│   └── date/
│       ├── __init__.py
│       ├── date.py         # Main implementation
│       └── extras.py       # Legacy functions
├── tests/
├── docs/
│   └── developer-guide.md  # This file
└── .github/
    └── workflows/
        └── release.yml     # CI/CD pipeline
```

## Rust Files: What to Commit

**Check in (source files):**
```
rust/
├── Cargo.toml              # ✓ Rust package config
├── pyproject.toml          # ✓ Maturin build config
└── src/
    ├── lib.rs              # ✓ Module exports
    ├── calendar.rs         # ✓ BusinessCalendar implementation
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
maturin develop --release
```

### Tests fail after changing Rust code
Rebuild the extension:
```bash
maturin develop --release
pytest tests/
```

### PyPI publish fails with "version already exists"
The version was already published. Bump to a new version:
```bash
bump2version patch
git push origin master --tags
```
