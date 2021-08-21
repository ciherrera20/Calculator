from functools import reduce

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

def terminal_class(tokens):
    return orelse(*[terminal(token) for token in tokens])

def neg_terminal_class(tokens):
    return terminal_type(lambda s: s not in tokens)

def terminal_sequence(tokens):
    return then(*[terminal(token) for token in tokens])

def boundary(terminals, include_empty=True):
    def boundary_parser(tokens, pos):
        if include_empty:
            to_add = ((),)
        else:
            to_add = ()
        if pos - 1 < 0 or tokens[pos - 1] not in terminals:
            if pos < len(tokens) and tokens[pos] in terminals:
                return ({pos}, {pos: to_add})
            else:
                return (set(), {})
        elif pos >= len(tokens) or tokens[pos] not in terminals:
            if tokens[pos - 1] in terminals:
                return ({pos}, {pos: to_add})
            else:
                return (set(), {})
        else:
            return(set(), {})
    return boundary_parser

word_char_ls = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'

# Define some boundaries, i.e. zero length matches
word_break = boundary(word_char_ls, include_empty=False)
start_word_boundary = boundary(word_char_ls[10:], include_empty=False)

# Guard a word by surrounding it with word breaks
def guarded_sequence(sequence):
    return then(word_break, terminal_sequence(sequence), word_break)

#------------------------ Basic definitions ------------------------#

# Parse a digit
digit = memoize(terminal_class('0123456789'))

# Parse one or more digits
digits = memoize(orelse(
    digit,
    then(digit, lambda *x: digits(*x))
))

# Parse a decimal place
decimal_place = memoize(terminal('.'))

# Parse a number possibly with a decimal place
number = memoize(label(orelse(
    then(decimal_place, digits),
    then(digits, decimal_place),
    then(digits, decimal_place, digits),
    digits,
    guarded_sequence('NaN'),
    guarded_sequence('Inf')
), label='number'))

# A word character
word_char = memoize(terminal_class(word_char_ls))

# 0 or more word characters
word_chars = memoize(orelse(
    empty,
    word_char,
    then(word_char, lambda *x: word_chars(*x))
))

# A word is defined as a non-digit and non-period word character followed by zero or more word characters
word = memoize(label(then(
    start_word_boundary,
    terminal_class('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'),
    word_chars,
    word_break,
), label='word'))

name = memoize(label(orelse(
    word,
    then(word, terminal('.'), lambda *x: name(*x))
), label='name', gathered=True))

# Match a single whitespace token
whitespace_token = memoize(terminal_type(lambda s: s.isspace()))

# Parse whitespace
whitespace = memoize(label(keep(orelse(
    empty,
    whitespace_token,
    then(whitespace_token, lambda *x: whitespace(*x))
)), label='whitespace', gathered=True))

# Define unary operators
unary_op = memoize(label(orelse(
    terminal_class('+-!'),
    guarded_sequence('not')
), label='unary_operator'))

# Define a binary_operand as a unary_operand followed by one or more unary operators
binary_operand = memoize(label(orelse(
    lambda *x: unary_operand(*x),
    then(whitespace, unary_op, lambda *x: binary_operand(*x)),
), label='operand', collapsed=True))

# unary_operand = number

# Define the number of levels of precedence of operators
num_prec_ops = 7

# Use more verbose names
# prec_op_labels = ['prec{}_op'.format(i) for i in range(num_prec_ops)]
# prec_exp_labels = ['prec{}_exp'.format(i) for i in range(num_prec_ops)]

# Use less verbose names
prec_op_labels = ['operator'] * num_prec_ops
prec_exp_labels = ['infix'] * num_prec_ops

# Define the operators of different precedences
prec0_op = memoize(label(terminal_class('^'), label=prec_op_labels[0]))
prec1_op = memoize(label(terminal_class('*/%'), label=prec_op_labels[1]))
prec2_op = memoize(label(terminal_class('+-'), label=prec_op_labels[2]))
prec3_op = memoize(label(orelse(
    terminal_class('><'),
    then(terminal_class('><'), terminal('=')),
), label=prec_op_labels[3]))
prec4_op = memoize(label(orelse(
    then(terminal_class('=!'), terminal('=')),
    guarded_sequence('eq'),
    guarded_sequence('neq'),
), label=prec_op_labels[4]))
prec5_op = memoize(label(guarded_sequence('and'), label=prec_op_labels[5]))
prec6_op = memoize(label(guarded_sequence('or'), label=prec_op_labels[6]))

