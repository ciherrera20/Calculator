from abc import ABC, abstractmethod
import Scope

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
            scope = Scope.Scope(parent=self._parent_scope)
            values = [param.eval('Cannot bind a{} to a function parameter') for param in params]
            for name, value in zip(self._param_names, values):
                scope.set_value(name, value)
            interpreter = Interpreter.Interpreter(scope)
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