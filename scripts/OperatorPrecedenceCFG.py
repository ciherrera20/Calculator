from enum import Enum
import numpy as np
import re

# Create regex strings
NUMBER = r'\d*\.\d+|\d+\.\d*|\d+|NaN|Inf'
OPERATOR = r'[+\-*\/^]'
TOKEN = NUMBER + '|' + OPERATOR + r'\(|\)|.'
NON_WHITESPACE = r'\S+'

# Compile the strings into regex patterns
NUMBER = re.compile(NUMBER)
OPERATOR = re.compile(OPERATOR)
TOKEN = re.compile(TOKEN)
NON_WHITESPACE = re.compile(NON_WHITESPACE)

class Token(Enum):
    NUMBER = 1
    PLUS = 2
    MINUS = 3
    MULT = 4
    DIV = 5
    EXP = 6
    OPEN_PAREN = 7
    CLOSE_PAREN = 8

    def to_token(string):
        if string == 'NaN':
            return ((Token.NUMBER), np.nan)
        elif string == 'Inf':
            return ((Token.NUMBER), np.inf)
        elif string == '+':
            return ((Token.PLUS), '+')
        elif string == '-':
            return ((Token.MINUS), '-')
        elif string == '*':
            return ((Token.MULT), '*')
        elif string == '/':
            return ((Token.DIV), '/')
        elif string == '^':
            return ((Token.EXP), '^')
        elif string == '(':
            return ((Token.OPEN_PAREN), '(')
        elif string == ')':
            return ((Token.CLOSE_PAREN), ')')
        else:
            try:
                return ((Token.NUMBER), np.float(string))
            except ValueError:
                raise ValueError('unrecognized token: {}'.format(string))

    def get_type(token):
        return token[0]


def tokenize(string):
    contig_strings = NON_WHITESPACE.findall(string)
    raw_tokens = []
    for contig_string in contig_strings:
        raw_tokens += TOKEN.findall(contig_string)
    return [Token.to_token(raw_token) for raw_token in raw_tokens]

def parser(tokens):
    pass

def generate_type_parser(token_type):
    def parse_type(tokens, pos):
        if len(tokens) <= pos:
            raise ValueError('Unexpected end of input. Expected a {} token at position {}'.format(token_type, pos))
        elif Token.get_type(tokens[pos]) != token_type:
            raise ValueError('Expected a {} token but got {}'.format(token_type, tokens[pos]))
        else:
            return ((tokens[pos], None, None), 1)
    return parse_type

def generate_alternating_parser(*parsers):
    def alternating_parser(tokens, pos):
        for parser in parsers:
            try:
                return parser(tokens, pos)
            except ValueError:
                pass
        raise ValueError('Alternating parser error at position {}'.format(pos))
    return alternating_parser

def generate_sequencing_parser(*parsers):
    def sequencing_parser(tokens, pos):
        overall_output = []
        overall_consumed = 0
        for parser in parsers:
            output, consumed = parser(tokens, pos + overall_consumed)
            overall_consumed += consumed
            overall_output.append(output)
        return(overall_output, overall_consumed)
    return sequencing_parser

def generate_map_parser(func, parser):
    def map_parser(tokens, pos):
        output, consumed = parser(tokens, pos)
        return (func(output), consumed)
    return map_parser

def binary_operator_group(output):
    if len(output) != 3:
        raise ValueError('Expected three output nodes, but recieved {}: {}'.format(len(output), output))

    exp_left, op, exp_right = output
    return (op[0], exp_left, exp_right)

def parenthesis_group(output):
    if len(output) != 3:
        raise ValueError('Expected three output nodes, but recieved {}: {}'.format(len(output), output))    

    open_paren, exp, close_paren = output
    return exp

# Create token parsers
parse_number_token = generate_type_parser(Token.NUMBER)
parse_plus_token = generate_type_parser(Token.PLUS)
parse_exp_token = generate_type_parser(Token.EXP)

# parse_expr = None
# parse_addsub = None
# parse_multdiv = None

# Define exponentiation
parse_expo = generate_alternating_parser(
    generate_map_parser(
        binary_operator_group,
        generate_sequencing_parser(
            parse_number_token,
            parse_exp_token,
            lambda *x: parse_expo(*x)
        )
    ),
    generate_map_parser(
        binary_operator_group,
        generate_sequencing_parser(
            parse_number_token,
            parse_exp_token,
            parse_number_token
        )
    )
)

# parse_expo = generate_map_parser(
#     binary_operator_group,
#     generate_sequencing_parser(
#         parse_number_token,
#         parse_exp_token,
#         parse_number_token
#     )
# )

parse_line = generate_alternating_parser(
    # parse_expr, 
    # parse_addsub, 
    # parse_multdiv, 
    parse_expo
)

# 1+2
# S -> A -> X+X -> N+X -> N+N

#           X -> N
# S -> A -> +
#           X -> N