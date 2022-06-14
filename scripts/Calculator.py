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
import yaml
import argparse
import numpy as np
from Scope import NoNewline
from Serialize import ProgramEncoder, json_program_obj_hook
from prompt_toolkit import PromptSession
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import input_dialog, checkboxlist_dialog, radiolist_dialog
from prompt_toolkit.styles import Style

CWD = os.path.dirname(os.path.realpath(__file__))
SAVE_DIR = os.path.join(os.path.split(CWD)[0], 'saves')
EXIT_DIALOG = True
DIALOG_STYLE = Style.from_dict({
    'dialog':             'bg:#88ff88',
    'dialog frame.label': 'bg:#ffffff #000000',
    'dialog':        'bg:#000000',
})

def find_files(*sources, name=None, extension=None):
    '''
    Recursively retrieve files from the given source directories whose names and/or extensions (full)match the given patterns.
    name: string or regex pattern
    extension: string or regex pattern
    Returns a DirEntry generator
    '''
    # Compile regexes if needed
    if name is None:
        name = re.compile(r'.*')
    elif type(name) is not re.Pattern:
        name = re.compile(name)
    if extension is None:
        extension = re.compile(r'.*')
    elif type(extension) is not re.Pattern:
        extension = re.compile(extension)

    # Keep track of the sources already scanned and the files already found
    memo_table = {}

    def find_files_helper(*sources):
        # Search through each source directoty
        for source in sources:
            # Get all of the contents of the source directory and search them
            entries = os.scandir(source)
            for entry in entries:
                # Check if the entry has already been scanned or matched
                normed = os.path.normpath(entry.path)
                if normed not in memo_table:
                    memo_table[normed] = True
                    # If the current entry is itself a directory, search it recursively
                    if entry.is_dir():
                        yield from find_files_helper(entry)

                    # Otherwise yield entries whose name matches the name pattern and whose extension matches the extension pattern
                    else:
                        # Return only entries that have not already been found
                        filename, fileext = os.path.splitext(entry.name)
                        if name.fullmatch(filename) is not None and \
                        extension.fullmatch(fileext) is not None:
                            yield entry
            entries.close()
    return find_files_helper(*sources)

def find_saves(path):
    dirs = os.listdir(path)
    saves = []
    for f in dirs:
        if os.path.isfile(os.path.join(SAVE_DIR, f)) and os.path.splitext(f)[1] == '.calc':
            saves.append(os.path.join(SAVE_DIR, f))
    saves = sorted(saves, key=os.path.getmtime, reverse=True)
    return saves

def load(path):
    if os.path.isfile(path):
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
    global EXIT_DIALOG
    # Give the option to save the scope before exiting
    if EXIT_DIALOG:
        NEW_SAVE = 1
        EXIT_DIALOG = False

        values = []
        if load_path:
            values = [
                (load_path, os.path.split(load_path)[1])
            ]
        values.append((NEW_SAVE, 'New save file'))

        # Give the user the option to save their work
        save_path = radiolist_dialog(
            title='Save',
            text='Would you like to save your work?',
            values=values,
            style=DIALOG_STYLE
        ).run()
        if save_path == NEW_SAVE:
            app = input_dialog(
                title='New save',
                text='Please enter the save path',
                style=DIALOG_STYLE
            )
            app.current_buffer.insert_text(os.path.normpath(os.path.join(SAVE_DIR, 'new_save.calc')))
            save_path = app.run()
        if save_path:
            # Repeat the user prompt as many times as necessary if the given path is incorrect
            done_saving = False
            while not done_saving:
                # If the given save path is not a file, give the user the option to correct it
                if os.path.split(save_path)[1] == '':
                    app = input_dialog(
                        title='New save',
                        text='Given path was not to a file. Please enter a corrected save path',
                        style=DIALOG_STYLE
                    )
                    app.current_buffer.insert_text(save_path)
                    save_path = app.run()

                    # If the user did not provide a save path, break out of the loop
                    if not save_path:
                        done_saving = True
                else:
                    # Add the proper extension if necessary and save
                    save_name, save_ext = os.path.splitext(save_path)
                    if save_ext != '.calc':
                        save_path = '{}.calc'.format(save_name)
                    save(save_path)
                    done_saving = True

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
    parser.add_argument('-c', '--config', help='Name of the config yaml file to use', default='../config.yml')
    args = parser.parse_args()

    # Retrieve save files from configuration file if possible, falling back to the default save path if necessary
    saves = []
    config_path = os.path.join(CWD, args.config)
    if os.path.isfile(config_path):
        config = yaml.safe_load(open(config_path, 'r'))
        basepath = os.path.dirname(config_path)
        if 'dirs' in config:
            save_dirs = [os.path.join(basepath, save_dir) for save_dir in config['dirs']] + [SAVE_DIR]
        else:
            save_dirs = [SAVE_DIR]
        saves = list(find_files(*save_dirs, extension=r'\.calc'))

    # Find any saves and give the option to load them
    # saves = find_saves(SAVE_DIR)
    if len(saves) > 0:
        save_path = radiolist_dialog(
            title='Load',
            text='The following save files were found. Which would you like to load?',
            values=[(save, os.path.split(save)[1]) for save in saves],
            style=DIALOG_STYLE
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
            result = None
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
        answers = interpreter.get_root_scope().set_value('ans', answers, force=True)
    onexit(save_path)