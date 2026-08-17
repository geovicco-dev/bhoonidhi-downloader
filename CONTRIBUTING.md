# Contributing to bhoonidhi-downloader

Thanks for taking the time to contribute. This tool exists because programmatic
access to ISRO's Bhoonidhi archive was hard, and every bug report, question, and
patch helps make it easier for the next person. Contributions of all kinds are
welcome — code, documentation, bug reports, and use-case ideas alike.

## Ways to help

- **Report a bug** — open an issue with steps to reproduce.
- **Suggest a feature** — open an issue describing the problem you're trying to
  solve, before writing code. It saves everyone effort if we agree on the
  direction first.
- **Improve the docs** — fixes to unclear or missing documentation are as
  valuable as code.
- **Submit a fix or feature** — see the workflow below.

## Development setup

You'll need [uv](https://docs.astral.sh/uv/). Then:

```shell
git clone https://github.com/geovicco-dev/bhoonidhi-downloader.git
cd bhoonidhi-downloader
uv sync --group dev
```

## Before you open a pull request

Run the same checks CI runs, and make sure they pass:

```shell
uv run ruff check src/          # lint
uv run ruff format --check src/  # formatting
uv run pytest                    # tests
```

If you add or change behaviour, please add or update a test for it. If you're
fixing a bug, a test that fails before your fix and passes after is the ideal.

## Pull request workflow

1. **Open an issue first** for anything beyond a small fix, so we can agree on
   the approach.
2. **One change per pull request.** Keep each PR focused on a single feature or
   fix — it's easier to review and to revert if needed.
3. **Branch** from `main` with a short, descriptive name (e.g.
   `fix/cart-date-window` or `feat/point-radius-search`).
4. **Match the existing style.** The codebase separates logic into
   client/command/render layers and uses Pydantic models for data — follow the
   patterns already there rather than introducing new ones.
5. **Write a clear commit message** describing what changed and why.
6. **Update the docs and `CHANGELOG.md`** if your change affects users. The
   changelog follows the [Keep a Changelog](https://keepachangelog.com) format
   with `Added` / `Changed` / `Fixed` sections.
7. **Open the PR** against `main` and fill in the template. Describe what the
   change does and link the issue it closes.

## Reporting a security issue

Please don't open a public issue for security problems. Instead, email the
maintainer at <geovicco.dev@gmail.com> so it can be addressed before disclosure.

## Code of conduct

Please be respectful and constructive in all interactions. We want this to be a
welcoming project for people of every background and experience level. Harassment
or dismissive behaviour isn't tolerated.

## Questions

If you're unsure about anything, open an issue and ask. No question is too small,
and asking early is always better than guessing.
