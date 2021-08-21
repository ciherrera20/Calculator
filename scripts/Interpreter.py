from Parsers import program
import numpy as np
import Scope

def remove_nodes(tree, *, labels):
    if len(tree) < 2:
        return tree
    else:
        if tree[0] in labels:
            return None
        else:
            new_tree = (tree[0],)
            for subtree in tree[1:]:
                node = remove_nodes(subtree, labels=labels)
                if node is not None:
                    new_tree += (node,)
            return new_tree

def remove_leaves(tree, *, type_func):
    if len(tree) == 0:
        return tree
    elif len(tree) == 1:
        if type_func(tree[0]):
            return None
        else:
            return tree
    else:
        new_tree = (tree[0],)
        for subtree in tree[1:]:
            node = remove_leaves(subtree, type_func=type_func)
            if node is not None:
                new_tree += (node,)
        return new_tree

def collapse_leaves(tree):
    '''
    Join adjacent leaves into single leaves with their values concatenated
    '''
    if len(tree) < 2:
        return tree
    else:
        new_tree = []
        for subtree in tree[1:]:
            if len(subtree) == 1:
                if len(new_tree) == 0 or len(new_tree[-1]) != 1:
                    new_tree.append(subtree)
                else:
                    new_tree[-1]= (new_tree[-1][0] + subtree[0],)
            else:
                new_tree.append(collapse_leaves(subtree))
        return (tree[0], *new_tree)

