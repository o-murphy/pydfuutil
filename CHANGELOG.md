# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Static type checking with [ty](https://github.com/astral-sh/ty), wired into `pre-commit` and a dedicated `ty.yml` CI workflow.
- `usb-stubs/` PEP 561 stub package for `pyusb`, filling in previously-missing submodules (`usb.legacy`, `usb._lookup`, `usb.backend`, `usb._objfinalizer`, etc.) so the codebase type-checks cleanly end to end.
- `pre-commit` configuration (`uv sync`, `ty check`).

### Changed
- Renamed CI workflow `python-package.yml` to `pytest.yml`.
- Bumped CI/build tooling and dependencies (`actions/checkout` 6→7, `ruff`, `dependabot` config).
- `pydfuutil-suffix`/`pydfuutil-prefix` now parse the target file with `pathlib.Path` instead of `argparse.FileType('r+b')`.
- Removed the unused, unreferenced `_old/__main__.py` legacy module (~1000 lines of dead code from an earlier implementation).

### Fixed
- `usb_dfu.py` imported `Union` from `ctypes` instead of `typing`, which broke `FuncDescriptor` — and by extension the whole `pydfuutil.dfu` import chain — at import time.
- `dfu.py`: `_get_state()` derived the DFU state from a boolean comparison instead of the actual status byte, so it almost never reported the correct device state.
- `dfu_util.py` (`_found_dfu`/`probe_configuration`) interface/alt-setting/vendor/product matching, re-verified against the upstream C source: a wrongly-gated `-a`/`--alt` filter, a copy-pasted `PrefixReq`/`SuffixReq` mixup, a `quirks and QUIRK.X` (logical instead of bitwise `&`) bug, a missing `-c`/`--cfg` filter, an interface-loop comparison against the wrong attribute, and `probe_configuration()` stopping after the first matching USB configuration instead of scanning all of them.
- `dfuse.py`: `upload()`/`do_upload()` mismatched their own return type (treated a raw USB read result as a status code), never incremented the DFU transaction counter across retries, and confused a CRC checksum with a byte count in the transfer bookkeeping.
- Assorted `Optional`/type-narrowing correctness fixes surfaced by the new `ty` type checker across `dfu.py`, `dfu_file.py`, `dfu_load.py`, `dfuse.py`, `dfuse_mem.py`, `dfu_util.py`, `exceptions.py`, `lsusb.py`, `prefix.py`, `progress.py`, `quirks.py`, and `usb_dfu.py`.
- `ruff` lint errors across the codebase.

[Unreleased]: https://github.com/o-murphy/pydfuutil/compare/v0.11.0b1...HEAD
</content>
