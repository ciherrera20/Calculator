# #!/usr/bin/env python 
from json.decoder import JSONDecodeError
import Interpreter
import sys
import os
import traceback
import re
import asyncio
import selectors
# import atexit
import json
import argparse
import numpy as np
from Scope import NoNewline
from Serialize import ProgramEncoder, json_program_obj_hook
from prompt_toolkit import PromptSession
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import input_dialog, checkboxlist_dialog, radiolist_dialog
from prompt_toolkit.styles import Style

cwd = os.path.dirname(os.path.realpath(__file__))
# save_path = os.path.join(cwd, './save.calc')
exit_dialog = True
dialog_style = Style.from_dict({
    'dialog':             'bg:#88ff88',
    'dialog frame.label': 'bg:#ffffff #000000',
    'dialog':        'bg:#000000',
})

def find_saves(path):
    dirs = os.listdir(path)
    saves = []
    for f in dirs:
        if os.path.isfile(os.path.join(cwd, f)) and os.path.splitext(f)[1] == '.calc':
            saves.append(os.path.join(cwd, f))
    saves = sorted(saves, key=os.path.getmtime, reverse=True)
    return saves

def load(path):
    if os.path.isfile(path):
        # print('Save file exists at', {save_path})
        f = open(path, 'r')
        try:
            scope = Interpreter.Interpreter.deserialize(json.load(f, object_hook=json_program_obj_hook))
            f.close()
            return Interpreter.Interpreter.get_global_interpreter(interface=True, subscope=scope)
        except JSONDecodeError:
            return Interpreter.Interpreter.get_global_interpreter(interface=True)
    else:
        return Interpreter.Interpreter.get_global_interpreter(interface=True)

def save(path):
    f = open(path, 'w')
    json.dump(interpreter.serialize(), f, cls=ProgramEncoder)
    f.close()

def onexit(load_path=None):
    global exit_dialog
    # Give the option to save the scope before exiting
    if exit_dialog:
        NEW_SAVE = 1
        exit_dialog = False

        values = []
        if load_path:
            values = [
                (load_path, os.path.split(load_path)[1])
            ]
        values.append((NEW_SAVE, 'New save file'))

        save_path = radiolist_dialog(
            title='Save',
            text='Would you like to save your work?',
            values=values,
            style=dialog_style
        ).run()
        if save_path == NEW_SAVE:
            app = input_dialog(
                title='New save',
                text='Please enter the save path',
                style=dialog_style
            )
            app.current_buffer.insert_text(os.path.normpath(os.path.join(cwd, 'new_save.calc')))
            save_path = app.run()
        if save_path:
            save(save_path)

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

# atexit.register(onexit)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CLI Calculator')
    parser.add_argument('-d', '--debug', action='store_true', help='prints abstract syntax trees for inputs')
    args = parser.parse_args()

    # Find any saves and give the option to load them
    saves = find_saves(cwd)
    if len(saves) > 0:
        save_path = radiolist_dialog(
            title='Load',
            text='The following save files were found. Which would you like to load?',
            values=[(save, os.path.split(save)[1]) for save in saves],
            style=dialog_style
        ).run()
    else:
        save_path = None

    if save_path:
        interpreter = load(save_path)
    else:
        interpreter = Interpreter.Interpreter.get_global_interpreter(interface=True)
        
    current_line = 0
    print('Enter expression:')
    sys.setrecursionlimit(3000)
    line_end_pattern = re.compile(r';\s*$|\S$')

    # Create the promp session
    session = PromptSession()
    while True:
        # Get some input
        i = 0
        newline = True
        current_line += 1
        line_end = False

        # Catch any errors
        try:
            program = session.prompt('{}: '.format(current_line), key_bindings=bindings)
            if args.debug:
                AST = interpreter._get_AST(program)
                print(AST)
                result = interpreter.evaluate_AST(AST)
            else:
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
        
        # Save answers in a variable
        answers = interpreter.retrieve_value('ans')
        if result is None or type(result) == str:
            answers = np.array(answers.tolist() + [np.nan], dtype=object)
        else:
            answers = np.array(answers.tolist() + [result], dtype=object)
        answers = interpreter.set_value('ans', answers, force=True)
    onexit(save_path)