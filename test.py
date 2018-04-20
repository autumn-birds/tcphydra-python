import unittest

import ansi

class TestANSIProcessing(unittest.TestCase):
    def test_all_text(self):
        self.assertEqual(
                ansi.parse_ANSI("hello world"),
                ["hello world"])

    def test_set_fg(self):
        self.assertEqual(
                ansi.parse_ANSI("\x1B[33mHello world!"),
                [{'fg': 3}, "Hello world!"])

    def test_set_twice(self):
        self.assertEqual(
                ansi.parse_ANSI("\x1B[33mHello \x1B[45mworld!"),
                [{'fg': 3}, "Hello ", {'fg': 3, 'bg': 5}, "world!"])

    def test_set_reset(self):
        self.assertEqual(
                ansi.parse_ANSI("\x1B[33mHello \x1B[0;45mworld\x1Bc!"),
                [{'fg': 3}, "Hello ", {'bg': 5}, "world", {}, "!"])

if __name__ == '__main__':
    unittest.main()
