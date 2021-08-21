from functools import reduce
from Lexer import Token, tokenize

def terminal(t):
    '''
    Creates a parser for the given terminal symbol
    '''
    def parse_terminal(tokens, pos):
        '''
        Parser for a given terminal symbol
        '''
        if pos >= len(tokens):
            return (set(), {})
        elif tokens[pos] == t:
            return ({pos + 1}, {pos + 1: ((tokens[pos],),)})
        else:
            return(set(), {})
    return parse_terminal

def terminal_type(type_func):
    '''
    Creates a parser for a terminal that satisfies a given type function, defined by the function returning true
    '''
    def parse_terminal_type(tokens, pos):
        '''
        Parser for a terminal that satisfies a type function, defined by the function returning true
        '''
        if pos >= len(tokens):
            return (set(), {})
        elif type_func(tokens[pos]):
            return ({pos + 1}, {pos + 1: ((tokens[pos],),)})
        else:
            return (set(), {})
    return parse_terminal_type

def empty(tokens, pos):
    return ({pos}, {pos: ()})

def unite_output(output1, output2):
    pos_set1, tree_dict1 = output1
    pos_set2, tree_dict2 = output2
    pos_set = pos_set1.union(pos_set2)
    tree_dict = {}
    for pos in pos_set1:
        tree_dict[pos] = tree_dict1[pos]
    for pos in pos_set2:
        tree_dict[pos] = tree_dict2[pos]
    return (pos_set, tree_dict)

def orelse(*parsers, keep=False):
    def parse_alternates(tokens, pos):
        pos_set, tree_dict = (set(), {})
        for parser in parsers:
            int_pos_set, int_tree_dict = parser(tokens, pos)
            if len(int_pos_set) != 0 and keep:
                return (int_pos_set, int_tree_dict)
            else:
                pos_set, tree_dict = unite_output((pos_set, tree_dict), (int_pos_set, int_tree_dict))
        # pos_set, tree_dict = reduce(unite_output, map(lambda parser: parser(tokens, pos), parsers), (set(), {}))
        # if len(pos_set) > 1:
        #     print('{} alternatives generated for \'{}\' at {}: {}'.format(len(pos_set), current_label, pos, pos_set))
        return (pos_set, tree_dict)
    return parse_alternates

def add_tree(output, tree):
    pos_set, tree_dict = output
    new_tree_dict = {}
    for pos in pos_set:
        new_tree_dict[pos] = tree + tree_dict[pos]
    return (pos_set, new_tree_dict)

def then(*parsers):
    global current_label
    def parse_sequential(tokens, pos):
        global current_label
        output = ({pos}, {pos: ()})
        max_pos = pos
        for parser in parsers:
            output = reduce(unite_output, map(lambda pos: add_tree(parser(tokens, pos), output[1][pos]), output[0]), (set(), {}))
            # if len(output[0]) == 0:
            #     if max_pos is not None:
            #         print('Prefix removed at label {}. Old max pos was {}, pos set is now empty.'.format(current_label, max_pos))
            # elif max(output[0]) < max_pos:
            #     print('Prefix removed at label {}. Old max pos was {}, max pos is now {}.'.format(current_label, max_pos, max(output[0])))
            #     max_pos = max(output[0])
            # else:
            #     max_pos = max(output[0])
        return output
    return parse_sequential

def keep(parser):
    def kept_parser(tokens, pos):
        pos_set, tree_dict = parser(tokens, pos)
        if len(pos_set) > 0:
            max_pos = max(pos_set)
            return ({max_pos}, {max_pos: tree_dict[max_pos]})
        else:
            return (pos_set, tree_dict)
        # return parser(tokens, pos)
    return kept_parser

memo_table = {}
c_table = {}
current_tokens = None
def memoize(parser):
    global memo_table, c_table, current_tokens
    def memoized_parser(tokens, pos):
        global memo_table, c_table, current_tokens
        # Discard memo table and c table if there is a new set of tokens
        if tokens is not current_tokens:
            # print('flushing old memo table of length {}', len(memo_table))
            memo_table = {}
            c_table = {}
            current_tokens = tokens
        
        # Check if the parser has already given a result for this position. If so return it.
        if (parser, pos) in memo_table:
            return memo_table[(parser, pos)]

        # Otherwise, apply the parser.
        # If this is the first time the parser sees this position, record it on c_table.
        if (parser, pos) not in c_table:
            c_table[(parser, pos)] = 1
        
        # Retrieve the recursion depth from c_table.
        c_pj = c_table[(parser, pos)]
        # print('Applying {} to {} with recursion depth {}'.format(p, j, c_pj))

        # If the recursion depth is greater than the tokens' remaining length + 1, curtail the recursion by returning the empty set.
        if c_pj > len(tokens) - pos + 1:
            # print('maximum recursion depth reached for {} at position {}'.format(current_label, pos))
            return (set(), {})

        # Otherwise, apply the parser and increment the depth of recursion.
        c_table[(parser, pos)] = c_pj + 1
        output = parser(tokens, pos)
        memo_table[(parser, pos)] = output
        return output
    return memoized_parser

current_label = None
def label(parser, *, label, gathered=False, collapsed=False, forced=False):
    global current_label
    def labeled_parser(tokens, pos):
        global current_label
        current_label = label
        pos_set, tree_dict = parser(tokens, pos)
        new_tree_dict = {}
        for pos in pos_set:
            rtree = tree_dict[pos]
            if rtree == ():
                if forced:
                    new_tree_dict[pos] = ((label, ()),)
                else:
                    new_tree_dict[pos] = rtree
            elif gathered:
                new_tree = ()
                for subtree in rtree:
                    if subtree[0] != label:
                        new_tree += (subtree,)
                    else:
                        new_tree += subtree[1:]
                new_tree_dict[pos] = ((label,) + new_tree,)
            elif collapsed:
                can_collapse = reduce(lambda x, y: x and y, [len(subtree) > 1 and subtree[0] == label for subtree in rtree], True)
                if can_collapse:
                    new_tree = ()
                    for subtree in rtree:
                        new_tree += subtree[1:]
                    new_tree_dict[pos] = ((label,) + new_tree,)
                else:
                    new_tree_dict[pos] = ((label,) + rtree,)    
            else:
                new_tree_dict[pos] = ((label,) + rtree,)
        return (pos_set, new_tree_dict)
    return labeled_parser

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