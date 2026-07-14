# Repository Guidelines

## Project Structure & Module Organization

Core Python code lives in `src/faster_whisper_transwithai_chickenrice/`. The root `infer.py` is a thin development and packaged-entry wrapper; `modal_infer.py`, `download_models.py`, and `build_windows.py` provide cloud inference, model download, and Windows packaging workflows. Tests are in `tests/` and mirror behavior rather than package layout. User-facing assets include `locales/*/messages.json`, `generation_config.json5`, the Chinese `.bat` launchers, and `transwithai.ico`. Conda environments are defined by `environment-*.yml`; PyInstaller inputs are `project.spec` and `modal.spec`.

## Build, Test, and Development Commands

Use Python 3.10 in the appropriate Conda environment.

- `python infer.py --help` — smoke-check the local CLI without running inference.
- `python -m unittest discover -s tests -p "test_*.py"` — run the unit test suite.
- `ruff check .` — run lint and import-order checks.
- `ruff format --check .` — verify formatting; use `ruff format .` to apply it.
- `mypy --config-file pyproject.toml src infer.py download_models.py modal_infer.py build_windows.py runtime_hook.py` — match CI type checking.
- `python build_windows.py` — build the PyInstaller distribution under `dist/`; run this only in a fully provisioned Windows environment.

Install and run `pre-commit` when available; its hooks fix Ruff issues and reject whitespace, malformed YAML, and oversized additions.

## Coding Style & Naming Conventions

Follow Ruff settings in `pyproject.toml`: four-space indentation, double quotes, 120-character lines, and Python 3.10 syntax. Use `snake_case` for functions and modules, `PascalCase` for classes, and uppercase names for constants. Keep root scripts thin when logic belongs in the package. Preserve UTF-8 text and existing bilingual user-facing wording.

## Testing Guidelines

Tests use the standard-library `unittest` framework. Name files `test_*.py`, classes `*Tests`, and methods `test_*`. Add a focused regression test for behavior changes. There is no numeric coverage gate; prioritize CLI configuration, download reliability, VAD, and timestamp behavior.

## Commit & Pull Request Guidelines

History primarily uses Conventional Commit prefixes such as `feat:`, `fix:`, `ci:`, and `chore:`. Keep subjects imperative and scoped to one change. Pull requests should explain user-visible impact, list validation commands, link relevant issues, and include logs or screenshots for CLI/build changes. Do not commit generated `dist/`, model files, logs, virtual environments, or Modal credentials.