# Create the expression parsers that correspond to each operator
# This only works for left-associative operators
def create_precedence_expressions(prec_ops, *, labels):
    # List out expressions of lower precedence
    # def list_lower_prec_exps(exps, op):
    #     ls = []
    #     for exp in exps:
    #         ls += [
    #             then(exp, whitespace, op, binary_operand),
    #             then(binary_operand, whitespace, op, exp),
    #             then(exp, whitespace, op, exp)
    #         ]
    #     return ls
    
    # Lambda wrapper to store the correct parser index in a closure, since the parser itself does not yet exist
    def lambda_wrapper(i):
        return lambda *x: prec_exps[i](*x)

    # Create the expression parsers
    prec_exps = []
    for i, (prec_op, the_label) in enumerate(zip(prec_ops, labels)):
        lower = orelse(*prec_exps)
        exp = lambda_wrapper(i)
        prec_exps.append(
            # Don't forget to memoize left recursive parsers!
            memoize(label(orelse(
                then(binary_operand, whitespace, prec_op, binary_operand),
                then(exp, whitespace, prec_op, binary_operand),
                then(exp, whitespace, prec_op, lower),
                then(lower, whitespace, prec_op, binary_operand),
                then(binary_operand, whitespace, prec_op, lower),
                then(lower, whitespace, prec_op, lower),
            ), label=the_label))
            # memoize(label(orelse(
            #     then(binary_operand, whitespace, prec_op, binary_operand),
            #     then(lambda_wrapper(i), whitespace, prec_op, binary_operand),
            #     *list_lower_prec_exps(prec_exps, prec_op),
            # ), label=the_label))
        )
    return prec_exps

# Create the expression parsers
prec_ops = [prec0_op, prec1_op, prec2_op, prec3_op, prec4_op, prec5_op, prec6_op]
prec_exps = create_precedence_expressions(
    prec_ops,
    labels=prec_exp_labels
)

# wrapped_expression = memoize(label(then(
#     whitespace,
#     terminal('('),
#     lambda *x: expression(*x),
#     whitespace,
#     terminal(')'),
# ), label='expression', gathered=True))

wrapped_expression = memoize(then(
    whitespace,
    terminal('('),
    lambda *x: expression(*x),
    whitespace,
    terminal(')'),
))

expression = memoize(label(keep(orelse(
    empty,
    then(whitespace, terminal('('), lambda *x: word_list(*x), whitespace, terminal(')')),
    binary_operand,
    *[parser for parser in prec_exps],
)), label='expression', forced=True))

expression_list = memoize(orelse(
    then(expression, whitespace, terminal(','), expression),
    then(expression, whitespace, terminal(','), lambda *x: expression_list(*x)),
))

wrapped_expression_list = memoize(then(
    whitespace, terminal('('), expression_list, whitespace, terminal(')')
))

array = memoize(label(then(
    whitespace, terminal('['), label(orelse(expression, expression_list), label='array', forced=True), whitespace, terminal(']')
), label='array', gathered=True))

callable = memoize(orelse(
    then(whitespace, name),
    wrapped_expression,
    lambda *x: index(*x)
))

callee = memoize(orelse(
    wrapped_expression,
    wrapped_expression_list
))

called = memoize(then(
    callable, callee
))

function_call = memoize(label(orelse(
    called,
    then(lambda *x: function_call(*x), callee),
), label='function_call'))

indexable = memoize(orelse(
    then(whitespace, name),
    array,
    function_call,
    wrapped_expression
))

indexed = memoize(then(
    indexable, array
))

index = memoize(label(orelse(
    indexed,
    then(lambda *x: index(*x), array),
), label='index'))

composable_unary_operand = memoize(label(orelse(
    then(whitespace, number),
    wrapped_expression,
    array,
    function_call,
    then(whitespace, name),
    index,
), label='operand'))

implicit_mult = memoize(label(orelse(
    then(lambda *x: implicit_mult(*x), composable_unary_operand),
    then(composable_unary_operand, composable_unary_operand),
), label='implicit_mult'))

unary_operand = memoize(orelse(
    implicit_mult,
    composable_unary_operand,
))

word_list = memoize(label(orelse(
    empty,
    then(whitespace, word),
    then(whitespace, word, whitespace, terminal(','), lambda *x: word_list(*x)),
), label='word_list', gathered=True, forced=True))

function_def = memoize(label(then(
    whitespace, word,
    whitespace, terminal('('), word_list, whitespace, terminal(')'),
    whitespace, terminal('='),
    expression,
), label='function_def'))

var_def = memoize(label(keep(orelse(
    then(whitespace, word, whitespace, terminal('='), expression),
    then(whitespace, word, whitespace, terminal('='), lambda *x: var_def(*x)),
)), label='var_def'))

# # import_statement = memoize(orelse(

# # ))

line = memoize(label(then(
    orelse(expression, function_def, var_def),
    whitespace,
), label='line'))

program = memoize(label(keep(orelse(
    line,
    then(line, terminal(';'), lambda *x: program(*x)),
)), label='program', gathered=True))

# Simple grammar that defines order of operations
mult_op = label(terminal('*'), label='operator')
mult_int = memoize(orelse(
    then(mult_op, terminal('x'), lambda *x: mult_int(*x)),
    empty,
    keep=True
))
mult = memoize(label(then(
    terminal('x'), mult_int
), label='infix', collapsed=True))

add_op = label(terminal('+'), label='operator')
add_int = memoize(orelse(
    then(add_op, mult, lambda *x: add_int(*x)),
    empty,
    keep=True
))
add = memoize(label(then(
    mult, add_int
), label='infix', collapsed=True))