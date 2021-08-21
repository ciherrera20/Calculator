import re
import numpy as np

class Token():
    WORD = 'WORD'
    NUMBER = 'NUMBER'
    OPERATOR = 'OPERATOR'
    STRING = 'STRING'

    def __init__(self, atype, value):
        self.type = atype
        if atype == Token.NUMBER:
            self.value = np.float(value)
        else:
            self.value = value
    
    def __repr__(self):
        if self.type == Token.NUMBER:
            return '{}: {}'.format(self.type, str(self.value))
        else:
            return '{}: \'{}\''.format(self.type, str(self.value))

    def is_unary_operator(token):
        return token.type == Token.OPERATOR and token.value in ['+', '-', '!', 'not']
    
    def is_number(token):
        return token.type == Token.NUMBER

    def is_word(token):
        return token.type == Token.WORD

    def is_value(*values):
        return lambda token: token.value in values

def apply_pattern(tokens, pattern, callback):
    new_tokens = []
    for string in tokens:
        if type(string) == str:
            previous = 0
            for match in pattern.finditer(string):
                span = match.span()
                prefix = string[previous:span[0]]
                if prefix != '':
                    new_tokens.append(prefix)
                previous = span[1]
                new_tokens.append(callback(match[0]))
            suffix = string[previous:]
            if suffix != '':
                new_tokens.append(suffix)
        else:
            new_tokens.append(string)
    return new_tokens

def tokenize(string):
    number_pattern = re.compile(r'(?<!\w)(?:\d+\.\d+|\.\d+|\d+\.|\d+|\bInf\b|\bNaN\b)(?=\s|\b|\w)')
    tokens = apply_pattern([string], number_pattern, lambda value: Token(Token.NUMBER, value))

    operator_pattern = re.compile(r'(?:\band\b|\bor\b|\bneq\b|\beq\b|\bnot\b|[!><=]=|[\^*\/%+\-><!=])')
    tokens = apply_pattern(tokens, operator_pattern, lambda value: Token(Token.OPERATOR, value))

    word_pattern = re.compile(r'\b[a-zA-Z_]\w*\b')
    tokens = apply_pattern(tokens, word_pattern, lambda value: Token(Token.WORD, value))

    whitespace_pattern = re.compile(r'\s*')
    tokens = apply_pattern(tokens, whitespace_pattern, lambda value: '')

    char_pattern = re.compile(r'.')
    tokens = apply_pattern(tokens, char_pattern, lambda value: Token(Token.STRING, value))

    return list(filter(lambda value: value != '', tokens))