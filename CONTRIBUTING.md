# Contributing to Rheo

Thanks for your interest in contributing! We care about code quality and clear communication, but we're not fussy about how you get there. Make the codebase better, and we'll be very grateful.

## Development Setup

```bash
# Clone and install
git clone https://github.com/plutopulp/rheo.git
cd rheo
poetry install
```

**Requirements:**

- Python 3.11+
- Poetry

## Code Quality

Before submitting, run the full CI suite locally:

```bash
make ci  # Run all checks locally
```

This runs:

- Formatting checks (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Tests with coverage

**CI runs automatically on GitHub** when you push or open a PR, testing on Python 3.11, 3.12, 3.13, and 3.14.

## Testing

```bash
make test        # Run tests with coverage
make test-quick  # Faster, no coverage report
pytest -m network  # Include network tests (skipped by default)
```

**What we care about:**

- Tests should be meaningful, not just to chase coverage percentage
- If you're fixing a bug, please try to add a test that would have caught it
- If you're adding a feature, test the key behaviour
- Network tests should be marked with `@pytest.mark.network`

## Code Style

**The basics:**

- Use Black formatting and isort
- Full type hints (mypy will complain if you don't)
- British English in docs and comments
- Look at existing code and match the style

**Architecture patterns we use:**

- Dependency injection (inject via constructors)
- Events over callbacks
- See `docs/ARCHITECTURE.md` for details

Don't worry about memorising everything though, reviews will guide you.

## Pull Request Process

**What makes a good PR:**

- **Clear description** explain what and why
- **Tests pass** - `make ci` should be green
- **Focused scope** - one thing per PR when possible
- **Documentation** - update docs if you changed behaviour

**Steps:**

- Fork and create a feature branch from `main`
- Make your changes
- Ensure `make ci` passes
- Open PR with clear description

**PR description should answer:**

- What does this change?
- Why is it needed?
- How did you test it?
- Any breaking changes?

## Commit Messages

Good commit messages are appreciated but not a blocker at all.

Good enough:

```text
Add bandwidth throttling support
Fix timeout handling in retry logic
Update README examples
```

## Running Examples

```bash
poetry run examples/{example_file}.py
```

## Getting Help

Open an issue if you:

- Have questions about implementation
- Want to discuss a design decision
- Need clarification on anything

We're happy to help!
