from Lexer import Token, tokenize
from Parsers import terminal_type, empty, orelse, then, memoize, label, keep

def eat(parser):
    def eaten_parser(tokens, pos):
        pos_set, tree_dict = parser(tokens, pos)
        new_tree_dict = {}
        for pos in pos_set:
            new_tree_dict[pos] = ()
        return (pos_set, new_tree_dict)
    return eaten_parser

def one_or_more(parser):
    repeated_parser = orelse(
        then(parser, lambda *x: repeated_parser(*x)),
        parser,
        keep=True
    )
    return repeated_parser

def zero_or_more(parser):
    repeated_parser = orelse(
        then(parser, lambda *x: repeated_parser(*x)),
        empty,
        keep=True
    )
    return repeated_parser

number = memoize(terminal_type(Token.is_number))
word = memoize(terminal_type(Token.is_word))
open_paren = memoize(eat(terminal_type(Token.is_value('('))))
close_paren = memoize(eat(terminal_type(Token.is_value(')'))))
period = memoize(eat(terminal_type(Token.is_value('.'))))
comma = memoize(eat(terminal_type(Token.is_value(','))))
equal_sign = memoize(eat(terminal_type(Token.is_value('='))))
semi_colon = memoize(eat(terminal_type(Token.is_value(';'))))

name = memoize(label(then(
    word, zero_or_more(then(period, word))
), label='name'))

unary_op = memoize(label(
    terminal_type(Token.is_unary_operator),
    label='operator'
))

binary_operand = memoize(label(orelse(
    # lambda *x: unary_operand(*x),
    # then(unary_op, lambda *x: binary_operand(*x)),
    then(zero_or_more(unary_op), lambda *x: unary_operand(*x)),
    keep=True
), label='operand', collapsed=True))

num_prec_ops = 7
prec_op_labels = ['operator'] * num_prec_ops
prec_exp_labels = ['infix'] * num_prec_ops

prec0_op = memoize(label(terminal_type(Token.is_value('^')), label=prec_op_labels[0]))
prec1_op = memoize(label(terminal_type(Token.is_value('*', '/', '%')), label=prec_op_labels[1]))
prec2_op = memoize(label(terminal_type(Token.is_value('+', '-')), label=prec_op_labels[2]))
prec3_op = memoize(label(terminal_type(Token.is_value('>', '<', '>=', '<=')), label=prec_op_labels[3]))
prec4_op = memoize(label(terminal_type(Token.is_value('!=', '==', 'eq', 'neq')), label=prec_op_labels[4]))
prec5_op = memoize(label(terminal_type(Token.is_value('and')), label=prec_op_labels[5]))
prec6_op = memoize(label(terminal_type(Token.is_value('or')), label=prec_op_labels[6]))
prec_ops = [prec0_op, prec1_op, prec2_op, prec3_op, prec4_op, prec5_op, prec6_op]

def create_precedence_expressions(prec_ops, *, labels):
    def exp_wrapper(i):
        return lambda *x: prec_exps[i](*x)
    
    prec_exps = []
    for i, (prec_op, the_label) in enumerate(zip(prec_ops, labels)):
        if i == 0:
            previous = binary_operand
        else:
            previous = exp_wrapper(i - 1)
        prec_exps.append(memoize(label(
            then(previous, zero_or_more(then(prec_op, previous))),
            label=the_label,
            collapsed=True
        )))
    return prec_exps

prec_exps = create_precedence_expressions(prec_ops, labels=prec_exp_labels)

expression = memoize(label(orelse(
    prec_exps[-1],
    then(open_paren, lambda *x: word_list(*x), close_paren),
    empty,
    keep=True
), label='expression', forced=True))

wrapped_expression = memoize(label(then(
    open_paren,
    expression,
    close_paren,
), label='expression', gathered=True))


expression_list = memoize(then(
    expression, one_or_more(then(comma, expression))
))

wrapped_expression_list = memoize(then(
    open_paren,
    expression_list,
    close_paren,
))

array = memoize(label(then(
    eat(terminal_type(Token.is_value('['))),
    orelse(expression_list, expression, keep=True),
    eat(terminal_type(Token.is_value(']')))
), label='array', forced=True))

callable = memoize(orelse(
    lambda *x: index(*x),
    wrapped_expression,
    name,
))

callee = memoize(label(orelse(
    then(open_paren, close_paren),
    wrapped_expression,
    wrapped_expression_list,
    keep=True
), label='params', forced=True))

function_call = memoize(label(then(
    callable, one_or_more(callee)
), label='function_call'))

indexable = memoize(orelse(
    function_call,
    wrapped_expression,
    array,
    name
))

index = memoize(label(then(
    indexable, one_or_more(array)
), label='index'))

composable_unary_operand = memoize(keep(label(orelse(
    index,
    function_call,
    array,
    name,
    wrapped_expression,
    number,
    keep=True
), label='operand')))

implicit_mult = memoize(label(then(
    composable_unary_operand, one_or_more(composable_unary_operand)
), label='implicit_mult'))

unary_operand = memoize(keep(orelse(
    implicit_mult,
    composable_unary_operand,
)))

word_list = memoize(label(orelse(
    then(word, zero_or_more(then(comma, word))),
    empty,
    keep=True
), label='word_list', forced=True))

function_def = memoize(label(then(
    word, open_paren, word_list, close_paren, equal_sign, expression
), label='function_def'))

var_def = memoize(label(then(
    # word, equal_sign, orelse(lambda *x: var_def(*x), expression, keep=True)
    one_or_more(then(word, equal_sign)), expression
), label='var_def'))

line = memoize(label(orelse(
    function_def,
    var_def,
    expression,
    keep=True
), label='line'))

program = memoize(label(then(
    line, zero_or_more(then(semi_colon, line))
), label='program'))