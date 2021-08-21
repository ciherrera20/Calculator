# #!/usr/bin/env python 
import Interpreter2
import sys
import traceback
from Scope2 import NoNewline
import re
from prompt_toolkit import PromptSession
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
import asyncio
import selectors

selector = selectors.SelectSelector()
loop = asyncio.SelectorEventLoop(selector)
asyncio.set_event_loop(loop)

bindings = KeyBindings()

@bindings.add('s-down')
def _(event):
    event.app.current_buffer.insert_text('\n')

@bindings.add('s-tab')
def _(event):
    event.app.current_buffer.insert_text('    ')

if __name__ == '__main__':
    session = PromptSession()
    interpreter = Interpreter2.get_global_interpreter(interface=True)
    current_line = 0
    print('Enter expression:')
    sys.setrecursionlimit(3000)
    line_end_pattern = re.compile(r';\s*$|\S$')

    while True:
        # Get some input
        i = 0
        newline = True
        # print('{}: '.format(current_line), end='')
        current_line += 1
        line_end = False

        # Catch any errors
        try:
            program = session.prompt('{}: '.format(current_line), key_bindings=bindings)
            result = interpreter.evaluate(program)
        except ValueError as err:
            result = str(err)
        except RecursionError as err:
            result = str(err)
        except KeyboardInterrupt as err:
            result = str(err)
            break
        except IndexError as err:
            result = str(err)
        except NoNewline:
            newline = False
        except:
            result = traceback.print_exc()
        
        # Print result
        if newline:
            if result is None:
                print('')
            else:
                print('\t', end='')
                print(result)
        else:
            print('Enter expression:')