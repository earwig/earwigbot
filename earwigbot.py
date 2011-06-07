# -*- coding: utf-8  -*-

import time
from subprocess import *

def main():
    while 1:
        call(['python', 'core/main.py'])
        time.sleep(5) # sleep for five seconds between bot runs

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit("\nKeyboardInterrupt: stopping bot wrapper.")
