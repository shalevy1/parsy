# -*- code: utf8 -*-
import unittest

from parsy import test_char as parsy_test_char  # to stop pytest thinking this function is a test
from parsy import (
    ParseError, alt, any_char, char_from, decimal_digit, digit, generate, letter, line_info_at, regex, seq, string,
    string_from, whitespace
)


class TestParser(unittest.TestCase):

    def test_string(self):
        parser = string('x')
        self.assertEqual(parser.parse('x'), 'x')

        self.assertRaises(ParseError, parser.parse, 'y')

    def test_regex(self):
        parser = regex(r'[0-9]')

        self.assertEqual(parser.parse('1'), '1')
        self.assertEqual(parser.parse('4'), '4')

        self.assertRaises(ParseError, parser.parse, 'x')

    def test_then(self):
        xy_parser = string('x') >> string('y')
        self.assertEqual(xy_parser.parse('xy'), 'y')

        self.assertRaises(ParseError, xy_parser.parse, 'y')
        self.assertRaises(ParseError, xy_parser.parse, 'z')

    def test_bind(self):
        piped = None

        def binder(x):
            nonlocal piped
            piped = x
            return string('y')

        parser = string('x').bind(binder)

        self.assertEqual(parser.parse('xy'), 'y')
        self.assertEqual(piped, 'x')

        self.assertRaises(ParseError, parser.parse, 'x')

    def test_map(self):
        parser = digit.map(int)
        self.assertEqual(parser.parse('7'),
                         7)

    def test_combine(self):
        parser = (seq(digit, letter)
                  .combine(lambda d, l: (d, l)))
        self.assertEqual(parser.parse('1A'),
                         ('1', 'A'))

    def test_generate(self):
        x = y = None

        @generate
        def xy():
            nonlocal x
            nonlocal y
            x = yield string('x')
            y = yield string('y')
            return 3

        self.assertEqual(xy.parse('xy'), 3)
        self.assertEqual(x, 'x')
        self.assertEqual(y, 'y')

    def test_generate_return_parser(self):
        @generate
        def example():
            yield string('x')
            return string('y')
        self.assertEqual(example.parse("xy"), "y")

    def test_mark(self):
        parser = (letter.many().mark() << string("\n")).many()

        lines = parser.parse("asdf\nqwer\n")

        self.assertEqual(len(lines), 2)

        (start, letters, end) = lines[0]
        self.assertEqual(start, (0, 0))
        self.assertEqual(letters, ['a', 's', 'd', 'f'])
        self.assertEqual(end, (0, 4))

        (start, letters, end) = lines[1]
        self.assertEqual(start, (1, 0))
        self.assertEqual(letters, ['q', 'w', 'e', 'r'])
        self.assertEqual(end, (1, 4))

    def test_generate_desc(self):
        @generate('a thing')
        def thing():
            yield string('t')

        with self.assertRaises(ParseError) as err:
            thing.parse('x')

        ex = err.exception

        self.assertEqual(ex.expected, frozenset(['a thing']))
        self.assertEqual(ex.stream, 'x')
        self.assertEqual(ex.index, 0)

    def test_generate_default_desc(self):
        # We shouldn't give a default desc, the messages from the internal
        # parsers should bubble up.
        @generate
        def thing():
            yield string('a')
            yield string('b')

        with self.assertRaises(ParseError) as err:
            thing.parse('ax')

        ex = err.exception

        self.assertEqual(ex.expected, frozenset(['b']))
        self.assertEqual(ex.stream, 'ax')
        self.assertEqual(ex.index, 1)

        self.assertIn("expected 'b' at 0:1",
                      str(ex))

    def test_multiple_failures(self):
        abc = string('a') | string('b') | string('c')

        with self.assertRaises(ParseError) as err:
            abc.parse('d')

        ex = err.exception
        self.assertEqual(ex.expected, frozenset(['a', 'b', 'c']))
        self.assertEqual(str(ex), "expected one of 'a', 'b', 'c' at 0:0")

    def test_generate_backtracking(self):
        @generate
        def xy():
            yield string('x')
            yield string('y')
            assert False

        parser = xy | string('z')
        # should not finish executing xy()
        self.assertEqual(parser.parse('z'), 'z')

    def test_or(self):
        x_or_y = string('x') | string('y')

        self.assertEqual(x_or_y.parse('x'), 'x')
        self.assertEqual(x_or_y.parse('y'), 'y')

    def test_or_with_then(self):
        parser = (string('\\') >> string('y')) | string('z')
        self.assertEqual(parser.parse('\\y'), 'y')
        self.assertEqual(parser.parse('z'), 'z')

        self.assertRaises(ParseError, parser.parse, '\\z')

    def test_many(self):
        letters = letter.many()
        self.assertEqual(letters.parse('x'), ['x'])
        self.assertEqual(letters.parse('xyz'), ['x', 'y', 'z'])
        self.assertEqual(letters.parse(''), [])

        self.assertRaises(ParseError, letters.parse, '1')

    def test_many_with_then(self):
        parser = string('x').many() >> string('y')
        self.assertEqual(parser.parse('y'), 'y')
        self.assertEqual(parser.parse('xy'), 'y')
        self.assertEqual(parser.parse('xxxxxy'), 'y')

    def test_times_zero(self):
        zero_letters = letter.times(0)
        self.assertEqual(zero_letters.parse(''), [])

        self.assertRaises(ParseError, zero_letters.parse, 'x')

    def test_times(self):
        three_letters = letter.times(3)
        self.assertEqual(three_letters.parse('xyz'), ['x', 'y', 'z'])

        self.assertRaises(ParseError, three_letters.parse, 'xy')
        self.assertRaises(ParseError, three_letters.parse, 'xyzw')

    def test_times_with_then(self):
        then_digit = letter.times(3) >> digit
        self.assertEqual(then_digit.parse('xyz1'), '1')

        self.assertRaises(ParseError, then_digit.parse, 'xy1')
        self.assertRaises(ParseError, then_digit.parse, 'xyz')
        self.assertRaises(ParseError, then_digit.parse, 'xyzw')

    def test_times_with_min_and_max(self):
        some_letters = letter.times(2, 4)

        self.assertEqual(some_letters.parse('xy'), ['x', 'y'])
        self.assertEqual(some_letters.parse('xyz'), ['x', 'y', 'z'])
        self.assertEqual(some_letters.parse('xyzw'), ['x', 'y', 'z', 'w'])

        self.assertRaises(ParseError, some_letters.parse, 'x')
        self.assertRaises(ParseError, some_letters.parse, 'xyzwv')

    def test_times_with_min_and_max_and_then(self):
        then_digit = letter.times(2, 4) >> digit

        self.assertEqual(then_digit.parse('xy1'), '1')
        self.assertEqual(then_digit.parse('xyz1'), '1')
        self.assertEqual(then_digit.parse('xyzw1'), '1')

        self.assertRaises(ParseError, then_digit.parse, 'xy')
        self.assertRaises(ParseError, then_digit.parse, 'xyzw')
        self.assertRaises(ParseError, then_digit.parse, 'xyzwv1')
        self.assertRaises(ParseError, then_digit.parse, 'x1')

    def test_at_most(self):
        ab = string("ab")
        self.assertEqual(ab.at_most(2).parse(""),
                         [])
        self.assertEqual(ab.at_most(2).parse("ab"),
                         ["ab"])
        self.assertEqual(ab.at_most(2).parse("abab"),
                         ["ab", "ab"])
        self.assertRaises(ParseError,
                          ab.at_most(2).parse, "ababab")

    def test_sep_by(self):
        digit_list = digit.map(int).sep_by(string(','))

        self.assertEqual(digit_list.parse('1,2,3,4'), [1, 2, 3, 4])
        self.assertEqual(digit_list.parse('9,0,4,7'), [9, 0, 4, 7])
        self.assertEqual(digit_list.parse('3,7'), [3, 7])
        self.assertEqual(digit_list.parse('8'), [8])
        self.assertEqual(digit_list.parse(''), [])

        self.assertRaises(ParseError, digit_list.parse, '8,')
        self.assertRaises(ParseError, digit_list.parse, ',9')
        self.assertRaises(ParseError, digit_list.parse, '82')
        self.assertRaises(ParseError, digit_list.parse, '7.6')

    def test_sep_by_with_min_and_max(self):
        digit_list = digit.map(int).sep_by(string(','), min=2, max=4)

        self.assertEqual(digit_list.parse('1,2,3,4'), [1, 2, 3, 4])
        self.assertEqual(digit_list.parse('9,0,4,7'), [9, 0, 4, 7])
        self.assertEqual(digit_list.parse('3,7'), [3, 7])

        self.assertRaises(ParseError, digit_list.parse, '8')
        self.assertRaises(ParseError, digit_list.parse, '')
        self.assertRaises(ParseError, digit_list.parse, '8,')
        self.assertRaises(ParseError, digit_list.parse, ',9')
        self.assertRaises(ParseError, digit_list.parse, '82')
        self.assertRaises(ParseError, digit_list.parse, '7.6')
        self.assertEqual(digit.sep_by(string(","), max=0).parse(''),
                         [])

    def test_add(self):
        self.assertEqual((letter + digit).parse("a1"),
                         "a1")

    def test_multiply(self):
        self.assertEqual((letter * 3).parse("abc"),
                         ['a', 'b', 'c'])

    def test_multiply_range(self):
        self.assertEqual((letter * range(1, 2)).parse("a"),
                         ["a"])
        self.assertRaises(ParseError, (letter * range(1, 2)).parse, "aa")

    # Primitives
    def test_alt(self):
        self.assertRaises(ParseError, alt().parse, '')
        self.assertEqual(alt(letter, digit).parse('a'),
                         'a')
        self.assertEqual(alt(letter, digit).parse('1'),
                         '1')
        self.assertRaises(ParseError, alt(letter, digit).parse, '.')

    def test_seq(self):
        self.assertEqual(seq().parse(''),
                         [])
        self.assertEqual(seq(letter).parse('a'),
                         ['a'])
        self.assertEqual(seq(letter, digit).parse('a1'),
                         ['a', '1'])
        self.assertRaises(ParseError, seq(letter, digit).parse, '1a')

    def test_test_char(self):
        ascii = parsy_test_char(lambda c: ord(c) < 128,
                                "ascii character")
        self.assertEqual(ascii.parse("a"), "a")
        with self.assertRaises(ParseError) as err:
            ascii.parse('☺')
        ex = err.exception
        self.assertEqual(str(ex), """expected 'ascii character' at 0:0""")

        with self.assertRaises(ParseError) as err:
            ascii.parse('')
        ex = err.exception
        self.assertEqual(str(ex), """expected 'ascii character' at 0:0""")

    def test_char_from(self):
        ab = char_from("ab")
        self.assertEqual(ab.parse("a"), "a")
        self.assertEqual(ab.parse("b"), "b")

        with self.assertRaises(ParseError) as err:
            ab.parse('x')

        ex = err.exception
        self.assertEqual(str(ex), """expected '[ab]' at 0:0""")

    def test_string_from(self):
        titles = string_from("Mr", "Mr.", "Mrs", "Mrs.")
        self.assertEqual(titles.parse("Mr"), "Mr")
        self.assertEqual(titles.parse("Mr."), "Mr.")
        self.assertEqual((titles + string(" Hyde")).parse("Mr. Hyde"),
                         "Mr. Hyde")
        with self.assertRaises(ParseError) as err:
            titles.parse('foo')

        ex = err.exception
        self.assertEqual(str(ex), """expected one of 'Mr', 'Mr.', 'Mrs', 'Mrs.' at 0:0""")

    def test_any_char(self):
        self.assertEqual(any_char.parse("x"), "x")
        self.assertEqual(any_char.parse("\n"), "\n")
        self.assertRaises(ParseError, any_char.parse, "")

    def test_whitespace(self):
        self.assertEqual(whitespace.parse("\n"), "\n")
        self.assertEqual(whitespace.parse(" "), " ")
        self.assertRaises(ParseError, whitespace.parse, "x")

    def test_letter(self):
        self.assertEqual(letter.parse("a"), "a")
        self.assertRaises(ParseError, letter.parse, "1")

    def test_digit(self):
        self.assertEqual(digit.parse("¹"), "¹")
        self.assertEqual(digit.parse("2"), "2")
        self.assertRaises(ParseError, digit.parse, "x")

    def test_decimal_digit(self):
        self.assertEqual(decimal_digit.at_least(1).map(''.join).parse("9876543210"),
                         "9876543210")
        self.assertRaises(ParseError, decimal_digit.parse, "¹")


class TestUtils(unittest.TestCase):
    def test_line_info_at(self):
        text = "abc\ndef"
        self.assertEqual(line_info_at(text, 0),
                         (0, 0))
        self.assertEqual(line_info_at(text, 2),
                         (0, 2))
        self.assertEqual(line_info_at(text, 3),
                         (0, 3))
        self.assertEqual(line_info_at(text, 4),
                         (1, 0))
        self.assertEqual(line_info_at(text, 7),
                         (1, 3))
        self.assertRaises(ValueError, lambda: line_info_at(text, 8))


if __name__ == '__main__':
    unittest.main()
