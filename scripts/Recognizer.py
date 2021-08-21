from functools import reduce

memo_table = {}
c_table = {}
def memoize(p):
    def memoized_p(string, j):
        # Check if the parser has already given a result for this position. If so return it.
        if (string, p, j) in memo_table:
            return memo_table[(string, p, j)]

        # Otherwise, apply the parser.
        # If this is the first time the parser sees this position, record it on c_table.
        if (string, p, j) not in c_table:
            c_table[(string, p, j)] = 1
        
        # Retrieve the recursion depth from c_table.
        c_pj = c_table[(string, p, j)]
        # print('Applying {} to {} with recursion depth {}'.format(p, j, c_pj))

        # If the recursion depth is greater than the string' remaining length + 1, curtail the recursion by returning the empty set.
        if c_pj > len(string) - j + 1:
            return set()

        # Otherwise, apply the parser and increment the depth of recursion.
        c_table[(string, p, j)] = c_pj + 1
        output = p(string, j)
        memo_table[(string, p, j)] = output
        return output
    return memoized_p

def term(t):
    def recognize_term(string, j):
        if j >= len(string):
            return set()
        elif string[j] == t:
            return {j + 1}
        else:
            return set()
    return recognize_term

def character_class(chs):
    return orelse(*[term(ch) for ch in chs])

def character_sequence(chs):
    return then(*[term(ch) for ch in chs])

def empty(string, j):
    return {j}

def orelse(*ps):
    def recognize_alternate_ps(string, j):
        return reduce(set.union, map(lambda p: p(string, j), ps), set())
    return recognize_alternate_ps

def then(*ps):
    def recognize_sequential_ps(string, j):
        result = {j}
        for p in ps:
            result = reduce(set.union, map(lambda r: p(string, r), result), set())
        return result
    return recognize_sequential_ps

def recognize(parser, string):
    return len(string) in parser(string, 0)

'''
Define a simple non-left recursive and highly ambiguous grammar:
sS -> 's' sS sS | empty

Terminals: 's'
Non-terminals: sS
'''
term_s = term('s')
ms = memoize(term_s)
msS = memoize(
    orelse(
        then(
            ms,
            lambda *x: msS(*x),
            lambda *x: msS(*x)
        ),
        empty
    )
)

'''
Define a simple left-recursive grammar:
d -> 'x' | 'y' | 'z'
A -> d '+' A | d '+' d
E -> A | empty

Terminals: 'x', 'y', 'z', '+'
Non-terminals: d, A, E
'''
term_x = term('x')
term_y = term('y')
term_z = term('z')
term_plus = term('+')
term_d = orelse(
    term('x'),
    term('y'),
    term('z')
)
term_A = orelse(
    then(
        term_d,
        term_plus,
        lambda *x: term_A(*x)
    ),
    then(
        term_d,
        term_plus,
        term_d
    )
)
term_S = orelse(
    term_A,
    empty
)

'''
Define a grammar for valid numbers
digit -> '0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9'
digit_plus -> d | d d_plus
number -> digit_plus '.' | '.' digit_plus | digit_plus '.' digit_plus | digit_plus | 'Inf' | 'NaN'
'''

term_decimal = term('.')
term_NaN = character_sequence('NaN')
term_Inf = character_sequence('Inf')
digit = character_class('0123456789')
digit_plus = orelse(
    digit,
    then(
        digit,
        lambda *x: digit_plus(*x)
    )
)
number = orelse(
    then(digit_plus, term_decimal),
    then(term_decimal, digit_plus),
    then(digit_plus, term_decimal, digit_plus),
    digit_plus,
    term_NaN,
    term_Inf
)

'''
Define a grammar for valid addition expressions
digit -> '0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9'
digit_plus -> d | d d_plus
number -> digit_plus '.' | '.' digit_plus | digit_plus '.' digit_plus | digit_plus | 'Inf' | 'NaN'
addition -> number '+' number | addition '+' number
'''
addition = memoize(orelse(
    then(number, term_plus, number),
    then(lambda *x: addition(*x), term_plus, number)
))