from abc import ABC, abstractmethod
import Interpreter

class Scope():
    def __init__(self, parent=None):
        self._parent = parent
        self._symbol_table = {}
    
    def retrieve_value(self, name):
        if name in self._symbol_table:
            return self._symbol_table[name]
        elif self._parent is not None:
            return self._parent.retrieve_value(name)
        else:
            raise ValueError('\'{}\' is not defined'.format(name))
    
    def set_value(self, name, value):
        self._symbol_table[name] = value
        return value
    
    def get_global_scope():
        scope = Scope()
        scope.set_value('True', True)
        scope.set_value('False', False)
        scope.set_value('lambda', LambdaFunction())
        BuiltinFunction('ifelse', ['condition', 'expression_true', 'expression_false'],
            lambda c, e_t, e_f: e_t.eval() if c.eval() else e_f.eval()
        ).add_to(scope)
        return scope

class Function(ABC):
    def __init__(self, name, param_names):
        self._name = name
        self._param_names = param_names
    
    @abstractmethod
    def evaluate(self, expressions):
        '''
        Evaluates a user defined function.
        Arguments:
            parent_interpreter:     The interpreter used to evaluate the arguments passed to the user function's definition
            expressions:            A list of abstract syntax trees whose values are to be bound to the function's parameters
        '''
        pass
    
    def add_to(self, scope):
        scope.set_value(self._name, self)

class UserFunction(Function):
    '''
    In a user function, the definition is an abstract syntax tree given by the parser
    '''
    def __init__(self, name, param_names, definition, parent_scope):
        super().__init__(name, param_names)
        self._definition = definition
        self._parent_scope = parent_scope
    
    def evaluate(self, parent_interpreter, expressions):
        if len(expressions) != len(self._param_names):
            raise ValueError('{} expected {} arguments but received {}'.format(self._name, len(self._param_names), len(expressions)))
        else:
            scope = Scope(parent=self._parent_scope)
            values = [parent_interpreter.evaluate_AST(expression) for expression in expressions]
            for name, value in zip(self._param_names, values):
                scope.set_value(name, value)
            interpreter = Interpreter.Interpreter(scope)
            return interpreter.evaluate_AST(self._definition)

class LambdaFunction(Function):
    def __init__(self):
        super().__init__('lambda', ['word_list', 'expression'])
    
    def evaluate(self, parent_interpreter, expressions):
        if len(expressions) != 2:
            raise ValueError('lambda expected 2 arguments but received {}'.format(len(expressions)))
        word_list, definition = expressions
        word_list = parent_interpreter.get_word_list(word_list)
        if word_list is None:
            raise ValueError('lambda expected a word list as its first argument')
        return UserFunction('lambda_function', word_list, definition, parent_interpreter._scope)

class BuiltinFunction(Function):
    def __init__(self, name, param_names, func):
        super().__init__(name, param_names)
        self._func = func
    
    def evaluate(self, parent_interpreter, expressions):
        if len(expressions) != len(self._param_names):
            raise ValueError('{} expected {} arguments but received {}'.format(self._name, len(self._param_names), len(expressions)))
        else:
            wrapped_expressions = [ExpressionWrapper(expression, parent_interpreter) for expression in expressions]
            return self._func(*wrapped_expressions)

class ExpressionWrapper():
    def __init__(self, expression, interpreter):
        self._expression = expression
        self._interpreter = interpreter
    
    def eval(self):
        return self._interpreter.evaluate_AST(self._expression)
    
    def word_list(self):
        return self._interpreter.get_word_list(self._expression)