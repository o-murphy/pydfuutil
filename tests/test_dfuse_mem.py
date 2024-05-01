import unittest
from pydfuutil.dfuse_mem import MemSegment, add_segment, parse_memory_layout


class TestDfuSeMem(unittest.TestCase):

    def test_parse_build(self):
        mem_seq = MemSegment.from_bytes(bytes(12))
        buf = bytes(mem_seq)
        self.assertEqual(buf, bytes(12))

    def test_append(self):
        mem_seq = MemSegment.from_bytes(bytes(12))
        seg = MemSegment.from_bytes(bytes(4))
        mem_seq.append(seg)
        buf = bytes(mem_seq)
        self.assertEqual(buf, bytes(16))
        self.assertEqual(len(mem_seq), 4)

    def test_iter(self):
        mem_seq = MemSegment.from_bytes(bytes(12))
        self.assertEqual(len(tuple(mem_seq)), len(mem_seq))

    def test_find(self):
        mem_seq = MemSegment.from_bytes(bytes([1, 2, 0, 0, 10, 20, 0, 0, 100, 200, 0, 0]))
        self.assertEqual(mem_seq.find(10),
                         mem_seq.from_bytes(bytes([10, 20, 0, 0, 100, 200, 0, 0])))
        self.assertEqual(mem_seq.find(150),
                         mem_seq.from_bytes(bytes([100, 200, 0, 0])))
        self.assertEqual(mem_seq.find(300), None)

    def test_free(self):
        mem_seq = MemSegment.from_bytes(bytes(10))
        del mem_seq
        self.assertNotIn('mem_seq', locals())

    def test_add_segment_empty_list(self):
        # Test adding a segment to an empty list
        seqment_sequence = None
        segment = MemSegment(0, 10, 4, 0)
        seqment_sequence = add_segment(seqment_sequence, segment)
        self.assertNotEqual(seqment_sequence, None)
        self.assertEqual(seqment_sequence.end, 10)
        self.assertEqual(seqment_sequence.next, None)

    def test_add_segment_nonempty_list(self):
        # Test adding a segment to a non-empty list
        seqment_sequence = MemSegment(0, 10, 4, 0)
        segment = MemSegment(12, 20, 4, 0)
        seqment_sequence = add_segment(seqment_sequence, segment)

        self.assertNotEqual(seqment_sequence, None)
        self.assertNotEqual(seqment_sequence.next, None)
        self.assertEqual(seqment_sequence.next.start, 12)
        self.assertEqual(seqment_sequence.next.end, 20)

    def test_add_segment_with_existing_next(self):
        # Test adding a segment when the last element in the list already has a next element
        seqment_sequence = MemSegment(0, 10, 4, 0)
        seqment_sequence.next = MemSegment(22, 30, 4, 0)
        segment = MemSegment(12, 20, 4, 0)
        seqment_sequence = add_segment(seqment_sequence, segment)
        self.assertNotEqual(seqment_sequence.next, None)
        self.assertNotEqual(seqment_sequence.next.next, None)
        self.assertEqual(seqment_sequence.next.end, 30)
        self.assertEqual(seqment_sequence.next.next.end, 20)

    def test_parse_memory_layout(self):
        with self.subTest("Test case 1: Valid input"):
            intf_desc = "@Internal Flash/0x08000000/04*016Kg,01*064Kg,01*128Kg"
            result = parse_memory_layout(intf_desc)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, MemSegment)
            self.assertEqual(len(result), 3)

        with self.subTest("Test case 2: Empty input"):
            result = parse_memory_layout("")
            self.assertIsNone(result)

        with self.subTest("Test case 3: Invalid input with missing name"):
            intf_desc = "/0x1000/1*1024B/04*016Kg"
            result = parse_memory_layout(intf_desc)
            self.assertIsNone(result)

        with self.subTest("Test case 4: Invalid input with missing address"):
            intf_desc = "@Internal Flash/1*1024B/"
            result = parse_memory_layout(intf_desc)
            self.assertIsNone(result)

        with self.subTest("Test case 5: Invalid input with missing segment details"):
            intf_desc = "@Internal Flash/0x08000000/"
            result = parse_memory_layout(intf_desc)
            self.assertIsNone(result)  # Should return None, as it's invalid


if __name__ == '__main__':
    unittest.main()