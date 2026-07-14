"""
Regression + performance test for the zlib-backed CRC replacement in
pydfuutil.dfu_file.

Guards against two failure modes:
1. Correctness regression: `_crc32_buf` (zlib-backed) must produce a
   bit-identical result to the original `crc32_byte` byte-at-a-time loop,
   for arbitrary starting accumulator values (not just the 0xFFFFFFFF
   suffix-verification case) — this covers the write_crc() chaining path
   used during upload as well as the one-shot suffix-check path.
2. Performance regression: if someone reverts to a Python-level loop in
   the hot path, this test will start failing the speedup assertion.
"""

import random
import time
import unittest

from pydfuutil.dfu_file import crc32_byte, _crc32_buf


def _reference_loop(accum: int, buf: bytes) -> int:
    """The original algorithm, kept here (not imported) so this test does
    not silently pass if someone deletes crc32_byte's real loop and only
    keeps a stub."""
    crc = accum
    for byte in buf:
        crc = crc32_byte(crc, byte)
    return crc


class TestCrc32BufCorrectness(unittest.TestCase):
    def setUp(self):
        random.seed(1234)

    def test_empty_buffer(self):
        self.assertEqual(_reference_loop(0xFFFFFFFF, b""), _crc32_buf(0xFFFFFFFF, b""))

    def test_various_sizes_default_init(self):
        for size in (1, 2, 3, 4, 15, 16, 17, 255, 256, 257, 4096, 65537):
            buf = bytes(random.randrange(256) for _ in range(size))
            expected = _reference_loop(0xFFFFFFFF, buf)
            actual = _crc32_buf(0xFFFFFFFF, buf)
            self.assertEqual(
                actual,
                expected,
                msg=f"mismatch at size={size}: expected=0x{expected:08X} actual=0x{actual:08X}",
            )

    def test_arbitrary_starting_accumulator(self):
        """write_crc() in dfu_load.py chains CRC across upload transfer
        chunks with whatever accumulator the caller passes in — this must
        stay correct even when that accumulator isn't the canonical
        0xFFFFFFFF init value."""
        for accum in (0, 1, 0xFFFFFFFF, 0xDEADBEEF, 0x12345678):
            buf = bytes(random.randrange(256) for _ in range(1000))
            expected = _reference_loop(accum, buf)
            actual = _crc32_buf(accum, buf)
            self.assertEqual(
                actual,
                expected,
                msg=f"mismatch at accum=0x{accum:08X}: expected=0x{expected:08X} actual=0x{actual:08X}",
            )

    def test_chunked_matches_one_shot(self):
        """Simulates do_upload()'s per-chunk write_crc() calls: processing
        data in pieces must give the same final register as processing it
        all at once, for both the old loop and the new implementation."""
        data = bytes(random.randrange(256) for _ in range(50_000))
        chunk_size = 517  # deliberately not a power of two / divisor of len(data)

        # one-shot
        one_shot_old = _reference_loop(0xFFFFFFFF, data)
        one_shot_new = _crc32_buf(0xFFFFFFFF, data)
        self.assertEqual(one_shot_old, one_shot_new)

        # chunked
        crc_old = 0xFFFFFFFF
        crc_new = 0xFFFFFFFF
        for i in range(0, len(data), chunk_size):
            piece = data[i : i + chunk_size]
            crc_old = _reference_loop(crc_old, piece)
            crc_new = _crc32_buf(crc_new, piece)

        self.assertEqual(crc_old, one_shot_old, "old loop: chunking changed the result")
        self.assertEqual(crc_new, one_shot_new, "new impl: chunking changed the result")
        self.assertEqual(
            crc_new, crc_old, "new impl diverges from old loop when chunked"
        )

    def test_structured_data(self):
        """Repetitive/structured bytes (closer to real firmware than pure
        random noise) still match."""
        data = (bytes(range(256)) * 200) + bytes(
            random.randrange(256) for _ in range(3333)
        )
        self.assertEqual(
            _reference_loop(0xFFFFFFFF, data),
            _crc32_buf(0xFFFFFFFF, data),
        )


class TestCrc32BufPerformance(unittest.TestCase):
    """Not a microbenchmark suite — just a floor to catch an accidental
    revert to a pure-Python loop in the hot path. Threshold is set well
    below the ~250-500x measured on a 1-16MB firmware image, so it won't
    be flaky on slow/loaded CI runners."""

    MIN_EXPECTED_SPEEDUP = 20

    def test_speedup_on_realistic_firmware_size(self):
        random.seed(7)
        buf = random.randbytes(
            1_000_000
        )  # 1 MB, typical firmware-image order of magnitude

        t0 = time.perf_counter()
        expected = _reference_loop(0xFFFFFFFF, buf)
        t1 = time.perf_counter()
        actual = _crc32_buf(0xFFFFFFFF, buf)
        t2 = time.perf_counter()

        self.assertEqual(actual, expected)

        old_time = t1 - t0
        new_time = t2 - t1
        speedup = old_time / new_time if new_time > 0 else float("inf")

        self.assertGreater(
            speedup,
            self.MIN_EXPECTED_SPEEDUP,
            msg=f"expected >{self.MIN_EXPECTED_SPEEDUP}x speedup, got {speedup:.1f}x "
            f"(old={old_time:.4f}s new={new_time:.6f}s) — "
            f"did the hot path regress to a pure-Python loop?",
        )


if __name__ == "__main__":
    unittest.main()
