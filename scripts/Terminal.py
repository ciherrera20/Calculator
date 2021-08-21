# #!/usr/bin/env python 
import Interpreter2
import sys
import traceback
from Scope2 import NoNewline
import re
import msvcrt

CTRL_C = b'\x03'
BACKSPACE = b'\x08'
ESC = b'\x1b'
UP = b'\xe0H'
DOWN = b'\xe0P'
RIGHT = b'\xe0M'
LEFT = b'\xe0K'
HOME = b'\xe0G'
END = b'\xe0O'
PAGEUP = b'\xe0I'
PAGEDOWN = b'\xe0Q'
ENTER = b'\r'
DELETE = b'\xe05'

CTRL_CHARS = [CTRL_C, BACKSPACE, ESC, UP, DOWN, RIGHT, LEFT, HOME, END, PAGEUP, PAGEDOWN, ENTER, DELETE]

class Terminal():
    def __init__(self):
        self._reset_lines()

    def _reset_lines(self):
        self._lines = ['']
        self._curr_ln = 0
        self._curr_col = 0

    def read(self):
        self._reset_lines()
        while True:
            key = msvcrt.getch()
            while msvcrt.kbhit() > 0:
                key += msvcrt.getch()
            if key == CTRL_C:
                break
            elif key == UP:
                if self._curr_ln > 0:
                    print('\033[1A', end='')
                    self._curr_ln -= 1
            elif key == DOWN:
                if self._curr_ln < len(self._lines) - 1:
                    print('\033[1B', end='')
                    self._curr_ln += 1
            elif key == LEFT:
                if self._curr_col > 0:
                    print('\033[1D', end='')
                    self._curr_col -= 1
            elif key == RIGHT:
                if self._curr_col < len(self._lines[self._curr_ln]):
                    print('\033[1C', end='')
                    self._curr_col += 1
            elif key == ENTER:
                print('\n', end='')
                self._curr_ln += 1
                self._lines = self._lines[:self._curr_ln] + ['']
            elif key in CTRL_CHARS:
                pass
            else:
                try:
                    # Convert to character
                    char = str(key, 'utf-8')

                    # Insert the character
                    self._insert_char(char)

                    # Update the column number
                    self._curr_col += 1
                except UnicodeDecodeError:
                    print(key, end='')
                    break
        return '\n'.join(self._lines)

    def _insert_char(self, char):
        # Insert the character into the current line
        line = self._lines[self._curr_ln]
        line = line[:self._curr_col] + char + line[self._curr_col:]
        self._lines[self._curr_ln] = line

        # Print from the character up to the end of the current line
        print(line[self._curr_col:], end='')

        # Move cursor back to its previous position
        print('\033[{}D'.format(len(line[self._curr_col + 1:])), end='')

if __name__ == '__main__':
    terminal = Terminal()
    print('\nYou entered:\n' + terminal.read())