class Interpreter():
    def __init__(self, scope):
        self._scope = scope

    def _get_AST(self, string):
        pos_set, tree_dict = program(string, 0)
        if len(string) not in pos_set:
            if len(pos_set) == 0:
                raise ValueError('Syntax error')
            else:
                error_pos = max(pos_set)
                line_no = string[:error_pos + 1].count('\n')
                line_pos = error_pos
                if line_no > 0:
                    i = error_pos
                    while string[i] != '\n':
                        i -= 1
                    line_pos = line_pos - i - 1
                raise ValueError('Unexpected token \'{}\' at position {} on line {}'.format(string[error_pos], line_pos, line_no))
        else:
            tree = tree_dict[len(string)][0]
            AST = remove_nodes(tree, labels=['whitespace'])
            AST = remove_leaves(AST, type_func=lambda t: t in '()[];,')
            AST = collapse_leaves(AST)
            AST = remove_leaves(AST, type_func=lambda t: t in '.=')
            return AST

    def _evaluate_nodes(self, tree, leaf_callback, callback_dict):
        if len(tree) < 2:
            return leaf_callback(tree)
        else:
            return callback_dict[tree[0]](*tree[1:])

    def _evaluate_leaf(self, leaf):
        raise ValueError('Why is there a leaf here?')

    def evaluate_AST(self, AST):
        if AST == ():
            return None
        else:
            return self._evaluate_nodes(AST, self._evaluate_leaf, {
                'program': self._evaluate_program,
                'expression': self._evaluate_expression
            })

    def _evaluate_program(self, *lines):
        results = []
        for line in lines:
            results.append(self._evaluate_nodes(line, self._evaluate_leaf, {
                'line': self._evaluate_line
            }))
        return results[-1]

    def _evaluate_line(self, rest):
        if rest == ():
            return None
        else:
            value = self._evaluate_nodes(rest, self._evaluate_leaf, {
                'var_def': self._evaluate_var_def,
                'function_def': self._evaluate_function_def,
                'expression': self._evaluate_expression
            })
            if type(value) == list:
                raise ValueError('A word list is not a valid line')
            return value

    def _evaluate_word(self, leaf):
        return leaf[0]

    def _evaluate_var_def(self, word, rest):
        word = self._evaluate_nodes(word, self._evaluate_leaf, {
            'word': self._evaluate_word
        })
        value = self._evaluate_nodes(rest, self._evaluate_leaf, {
            'var_def': self._evaluate_var_def,
            'expression': self._evaluate_expression
        })
        if value is None:
            raise ValueError('No value given for variable definition')
        elif type(value) == list:
            raise ValueError('A variable cannot be a word list')
        return self._scope.set_value(word, value)

    def _evaluate_word_list(self, *words):
        if words[0] == ():
            return []
        return [self._evaluate_nodes(word, self._evaluate_leaf, {
            'word': self._evaluate_word
        }) for word in words]

    def _evaluate_function_def(self, word, word_list, definition):
        function_name = self._evaluate_nodes(word, self._evaluate_leaf, {
            'word': self._evaluate_word
        })
        param_names = self._evaluate_nodes(word_list, self._evaluate_leaf, {
            'word_list': self._evaluate_word_list
        })
        user_function = Scope.UserFunction(function_name, param_names, definition, self._scope)
        self._scope.set_value(function_name, user_function)
        return None

    def _evaluate_expression(self, rest):
        if rest == ():
            return None
        else:
            return self._evaluate_nodes(rest, self._evaluate_leaf, {
                'infix': self._evaluate_binary_infix,
                'operand': self._evaluate_operand,
                'word_list': self._evaluate_word_list
            })

    def _evaluate_binary_infix(self, operand1, operator, operand2):
        values = []
        for operand in [operand1, operand2]:
            values.append(self._evaluate_nodes(operand, self._evaluate_leaf, {
                'operand': self._evaluate_operand,
                'infix': self._evaluate_binary_infix
            }))
        operator_func = self._evaluate_nodes(operator, self._evaluate_leaf, {
            'operator': self._evaluate_operator
        })
        return operator_func(*values)

    def _evaluate_operator(self, leaf):
        operator_str = leaf[0]
        if operator_str == '^':
            return np.power
        elif operator_str == '*':
            return np.multiply
        elif operator_str == '/':
            return np.divide
        elif operator_str == '%':
            return np.mod
        elif operator_str == '+':
            return np.add
        elif operator_str == '-':
            return np.subtract
        elif operator_str == '>':
            return np.greater
        elif operator_str == '<':
            return np.less
        elif operator_str == '>=':
            return np.greater_equal
        elif operator_str == '<=':
            return np.less_equal
        elif operator_str == '==' or operator_str == 'eq':
            return np.equal
        elif operator_str == '!=' or operator_str == 'neq':
            return np.not_equal
        elif operator_str == 'and':
            return np.logical_and
        elif operator_str == 'or':
            return np.logical_or
        else:
            raise ValueError('Unknown operator')

    def _evaluate_operand(self, *rest):
        if len(rest) > 1:
            operator_func = self._evaluate_nodes(rest[0], self._evaluate_leaf, {
                'unary_operator': self._evaluate_unary_operator
            })
            value = self._evaluate_nodes(rest[1], self._evaluate_leaf, {
                'operand': self._evaluate_operand
            })
            return operator_func(value)
        else:
            value = self._evaluate_nodes(rest[0], self._evaluate_leaf, {
                'implicit_mult': self._evaluate_implicit_mult,
                'number': self._evaluate_number,
                'name': self._evaluate_name,
                'expression': self._evaluate_expression,
                'array': self._evaluate_array,
                'function_call': self._evaluate_function_call,
                'index': self._evaluate_index
            })
            if value is None:
                raise ValueError('An empty expression cannot be an operand')
            return value

    def _evaluate_unary_operator(self, leaf):
        operator_str = leaf[0]
        if operator_str == '+':
            return np.positive
        elif operator_str == '-':
            return np.negative
        elif operator_str == '!' or operator_str == 'not':
            return np.logical_not
        else:
            raise ValueError('Unknown unary operator')

    def _evaluate_implicit_mult(self, operand1, operand2):
        values = []
        for operand in [operand1, operand2]:
            values.append(self._evaluate_nodes(operand, self._evaluate_leaf, {
                'operand': self._evaluate_operand,
                'implicit_mult': self._evaluate_implicit_mult
            }))
        return np.multiply(*values)

    def _evaluate_number(self, leaf):
        return np.float(leaf[0])

    def _evaluate_name(self, *words):
        words = [self._evaluate_nodes(word, self._evaluate_leaf, {
            'word': self._evaluate_word
        }) for word in words]
        name = '.'.join(words)
        return self._scope.retrieve_value(name)
    
    def _retrieve_name(self, *words):
        words = [self._evaluate_nodes(word, self._evaluate_leaf, {
            'word': self._evaluate_word
        }) for word in words]
        return '.'.join(words)

    def _evaluate_array(self, *expressions):
        values = [self._evaluate_nodes(expression, self._evaluate_leaf, {
            'expression': self._evaluate_expression
        }) for expression in expressions]
        for value in values:
            if type(value) == list:
                raise ValueError('A word list cannot be an array element')
        if len(values) == 0 and values[0] is None:
            return np.array()
        return np.array(values)

    def _evaluate_function_call(self, callable, *expressions):
        # raise ValueError('I haven\'t implemented function calls yet')
        value = self._evaluate_nodes(callable, self._evaluate_leaf, {
            'expression': self._evaluate_expression,
            'function_call': self._evaluate_function_call,
            'name': self._evaluate_name,
            'index': self._evaluate_index
        })
        if value is None:
            raise ValueError('An empty expression is not callable')
        elif type(value) == list:
            raise ValueError('A word list is not callable')
        
        if isinstance(value, Scope.Function):
            return value.evaluate(self, self._filter_empty_expressions(expressions))
        elif len(expressions) > 1:
            raise ValueError('\'{}\' is not callable'.format(type(value)))
        else:
            value2 = self._evaluate_nodes(expressions[0], self._evaluate_leaf, {
                'expression': self._evaluate_expression
            })
            if value2 is None:
                raise ValueError('Cannot multiply by an empty expression')
            elif type(value2) == list:
                raise ValueError('Cannot multiply by a word list')
            return np.multiply(value, value2)
    
    def _filter_empty_expressions(self, expressions):
        non_empty = []
        for expression in expressions:
            if expression[1] != ():
                non_empty.append(expression)
        return non_empty

    def _evaluate_index(self, indexable, array):
        value = self._evaluate_nodes(indexable, self._evaluate_leaf, {
            'array': self._evaluate_array,
            'function_call': self._evaluate_function_call,
            'expression': self._evaluate_expression
        })
        if value is None:
            raise ValueError('An empty expression cannot be indexed')
        elif type(value) == list:
            raise ValueError('A word list cannot be indexed')
        array = self._evaluate_nodes(array, self._evaluate_leaf, {
            'array': self._evaluate_array
        })
        if type(value) != np.ndarray:
            return np.multiply(value, array)
        else:
            int_array = array.astype(np.int32)
            equivalent = np.ufunc.reduce(np.logical_and, int_array == array, axis=None)
            if not equivalent:
                raise ValueError('An array can only be indexed with integers')
            else:
                return value[tuple(int_array)]
    
    def get_word_list(self, expression):
        if expression[1][0] == 'operand' and expression[1][1][0] == 'expression':
            if expression[1][1][1] == ():
                return []
            elif expression[1][1][1][1][0] == 'name':
                name = self._evaluate_nodes(expression[1][1][1][1], self._evaluate_leaf, {
                    'name': self._retrieve_name
                })
                if '.' not in name:
                    return [name]
        else:
            word_list = self.evaluate_AST(expression)
            if type(word_list) == list:
                return word_list
        return None

    def evaluate(self, string):
        return self.evaluate_AST(self._get_AST(string))

def get_global_interpreter():
    return Interpreter(Scope.Scope.get_global_scope())

interpreter = None
if __name__ == '__main__':
    interpreter = get_global_interpreter()