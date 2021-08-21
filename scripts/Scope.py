from functools import reduce
import Interpreter
import Function
import os
import numpy as np

class NoNewline(Exception):
    pass

class Scope():
    def __init__(self, parent=None):
        self._parent = parent
        self._symbol_table = {}
    
    def retrieve_value(self, name):
        if name in self._symbol_table:
            return self._symbol_table[name][0]
        elif self._parent is not None:
            return self._parent.retrieve_value(name)
        else:
            raise ValueError('\'{}\' is not defined'.format(name))
    
    def set_value(self, name, value, mutable=True):
        current_value = self._symbol_table.get(name)
        if not current_value or (current_value and current_value[1]):
            self._symbol_table[name] = (value, mutable)
        return value
    
    def get_global_scope(interface=False):
        scope = Scope()
        scope.set_value('True', True, mutable=False)
        scope.set_value('False', False, mutable=False)
        scope.set_value('pi', np.pi, mutable=False)
        scope.set_value('e', np.e, mutable=False)

        # Define the lambda function
        def lambda_def(word_list, definition):
            param_names = word_list.to_word_list()
            if param_names == None:
                raise ValueError('lambda expected a word list as its first argument')
            else:
                scope = Scope(parent=word_list.get_scope())
                func = Function.UserFunction('<anonymous>', param_names, definition.get_AST(), scope)
                scope.set_value('self', func)
                return func
        Function.BuiltinFunction('lambda', ['param_names', 'expression'], lambda_def).add_to(scope, mutable=False)

        # Define the sum function
        def sum_def(index, start, end, exp):
            index_names = index.to_word_list()
            start_val = start.eval()
            end_val = end.eval()
            if index_names == None or len(index_names) != 1:
                raise ValueError('sum exprected a single word as its first argument')
            else:
                # Create the scope and interpreter to use to evaluate the expression
                index_name = index_names[0]
                scope = Scope(parent=index.get_scope())
                interpreter = Interpreter.Interpreter(scope)
                exp = Interpreter.ExpressionWrapper(exp.get_AST(), interpreter)

                # Validate start and end values
                try:
                    int_start_val = int(start_val)
                    int_end_val = int(end_val)
                except TypeError:
                    raise ValueError('Start and end values must be integers')
                if int_start_val != start_val or int_end_val != end_val:
                    raise ValueError('Start and end values must be integers')

                # Create the range to iterate over
                if start_val <= end_val:
                    r = range(int_start_val, int_end_val + 1)
                else:
                    r = range(int_start_val, int_end_val - 1, -1)

                # Generate the values and return their sum
                values = []
                for i in r:
                    scope.set_value(index_name, i)
                    values.append(exp.eval())
                return reduce(np.add, values, 0)
        Function.BuiltinFunction('sum', ['index', 'start', 'end', 'expression'], sum_def).add_to(scope, mutable=False)

        # Define the ifelse function
        Function.BuiltinFunction('ifelse', ['condition', 'expression_true', 'expression_false'],
            lambda c, e_t, e_f: e_t.eval() if c.eval() else e_f.eval()
        ).add_to(scope, mutable=False)

        # Define the len function
        Function.BuiltinFunction('len', ['array'],
            lambda array: len(array.eval())
        ).add_to(scope, mutable=False)

        # Define the sin function
        Function.BuiltinFunction('sin', ['theta'],
            lambda theta: np.sin(theta.eval())
        ).add_to(scope, mutable=False)

        # Define the cos function
        Function.BuiltinFunction('cos', ['theta'],
            lambda theta: np.cos(theta.eval())
        ).add_to(scope, mutable=False)

        # Define the tan function
        Function.BuiltinFunction('tan', ['theta'],
            lambda theta: np.tan(theta.eval())
        ).add_to(scope, mutable=False)

        # Define the arcsin function
        Function.BuiltinFunction('arcsin', ['x'],
            lambda x: np.arcsin(x.eval())
        ).add_to(scope, mutable=False)

        # Define the arccos function
        Function.BuiltinFunction('arccos', ['x'],
            lambda x: np.arccos(x.eval())
        ).add_to(scope, mutable=False)

        # Define the arctan function
        Function.BuiltinFunction('arctan', ['x'],
            lambda x: np.arctan(x.eval())
        ).add_to(scope, mutable=False)

        # Define the arctan2 function
        Function.BuiltinFunction('arctan2', ['y', 'x'],
            lambda y, x: np.arctan2(x.eval(), y.eval())
        ).add_to(scope, mutable=False)

        # Define the sqrt function
        Function.BuiltinFunction('sqrt', ['x'],
            lambda x: np.sqrt(x.eval())
        ).add_to(scope, mutable=False)

        # Define the exp function
        Function.BuiltinFunction('exp', ['x'],
            lambda x: np.exp(x.eval())
        ).add_to(scope, mutable=False)

        if interface:
            def exit():
                raise KeyboardInterrupt('Exiting the program...')
            # Define the exit function
            Function.BuiltinFunction('exit', [], exit).add_to(scope, mutable=False)

            def clear():
                print('')
                if os.name == 'nt':
                    _ = os.system('cls')
                else:
                    _ = os.system('clear')
                raise NoNewline()
            Function.BuiltinFunction('clear', [], clear).add_to(scope, mutable=False)

        return scope