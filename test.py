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

    def test_a_real_example(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[34m[OOC]\x1b[0m\x1b[0m Someone says, "test"\x1b[0m\x1b[0m\r\n'),
                [{'fg': 4}, '[OOC]', {}, ' Someone says, "test"\r\n'])

    def test_a_hard_real_example(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[31mCo\x1b[0m\x1b[34mlo\x1b[0m\x1b[32mr \x1b[0m\x1b[36mTe\x1b[0m\x1b[33mst\x1b[0m\x1b[47m\x1b[30m!\x1b[0m\x1b[0m\r\n'),
                [{'fg': 1}, "Co", {'fg': 4}, "lo", {'fg': 2}, "r ", {'fg': 6}, "Te", {'fg': 3}, "st", {'bg': 7, 'fg': 0}, "!", {}, "\r\n"])

if __name__ == '__main__':
    unittest.main()
