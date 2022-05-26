from Parsers import program
import numpy as np
import Scope
import Function
from Lexer import Token, tokenize
from functools import reduce

class ExpressionWrapper():
    def __init__(self, expression, interpreter):
        self._expression = expression
        self._interpreter = interpreter
    
    def get_AST(self):
        return self._expression

    def eval(self, err_msg='Did not expect a{}'):
        value = self._interpreter.evaluate_AST(self._expression)
        if type(value) == list:
            raise ValueError(err_msg.format(' word list'))
        elif value is None:
            raise ValueError(err_msg.format('n empty expression'))
        else:
            return value

    def to_word_list(self):
        return self._interpreter.get_word_list(self._expression)
    
    def get_scope(self):
        return self._interpreter._scope

class Interpreter():
    def __init__(self, scope):
        self._scope = scope

    def evaluate(self, string):
        return self.evaluate_AST(self._get_AST(string))

    def evaluate_AST(self, AST):
        if AST == ():
            return None
        else:
            return self._evaluate_node(AST, self._evaluate_leaf, {
                'program': self._evaluate_program,
                'expression': self._evaluate_expression
            })

    def get_word_list(self, expression):
        try:
            wl = self._evaluate_node(expression, self._evaluate_leaf, {
                'expression': self._evaluate_word_list_expression
            })
            if wl is None:
                return []
            elif type(wl) == str:
                if '.' in wl:
                    return None
                else:
                    return [wl]
            else:
                return wl
        except KeyError:
            return None

    def serialize(self):
        return self._scope.serialize('.', {})

    def retrieve_value(self, name):
        return self._scope.retrieve_value(name)

    def set_value(self, name, value, mutable=True, force=False):
        return self._scope.set_value(name, value, mutable=mutable, force=force)
    
    def get_root_scope(self):
        return self._scope.get_root_scope()

    def _get_AST(self, string):
        tokens = tokenize(string)
        pos_set, tree_dict = program(tokens, 0)
        if len(tokens) not in pos_set:
            if len(pos_set) == 0:
                raise ValueError('Syntax error')
            else:
                error_pos = max(pos_set)
                raise ValueError('Unexpected token \'{}\''.format(tokens[error_pos]))
        else:
            tree = tree_dict[len(tokens)]
            if tree == ():
                return tree
            else:
                return tree[0]

    def _evaluate_node(self, tree, leaf_callback, callback_dict):
        if len(tree) < 2:
            return leaf_callback(tree)
        else:
            elems = tree[1:]
            return callback_dict[tree[0]](*tree[1:])

    def _evaluate_leaf(self, leaf):
        raise ValueError('Why is there a leaf here?')

    def _evaluate_program(self, *lines):
        results = []
        for line in lines:
            results.append(self._evaluate_node(line, self._evaluate_leaf, {
                'line': self._evaluate_line
            }))
        return results[-1]

    def _evaluate_line(self, rest):
        if rest == ():
            return None
        else:
            value = self._evaluate_node(rest, self._evaluate_leaf, {
                'var_def': self._evaluate_var_def,
                'function_def': self._evaluate_function_def,
                'expression': self._evaluate_expression
            })
            if type(value) == list:
                raise ValueError('A word list is not a valid line')
            return value

    def _evaluate_var_def(self, *args):
        if len(args) == 1:
            raise ValueError('No value given for variable definition')
        value = self._evaluate_node(args[-1], self._evaluate_leaf, {
            'expression': self._evaluate_valid_expression('A variable cannot be a{}')
        })
        for arg in args[:-1]:
            self._scope.set_value(arg[0].value, value)
        return value

    def _evaluate_word_list(self, *args):
        if len(args) == 1 and args[0] == ():
            return []
        else:
            return [arg[0].value for arg in args]

    def _evaluate_function_def(self, word, word_list, definition):
        function_name = word[0].value
        param_names = self._evaluate_node(word_list, self._evaluate_leaf, {
            'word_list': self._evaluate_word_list
        })
        user_function = Function.UserFunction(function_name, param_names, definition, self._scope)
        self._scope.set_value(function_name, user_function)
        return None

    def _evaluate_expression(self, AST):
        if AST == ():
            return None
        else:
            return self._evaluate_node(AST, self._evaluate_leaf, {
                'infix': self._evaluate_infix,
                'word_list': self._evaluate_word_list
            })
    
    def _evaluate_valid_expression(self, error_msg, allow_none=False):
        def _evaluator(AST):
            value = self._evaluate_expression(AST)
            if type(value) == list:
                raise ValueError(error_msg.format(' word list'))
            elif value is None and not allow_none:
                raise ValueError(error_msg.format('n empty expression'))
            else:
                return value
        return _evaluator
    
    def _evaluate_word_list_expression(self, AST):
        if AST == ():
            return None
        else:
            return self._evaluate_node(AST, self._evaluate_leaf, {
                'infix': self._evaluate_word_list_expression,
                'operand': self._evaluate_word_list_expression,
                'expression': self._evaluate_word_list_expression,
                'name': self._retrieve_name,
                'word_list': self._evaluate_word_list
            })

    def _evaluate_infix(self, *args):
        values = [self._evaluate_node(arg, self._evaluate_leaf, {
            'infix': self._evaluate_infix,
            'operand': self._evaluate_operand,
            'operator': self._evaluate_operator
        }) for arg in args]
        if (len(values) - 1) % 2 != 0:
            raise ValueError('Invalid number of infix arguments... good job Chris this shouldn\'t be possible at all')
        while len(values) > 1:
            value1, func, value2 = values[:3]
            values = [func(value1, value2)] + values[3:]
        return values[0]

    def _evaluate_operator(self, operator):
        raw = operator[0].value
        if raw == '^':
            return np.power
        elif raw == '*':
            return np.multiply
        elif raw == '/':
            return np.divide
        elif raw == '%':
            return np.mod
        elif raw == '+':
            return np.add
        elif raw == '-':
            return np.subtract
        elif raw == '>':
            return np.greater
        elif raw == '<':
            return np.less
        elif raw == '>=':
            return np.greater_equal
        elif raw == '<=':
            return np.less_equal
        elif raw == '==' or raw == 'eq':
            return np.equal
        elif raw == '!=' or raw == 'neq':
            return np.not_equal
        elif raw == 'and':
            return np.logical_and
        elif raw == 'or':
            return np.logical_or
        else:
            raise ValueError('Unknown operator')

    def _evaluate_unary_operator(self, operator):
        raw = operator[0].value
        if raw == '+':
            return np.positive
        elif raw == '-':
            return np.negative
        elif raw == '!' or raw == 'not':
            return np.logical_not
        else:
            raise ValueError('Unknown unary operator')

    def _evaluate_operand(self, *args):
        if len(args) > 1:
            ops = [self._evaluate_node(arg, self._evaluate_leaf, {
                'operator': self._evaluate_unary_operator
            }) for arg in args[:-1]]
            value = self._evaluate_node(args[-1], self._evaluate_leaf, {
                'operand': self._evaluate_operand,
                'implicit_mult': self._evaluate_implicit_mult
            })
            for op in reversed(ops):
                value = op(value)
            return value
        else:
            # If the only argument is a leaf, then it can only be a number, so return its value
            if len(args[0]) == 1:
                return args[0][0].value
            else:
                return self._evaluate_node(args[0], self._evaluate_leaf, {
                    'implicit_mult': self._evaluate_implicit_mult,
                    'index': self._evaluate_index,
                    'function_call': self._evaluate_function_call,
                    'array': self._evaluate_array,
                    'name': self._evaluate_name,
                    'expression': self._evaluate_valid_expression('A{} cannot be an operand'),
                })

    def _evaluate_implicit_mult(self, *args):
        values = [
            self._evaluate_node(arg, self._evaluate_leaf, {
                'operand': self._evaluate_operand
            }) for arg in args
        ]
        return reduce(np.multiply, values[1:], values[0])

    def _evaluate_name(self, *args):
        name = self._retrieve_name(*args)
        return self._scope.retrieve_value(name)
    
    def _retrieve_name(self, *args):
        return '.'.join([arg[0].value for arg in args])

    def _evaluate_array(self, *args):
        if len(args) == 1 and args[0] == ():
            return np.array([])
        else:
            # Allow for empty arrays
            if len(args) == 1:
                values = [self._evaluate_node(arg, self._evaluate_leaf, {
                    'expression': self._evaluate_valid_expression('A{} cannot be an array element', allow_none=True)
                }) for arg in args]
                if values[0] == None:
                    return np.array([])
            else:
                values = [self._evaluate_node(arg, self._evaluate_leaf, {
                    'expression': self._evaluate_valid_expression('A{} cannot be an array element')
                }) for arg in args]
            return np.array(values)

    def _evaluate_param_set(self, *args):
        if len(args) == 1 and args[0] == ():
            return []
        else:
            return [ExpressionWrapper(arg, self) for arg in args]

    def _evaluate_function_call(self, callable, *args):
        def empty_err(*x):
            raise ValueError('An empty expression is not callable')
        
        value = self._evaluate_node(callable, self._evaluate_leaf, {
            'expression': self._evaluate_valid_expression('A{} is not callable'),
            'params': empty_err,
            'name': self._evaluate_name,
            'index': self._evaluate_index
        })
        param_sets = [self._evaluate_node(arg, self._evaluate_leaf, {
            'params': self._evaluate_param_set
        }) for arg in args]

        for param_set in param_sets:
            if isinstance(value, Function.Function):
                value = value.evaluate(param_set)
            else:
                if len(param_set) != 1:
                    raise ValueError('\'{}\' is not callable'.format(type(value)))
                else:
                    value = np.multiply(value, param_set[0].eval('Cannot multiply by a{}'))
        return value

    def _evaluate_index(self, indexable, *args):
        value = self._evaluate_node(indexable, self._evaluate_leaf, {
            'expression': self._evaluate_valid_expression('A{} is not indexable'),
            'name': self._evaluate_name,
            'funcion_call': self._evaluate_function_call,
            'array': self._evaluate_array
        })
        indices = [self._evaluate_node(arg, self._evaluate_leaf, {
            'array': self._evaluate_array
        }) for arg in args]

        for index in indices:
            if type(value) == np.ndarray:
                # int_array = index.astype(np.int32)
                # equivalent = np.ufunc.reduce(np.logical_and, int_array == index, axis=None)
                # if not equivalent:
                #     raise ValueError('An array can only be indexed with integers')
                # else:
                #     value = value[tuple(int_array)]
                int_array = Interpreter.to_ints(index, 'An array can only be indexed with integers')
                value = value[tuple(int_array)]
            else:
                value = np.multiply(value, index)
        return value
    
    def to_ints(array, msg):
        if type(array) == np.ndarray:
            int_array = array.astype(np.int32)
            equivalent = np.ufunc.reduce(np.logical_and, int_array == array, axis=None)
        elif type(array) == float:
            int_array = int(array)
            equivalent = int_array == array
        if not equivalent:
            raise ValueError(msg)
        return int_array

    def get_global_interpreter(interface=False, subscope=None):
        return Interpreter(Scope.Scope.get_global_scope(interface=interface, subscope=subscope))

    def deserialize(obj):
        return Scope.Scope.deserialize(obj, '.', {})

interpreter = None
if __name__ == '__main__':
    interpreter = Interpreter.get_global_interpreter()