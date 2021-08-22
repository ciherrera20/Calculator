import base64
import json
import numpy as np
from Lexer import Token

# Numpy encoder and decoder code taken from https://stackoverflow.com/questions/27909658/json-encoder-and-decoder-for-complex-numpy-arrays

class ProgramEncoder(json.JSONEncoder):
    def default(self, obj):
        '''
        If the input object is a Token, it will be converted into a dict holding the type and value.
        If input object is an ndarray, it will be converted into a dict holding dtype, shape, and the data base 64 encoded.
        '''
        if isinstance(obj, np.ndarray):
            print(obj)
            data_b64 = base64.b64encode(np.ascontiguousarray(obj).data).decode('ascii')
            return {
                '__ndarray__': data_b64,
                'dtype': str(obj.dtype),
                'shape': obj.shape
            }
        elif isinstance(obj, Token):
            return {'type': obj.type, 'value': obj.value}
        return json.JSONEncoder.default(self, obj)

def json_program_obj_hook(dct):
    '''
    Decodes a previously encoded numpy ndarray
    with proper shape and dtype, or a previously
    encoded Token.
    '''
    if isinstance(dct, dict):
        if '__ndarray__' in dct:
            data = base64.b64decode(dct['__ndarray__'])
            return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
        elif 'type' in dct:
            return Token(dct['type'], dct['value'])
    return dct