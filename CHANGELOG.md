# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.2] - 2026-07-14

### Changed
- `libusb-package` is no longer a hard runtime dependency — it moved to the optional `libusb`
  extra (`pip install pydfuutil[libusb]`). Platforms that already ship a system `libusb` no longer
  need to pull in the bundled binary; `pydfuutil.DEFAULT_BACKEND` resolves to it when installed and
  falls back to pyusb's own system search (`DEFAULT_BACKEND = None`) otherwise. `__main__.py`,
  `dfu_util.py`, and `lsusb.py` now thread this resolved backend through every `usb.core.find()`
  call so they all go through the same loaded libusb instance instead of letting pyusb re-resolve
  it independently each time.
- `dfu_file.py`: CRC32 computation (`_load_file`'s suffix check, `_write_crc`) now delegates to a
  new `_crc32_buf()` helper backed by `zlib.crc32` instead of looping `crc32_byte()` in pure Python
  — ~250-500x faster on real firmware-sized buffers, bit-identical output. Accepts
  `bytes`/`bytearray`/`memoryview` and operates on a `memoryview` slice of the firmware buffer to
  avoid copying it. `crc32_byte()` is kept as the documented reference implementation.

### Fixed
- `pydfuutil/__init__.py`: a non-`ImportError` failure while resolving the `libusb_package`
  backend (e.g. `OSError` from a broken bundled binary) no longer crashes the whole package import;
  it's now caught and logged, falling back to `DEFAULT_BACKEND = None`.
- `ty` CI (`ty.yml`) failed on a clean `uv sync --dev` because `libusb_package` (now optional at
  runtime) wasn't resolvable in the type-checking environment; added it to the `dev` dependency
  group so `ty` can still resolve the import without making it a runtime requirement.

## [0.11.1] - 2026-07-13

### Removed
- Dropped support for Python ≤3.9. `requires-python` is now `>=3.10`; trove classifiers and
  `uv.lock` resolution markers for 3.9 have been removed accordingly.

### Changed
- Modernized type hints across the codebase, enabled by the Python 3.10 floor:
  `Optional[X]`/`Union[X, Y]` → `X | None`/`X | Y` (`dfu.py`, `dfu_file.py`, `dfu_util.py`,
  `dfuse.py`, `dfuse_mem.py`, `exceptions.py`, `lsusb.py`, `progress.py`, `__main__.py`,
  `usb_dfu.py`, `quirks.py`, `usb-stubs/core.pyi`, `usb-stubs/util.pyi`); `typing.Generator`/
  `Callable`/`Iterable`/`Iterator` (PEP 585, deprecated aliases of the `collections.abc` ABCs)
  → `collections.abc` (`dfu_util.py`, `lsusb.py`, `dfuse_mem.py`, `usb-stubs/core.pyi`,
  `usb-stubs/util.pyi`, `usb-stubs/backend/libusb1.pyi`).
- Added `from __future__ import annotations` (PEP 563) to every module in `pydfuutil/`, and
  dropped the now-unnecessary quotes on self-referencing forward-ref annotations
  (`DfuIf.next` in `dfu.py`; `MemSegment.next`/`from_bytes`/`append`/`find` in `dfuse_mem.py`;
  `FuncDescriptor.from_bytes` in `usb_dfu.py`, also dropping its `# noqa: F821`).
- Bumped dev dependencies (`pytest`, `ty`, `pre-commit`) and regenerated `uv.lock`.
- Reformatted the codebase and `usb-stubs/` with the current `ruff` (double-quote strings,
  uppercase hex literals, updated line-wrapping).

### Fixed
- `dfuse_mem.py`/`dfu.py`: `MemSegment`/`DfuIf.next` self-referencing type hints were written as
  `"ClassName" | None` — a string literal `|`'d with `None`, which is invalid at runtime and broke
  both `ty` and every test importing `pydfuutil.dfu` under Python 3.14's dataclass annotation
  evaluation. Fixed by quoting the whole union (`"ClassName | None"`).

## [0.11.0] - 2026-07-11

No changes since [0.11.0b2], stable release

## [0.11.0b2] - 2026-07-10
### Added
- CLI long-option aliases matching the C reference: `--configuration`, `--interface`,
  `--altsetting` (alongside the existing `--cfg`, `--intf`, `--alt`).
- Full `<vid>:<pid>[,<vid_dfu>:<pid_dfu>]` dual-spec and `*`/`-` wildcard support for `-d`/`--device`.
- Static type checking with [ty](https://github.com/astral-sh/ty), wired into `pre-commit` and a dedicated `ty.yml` CI workflow.
- `usb-stubs/` PEP 561 stub package for `pyusb`, filling in previously-missing submodules (`usb.legacy`, `usb._lookup`, `usb.backend`, `usb._objfinalizer`, etc.) so the codebase type-checks cleanly end to end.
- `pre-commit` configuration (`uv sync`, `ty check`, `ruff check --fix`, `ruff format`, `pytest`).
- [docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md](docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md) — the itemized
  upstream-parity audit (moved from the former top-level `BACKLOG.md`, now with every item marked
  resolved or explicitly documented as an intentional, reviewed difference from upstream).

### Changed
- Renamed CI workflow `python-package.yml` to `pytest.yml`.
- Bumped CI/build tooling and dependencies (`actions/checkout` 6→7, `ruff`, `dependabot` config).
- `pydfuutil-suffix`/`pydfuutil-prefix` now parse the target file with `pathlib.Path` instead of `argparse.FileType('r+b')`.
- Removed the unused, unreferenced `_old/__main__.py` legacy module (~1000 lines of dead code from an earlier implementation).

### Fixed
- A full function-by-function audit against the upstream C `dfu-util` (master) turned up and
  fixed ~40 behavioral divergences introduced during the port — logic/semantics bugs invisible to
  `ty`/`ruff` that only a behavioral comparison against the reference implementation catches. Full
  itemized list, C references, and verification notes:
  [docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md](docs/SYNC_WITH_C_UPSTREAM_BACKLOG.md). Highlights:
  - **CLI entry point (`__main__.py`)**: `-D`/`--download` was completely non-functional (a dead
    `elif` branch on an already-handled condition meant it could never fire); `-d`/`--device`
    vendor:product filtering was parsed but never applied to device matching (now supports the
    full `<vid>:<pid>[,<vid_dfu>:<pid_dfu>]` syntax plus `*`/`-` wildcards, matching the C
    reference's `parse_vendprod`/`parse_match_value`); an inverted runtime-vs-DFU-mode branch
    condition swapped the "claim a runtime device" and "already in DFU mode" code paths on every
    probe; DfuSe downloads almost never routed to the DfuSe path because a required `or` had been
    written as `and`; a swapped `IFF.DFU`/`IFF.ALT` flag check, an inverted pipe-error fallback,
    a dropped `dfu_root.detach()` call before `-R`/`--reset`, non-`O_EXCL` upload-file writes,
    and a swallowed process exit code were also fixed.
  - **Core protocol (`dfu.py`, `portable.py`)**: `milli_sleep()` truncated every sub-second poll
    delay to a no-op busy loop; the DFU control-transfer `TIMEOUT` defaulted to `-1` (wrapping to
    an effectively infinite libusb timeout) since `dfu.init()` was never called anywhere in the
    CLI; `StatusRetVal.from_bytes()` validated `bState` against the wrong response byte;
    `QUIRK_POLLTIMEOUT` is now applied centrally inside `DfuIf.get_status()` (matching where the C
    reference applies it) instead of being re-implemented ad hoc, and inconsistently, at
    individual call sites.
  - **Plain DFU download/upload (`dfu_load.py`)**: `do_download()` was non-functional end to end
    (it tried to read firmware from a file handle that is only ever opened in write-only mode for
    the upload path); no DFU transaction counter was tracked across download chunks; uploads with
    no explicit `-Z`/`--upload-size` were truncated to a single transfer chunk instead of running
    until the device signals completion; added the missing `DFU_MANIFEST_WAIT_RESET` handling
    (explicit USB reset for devices with `ManifestationTolerant=0`).
  - **DfuSe protocol (`dfuse.py`)**: most download paths were non-functional end to end — a stale
    module-level memory-layout reference instead of the per-interface one, a call site missing a
    required parameter, an inverted/wrong polling-loop exit condition risking flash corruption, an
    unbounded data slice overrunning the intended chunk boundary, a mass-erase request that sent
    the wrong DfuSe command byte, and inverted `will-reset` handling. `parse_options()` didn't
    recognize the documented hyphenated option syntax (`mass-erase`, `will-reset`) nor `fast` at
    all, and rejected a legitimate address/length of `0` as invalid. A `LIBUSB_ERROR_PIPE`
    stall-recovery path discarded the last known poll timeout, causing premature "device stuck"
    errors on flaky STM32L4-style bootloaders. `do_leave()` didn't tolerate a device disappearing
    during its own quirk-tolerant leave request, and its non-quirk fallback call was missing a
    required argument, raising `TypeError` on every leave for a device without that quirk. A
    `.dfu` file loaded from disk was immutable `bytes`, but the DfuSe binary parser mutates its
    input buffer in place — breaking every real on-disk DfuSe (`.dfu`) download.
  - **File format (`dfu_file.py`)**: TI Stellaris (LMDFU) vs. NXP LPC prefix-type detection was
    swapped, so `dfu-suffix -c`/`dfu-prefix -c` misidentified or failed to recognize real prefixed
    files; the suffix CRC was computed for the mismatch check but never stored, so those same
    commands always displayed `CRC: 0x00000000` for a valid file.
  - **`suffix.py`/`prefix.py`**: an explicit VID/PID/DID of `0` was silently replaced with the
    wildcard `0xFFFF`; `-s/--stellaris-address` didn't imply the LMDFU prefix type as documented
    in `--help`; `prefix.py`'s address parsing didn't auto-detect the numeric base the way the C
    reference's `strtoul(..., 0)` does, so a plain decimal address was silently misread as hex.
  - **`quirks.py`**: `VENDOR.FIC` duplicated `VENDOR.OPENMOKO`'s numeric value instead of its own,
    so genuine FIC-vendor (Openmoko GTA02) devices never received the `POLLTIMEOUT` quirk.
  - **`dfu.py::IFF`**: flag values had been copied from a revision of the C `dfu.h` header that
    predates a 2013 upstream refactor of the USB enumeration logic; six flags that upstream itself
    removed over a decade ago were dead code here too, and `ALT` was left at that old header's
    `0x1000` instead of the value (`0x0002`) upstream reintroduced afterward. Cleaned up to match
    current upstream exactly.
  - `dfu.py::_get_state()` had no length guard before indexing a (possibly truncated/empty) pyusb
    response buffer, unlike the C reference's explicit `result < 1` check.
- `usb_dfu.py` imported `Union` from `ctypes` instead of `typing`, which broke `FuncDescriptor` — and by extension the whole `pydfuutil.dfu` import chain — at import time.
- `dfu.py`: `_get_state()` derived the DFU state from a boolean comparison instead of the actual status byte, so it almost never reported the correct device state.
- `dfu_util.py` (`_found_dfu`/`probe_configuration`) interface/alt-setting/vendor/product matching, re-verified against the upstream C source: a wrongly-gated `-a`/`--alt` filter, a copy-pasted `PrefixReq`/`SuffixReq` mixup, a `quirks and QUIRK.X` (logical instead of bitwise `&`) bug, a missing `-c`/`--cfg` filter, an interface-loop comparison against the wrong attribute, and `probe_configuration()` stopping after the first matching USB configuration instead of scanning all of them.
- `dfuse.py`: `upload()`/`do_upload()` mismatched their own return type (treated a raw USB read result as a status code), never incremented the DFU transaction counter across retries, and confused a CRC checksum with a byte count in the transfer bookkeeping.
- Assorted `Optional`/type-narrowing correctness fixes surfaced by the new `ty` type checker across `dfu.py`, `dfu_file.py`, `dfu_load.py`, `dfuse.py`, `dfuse_mem.py`, `dfu_util.py`, `exceptions.py`, `lsusb.py`, `prefix.py`, `progress.py`, `quirks.py`, and `usb_dfu.py`.
- `ruff` lint errors across the codebase.

## [0.11.0b1] - 2025-03-24
### Changed
- Bumped and updated project dependencies (`pyproject.toml`).
- Minor fixes to `dfu_load.py` (#18).
- CI workflow maintenance (`python-package.yml`, `python-publish.yml`, `python-publish-test.yml`).

## [0.11.0b0] - 2024-05-14
### Added
- `dfu_util.py`: extracted, upstream-matching device probing/enumeration logic
  (`probe_devices`/`probe_configuration`/`_found_dfu`), replacing the ad hoc enumeration
  previously spread across `__main__.py`.
- `pydfuutil-lsusb` — a minimal `lsusb`-alike CLI for listing attached USB devices.
- `logger.py` — centralized logging setup used across the package.

### Changed
- Brought `__main__.py`, `dfu.py`, `dfu_file.py`, `dfu_load.py`, `dfuse.py`, `suffix.py`,
  `prefix.py`, and `quirks.py` up to parity with upstream `dfu-util` 0.11 (previously tracking an
  older/ad hoc API shape).
- Reworked `exceptions.py` error handling to more closely mirror the C reference's `errx`-style
  exit-code semantics.
- Removed the `construct` dependency; DfuSe/`usb_dfu` binary parsing is now done with plain
  `struct`.
- USB errors are now handled via `usb.core.USBError` instead of ad hoc return-code checks.

### Removed
- `lmdfu.py` — superseded by the upstream-parity `prefix.py`/`suffix.py` implementation.

## [0.0.5] - 2024-05-06
## [0.0.4] - 2024-05-06
## [0.0.3] - 2024-05-06
### Fixed
- Entry-point (`console_scripts`) fixes following the `dfu-util` 0.11 API migration started in
  0.0.2b3/0.0.2 (`#11`, `#12`); iterative fixes to the `pydfuutil-suffix`/CLI entry points across
  these four back-to-back releases.

## [0.0.2] - 2024-05-06
### Changed
- Began migrating the CLI/API surface toward parity with upstream `dfu-util` 0.11 (`#12`),
  continued in `0.11.0b0`.

## [0.0.2b3] - 2024-05-02
### Changed
- Removed the `construct` dependency from `dfuse.py` and `usb_dfu.py` in favor of plain `struct`
  parsing.
- Added a pluggable progress-bar backend (`progress.py`) and a `test_dfuse.py` test module.

## [0.0.2b2] - 2024-04-30
### Added
- Initial test suite scaffolding.
- Reimplemented `dfuse_mem.py` memory-layout parsing.

### Changed
- General refactoring; `dfuse.py` temporarily disabled pending the `dfuse_mem.py` rework.

## [0.0.2b1] - 2024-04-29
### Added
- `console_scripts` entry points for `pydfuutil`/`pydfuutil-suffix`/`pydfuutil-prefix` (`#8`).

## [0.0.2b0] - 2024-03-26
### Added
- Initial `dfuse.py` (DfuSe / ST extensions) implementation (`#6`).

### Changed
- Simplified package namespaces and general refactoring (`#7`).

## [0.0.1b5] - 2024-03-01
### Fixed
- Logger initialization fix.

## [0.0.1b4] - 2024-01-15
### Added
- Initial `lmdfu.py` (TI Stellaris LMDFU prefix) and `dfuse_mem.py` implementations.

## [0.0.1b3] - 2023-11-13
### Added
- Initial `dfu_load.py` implementation (`dfuload_do_upload` and friends).

## [0.0.1b2] - 2023-11-11
### Changed
- Housekeeping release; no functional changes beyond `0.0.1b1.post1`.

## [0.0.1b1.post1] - 2023-10-18
### Changed
- Migrated packaging to `pyproject.toml`.
- Added initial GitHub Actions workflows (`pylint`, PyPI publish/publish-test).

## [0.0.1b1] - 2023-06-15
### Added
- First public beta: initial pure-Python `dfu.py` core (GET_STATUS/GETSTATE/DNLOAD/UPLOAD control
  transfers), `dfu_load.py` upload/download routines with parallel-read support, USB device
  reconnection by port number, and PyPI packaging.

[Unreleased]: https://github.com/o-murphy/pydfuutil/compare/v0.11.2...HEAD
[0.11.2]: https://github.com/o-murphy/pydfuutil/compare/v0.11.1...v0.11.2
[0.11.1]: https://github.com/o-murphy/pydfuutil/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/o-murphy/pydfuutil/compare/v0.11.0b2...v0.11.0
[0.11.0b2]: https://github.com/o-murphy/pydfuutil/compare/v0.11.0b1...v0.11.0b2
[0.11.0b1]: https://github.com/o-murphy/pydfuutil/compare/v0.11.0b0...v0.11.0b1
[0.11.0b0]: https://github.com/o-murphy/pydfuutil/compare/v0.0.5...v0.11.0b0
[0.0.5]: https://github.com/o-murphy/pydfuutil/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/o-murphy/pydfuutil/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/o-murphy/pydfuutil/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/o-murphy/pydfuutil/compare/v0.0.2b3...v0.0.2
[0.0.2b3]: https://github.com/o-murphy/pydfuutil/compare/v0.0.2b2...v0.0.2b3
[0.0.2b2]: https://github.com/o-murphy/pydfuutil/compare/v0.0.2b1...v0.0.2b2
[0.0.2b1]: https://github.com/o-murphy/pydfuutil/compare/v0.0.2b0...v0.0.2b1
[0.0.2b0]: https://github.com/o-murphy/pydfuutil/compare/v0.0.1b5...v0.0.2b0
[0.0.1b5]: https://github.com/o-murphy/pydfuutil/compare/v0.0.1b4...v0.0.1b5
[0.0.1b4]: https://github.com/o-murphy/pydfuutil/compare/v0.0.1b3...v0.0.1b4
[0.0.1b3]: https://github.com/o-murphy/pydfuutil/compare/v0.0.1b2...v0.0.1b3
[0.0.1b2]: https://github.com/o-murphy/pydfuutil/compare/v0.0.1b1.post1...v0.0.1b2
[0.0.1b1.post1]: https://github.com/o-murphy/pydfuutil/compare/v0.0.1b1...v0.0.1b1.post1
[0.0.1b1]: https://github.com/o-murphy/pydfuutil/releases/tag/v0.0.1b1
