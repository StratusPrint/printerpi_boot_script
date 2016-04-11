#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import thread
import datetime

class Log(object):
    """Log is a class that allows easy logging and printing
    in a very easy fashion"""

    _flock = thread.allocate_lock()

    def __init__(self, fname=".log", print_enabled=False):

        self._print = print_enabled
        self._fname = fname
        if not os.path.isfile(self._fname):
            try:
                f = open(self._fname, "a")
            except IOError:
                print("Unable to create log file."
                      + " Please make sure nothing named "
                      + self._fname 
                      + " exists.")
            f.close()


    def log(self, message):
        """logs the message. If printing is enabled,
        will also print to stdout. Prepends a timestamp
        when writing to the log
        """

        message = str(datetime.datetime.now()) + ": " + str(message)
        if self._print:
            print(message)
        with self._flock:

            with open(self._fname, 'r') as f:
                lines = f.readlines()
                if len(lines) > 2000:
                    lines = lines[1000:]
                lines.append(message + "\n")
            with open(self._fname, 'w+') as f:
                f.writelines(lines)

if __name__ == "__main__":
    log = Log()
    for i in range(100):
        log.log(i)
