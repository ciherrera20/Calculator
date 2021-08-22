from abc import ABC, abstractmethod
import Scope
import Interpreter

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
            scope.set_value('self', self, mutable=False)
            values = [param.eval('Cannot bind a{} to a function parameter') for param in params]
            for name, value in zip(self._param_names, values):
                scope.set_value(name, value, mutable=False)
            interpreter = Interpreter.Interpreter(scope)
            return interpreter.evaluate_AST(self._definition)

    def serialize(self, path, serialized):
        if self not in serialized:
            # Store a path to avoid circular references
            serialized[self] = path

            if self._definition not in serialized:
                serialized[self._definition] = '{}/definition'.format(path)
                definition = self._definition
            else:
                definition = serialized[self._definition]

            # Create the serializable object
            new_path = '{}/parent_scope'.format(path)
            obj = {
                'name': self._name,
                'param_names': self._param_names,
                'definition': definition,
                'parent_scope': self._parent_scope.serialize(new_path, serialized),
            }

            return obj
        else:
            # Return the memoized path
            return serialized[self]

    def deserialize(obj, path, deserialized):
        if path not in deserialized:
            # Create Function object and add it to the deserialized dict
            definition = obj['definition']
            if type(definition) == str:
                definition = deserialized[definition]
            else:
                definition = deserialize_AST(obj['definition'])
                deserialized['{}/definition'.format(path)] = definition
            func = UserFunction(obj['name'], obj['param_names'], definition, None)
            deserialized[path] = func

            # Deserialize the parent scope
            new_path = '{}/parent_scope'.format(path)
            parent_scope = obj['parent_scope']
            if type(parent_scope) == str:
                parent_scope = deserialized[parent_scope]
            else:
                parent_scope = Scope.Scope.deserialize(parent_scope, new_path, deserialized)
            func._parent_scope = parent_scope
            return func
        else:
            return deserialized[path]

def deserialize_AST(AST):
        '''
        Recursively traverse the AST converting lists into tuples
        '''
        if type(AST) == list:
            new_AST = ()
            for elem in AST:
                new_AST += (deserialize_AST(elem),)
            return new_AST
        else:
            return AST

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