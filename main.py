#!/usr/bin/python

"""
main file of RaBit client integrated with gui
"""

from src.app import Application

import sys
import tracemalloc


def main():
    # run application
    Application()


if __name__ == '__main__':
    tracemalloc.start()

    if sys.version_info[0] != 3 or sys.version_info[1] < 10:
        raise Exception("Wrong Python version! Use version 3.10 and above.")

    main()
    sys.exit()
