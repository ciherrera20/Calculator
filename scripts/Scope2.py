from abc import ABC, abstractmethod
from functools import reduce
import Interpreter2
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
                func = UserFunction('<anonymous>', param_names, definition.get_AST(), scope)
                scope.set_value('self', func)
                return func
        BuiltinFunction('lambda', ['param_names', 'expression'], lambda_def).add_to(scope, mutable=False)

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
                interpreter = Interpreter2.Interpreter(scope)
                exp = Interpreter2.ExpressionWrapper(exp.get_AST(), interpreter)

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
        BuiltinFunction('sum', ['index', 'start', 'end', 'expression'], sum_def).add_to(scope, mutable=False)

        # Define the ifelse function
        BuiltinFunction('ifelse', ['condition', 'expression_true', 'expression_false'],
            lambda c, e_t, e_f: e_t.eval() if c.eval() else e_f.eval()
        ).add_to(scope, mutable=False)

        # Define the len function
        BuiltinFunction('len', ['array'],
            lambda array: len(array.eval())
        ).add_to(scope, mutable=False)

        # Define the sin function
        BuiltinFunction('sin', ['theta'],
            lambda theta: np.sin(theta.eval())
        ).add_to(scope, mutable=False)

        # Define the cos function
        BuiltinFunction('cos', ['theta'],
            lambda theta: np.cos(theta.eval())
        ).add_to(scope, mutable=False)

        # Define the tan function
        BuiltinFunction('tan', ['theta'],
            lambda theta: np.tan(theta.eval())
        ).add_to(scope, mutable=False)

        # Define the arcsin function
        BuiltinFunction('arcsin', ['x'],
            lambda x: np.arcsin(x.eval())
        ).add_to(scope, mutable=False)

        # Define the arccos function
        BuiltinFunction('arccos', ['x'],
            lambda x: np.arccos(x.eval())
        ).add_to(scope, mutable=False)

        # Define the arctan function
        BuiltinFunction('arctan', ['x'],
            lambda x: np.arctan(x.eval())
        ).add_to(scope, mutable=False)

        # Define the arctan2 function
        BuiltinFunction('arctan2', ['y', 'x'],
            lambda y, x: np.arctan2(x.eval(), y.eval())
        ).add_to(scope, mutable=False)

        # Define the sqrt function
        BuiltinFunction('sqrt', ['x'],
            lambda x: np.sqrt(x.eval())
        ).add_to(scope, mutable=False)

        # Define the exp function
        BuiltinFunction('exp', ['x'],
            lambda x: np.exp(x.eval())
        ).add_to(scope, mutable=False)

        if interface:
            def exit():
                raise KeyboardInterrupt('Exiting the program...')
            # Define the exit function
            BuiltinFunction('exit', [], exit).add_to(scope, mutable=False)

            def clear():
                print('')
                if os.name == 'nt':
                    _ = os.system('cls')
                else:
                    _ = os.system('clear')
                raise NoNewline()
            BuiltinFunction('clear', [], clear).add_to(scope, mutable=False)

        return scope

class Function(ABC):
    def __init__(self, name, param_names):
        self._name = name
        self._param_names = param_names
    
    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def evaluate(self, expressions):
        '''
        Evaluates a user defined function.
        Arguments:
            parent_interpreter:     The interpreter used to evaluate the arguments passed to the user function's definition
            expressions:            A list of abstract syntax trees whose values are to be bound to the function's parameters
        '''
        pass
    
    def add_to(self, scope, mutable=True):
        scope.set_value(self._name, self, mutable=mutable)

class UserFunction(Function):
    '''
    In a user function, the definition is an abstract syntax tree given by the parser
    '''
    def __init__(self, name, param_names, definition, parent_scope):
        super().__init__(name, param_names)
        self._definition = definition
        self._parent_scope = parent_scope
    
    def __repr__(self):
        num_params = len(self._param_names)
        if num_params > 1:
            return ('UserFunction: {}(' + ('{}, ' * (num_params - 1)) + '{})').format(self._name, *self._param_names)
        else:
            return ('UserFunction: {}(' + ('{}' * num_params) + ')').format(self._name, *self._param_names)

    def evaluate(self, params):
        if len(params) != len(self._param_names):
            raise ValueError('{} expected {} arguments but received {}'.format(self._name, len(self._param_names), len(params)))
        else:
            scope = Scope(parent=self._parent_scope)
            values = [param.eval('Cannot bind a{} to a function parameter') for param in params]
            for name, value in zip(self._param_names, values):
                scope.set_value(name, value)
            interpreter = Interpreter2.Interpreter(scope)
            return interpreter.evaluate_AST(self._definition)

class BuiltinFunction(Function):
    def __init__(self, name, param_names, func):
        super().__init__(name, param_names)
        self._func = func
    
    def __repr__(self):
        num_params = len(self._param_names)
        if num_params > 1:
            return ('BuiltinFunction: {}(' + ('{}, ' * (num_params - 1)) + '{})').format(self._name, *self._param_names)
        else:
            return ('BuiltinFunction: {}(' + ('{}' * num_params) + ')').format(self._name, *self._param_names)

    def evaluate(self, params):
        if len(params) != len(self._param_names):
            raise ValueError('{} expected {} arguments but received {}'.format(self._name, len(self._param_names), len(params)))
        else:
            return self._func(*params)