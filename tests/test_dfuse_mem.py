import unittest
from pydfuutil.dfuse_mem import MemSegment, add_segment, find_segment


# @unittest.skip("Not implemented")
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

    def test_find(self):
        mem_seq = MemSegment.from_bytes(bytes([1, 2, 0, 0, 10, 20, 0, 0, 100, 200, 0, 0]))
        self.assertEqual(mem_seq.find(10),
                         mem_seq.from_bytes(bytes([10, 20, 0, 0, 100, 200, 0, 0])))
        self.assertEqual(mem_seq.find(150),
                         mem_seq.from_bytes(bytes([100, 200, 0, 0])))

    def test_free(self):
        mem_seq = MemSegment.from_bytes(bytes(10))
        del mem_seq
        try:
            print(mem_seq)
        except UnboundLocalError as exc:
            self.assertTrue(exc)


    def test_add_segment_empty_list(self):
        # Test adding a segment to an empty list
        seqment_sequence = None
        segment = MemSegment(0, 10, 4, 'data')
        seqment_sequence = add_segment(seqment_sequence, segment)
        self.assertNotEqual(seqment_sequence, None)
        self.assertEqual(seqment_sequence.end, 10)
        self.assertEqual(seqment_sequence.next, None)

    def test_add_segment_nonempty_list(self):
        # Test adding a segment to a non-empty list
        seqment_sequence = MemSegment(0, 10, 4, 'data')
        segment = MemSegment(12, 20, 4, 'code')
        seqment_sequence = add_segment(seqment_sequence, segment)

        self.assertNotEqual(seqment_sequence, None)
        self.assertNotEqual(seqment_sequence.next, None)
        self.assertEqual(seqment_sequence.next.start, 12)
        self.assertEqual(seqment_sequence.next.end, 20)

    def test_add_segment_with_existing_next(self):
        # Test adding a segment when the last element in the list already has a next element
        seqment_sequence = MemSegment(0, 10, 4, 'data')
        seqment_sequence.next = MemSegment(22, 30, 4, 'heap')
        segment = MemSegment(12, 20, 4, 'code')
        seqment_sequence = add_segment(seqment_sequence, segment)
        self.assertNotEqual(seqment_sequence.next, None)
        self.assertNotEqual(seqment_sequence.next.next, None)
        self.assertEqual(seqment_sequence.next.end, 30)
        self.assertEqual(seqment_sequence.next.next.end, 20)

    def test_find_segment(self):
        seqment_sequence = MemSegment(0, 10, 4, 'data')
        seqment_sequence.next = MemSegment(22, 30, 4, 'heap')
        segment = MemSegment(12, 20, 4, 'code')
        seqment_sequence = add_segment(seqment_sequence, segment)
        found = find_segment(seqment_sequence, segment)
        self.assertEqual(found, segment)


if __name__ == '__main__':
    unittest.main()