"""
Main entry point for running as a script
"""

import subprocess
import sys
import time


from . import interactive_mode as im

TEST_SAVE_FILE = b'uranium_test.json'

URANIUM_TEST = (
    b'uranium\n',
    b'1\n',
    b'add-recipe-goal\n',
    b'0\n',
    b'1\n',
    b'add-recipe-shortage\n',
    b'2\n',
    b'0\n',
    b'scale-item\n',
    b'6\n',
    b'2100\n',
    b'save\n',
    TEST_SAVE_FILE+b'\n',
    b'print\n',
)

def simple_test():
    # TODO Move to tests
    proc = subprocess.Popen(
        [sys.executable, '-m', 'satisfactory_recipes.interactive_mode'],
        stdin=subprocess.PIPE,
    )
    for thing in (
        b'pluton\n',
        b'0\n',
        b'add-recipe-goal\n',
        b'0\n',
        b'1\n',
        b'add-recipe-shortage\n',
        b'0\n',
        b'0\n',
        b'print\n',
    ):
        time.sleep(0.5)
        print('   ---->', thing)
        proc.stdin.write(thing)
    proc.stdin.write(b'exit')
    proc.communicate()


def main():
    # if len(sys.argv) > 1:
    #     simple_test()
    # else:
    #     import os
    #     os.system('cls')
    im.main()#TEST_SAVE_FILE)

if __name__ == '__main__':
    main()
