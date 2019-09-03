# -*- coding: utf-8 -*-

""" Module summary description.

More detailed description.
"""

# __all__ = []
# __version__ = '0.1'
from time import sleep

from utils.sys.io import LogFile

__author__ = 'Benjamin Pillot'
__copyright__ = 'Copyright 2018, Benjamin Pillot'
__email__ = 'benjaminpillot@riseup.net'

from contextlib import contextmanager
import ctypes
import io
import os
import sys
import tempfile

libc = ctypes.CDLL(None)
c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')


@contextmanager
def stdout_redirector(stream):
    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stdout_fd = sys.stdout.fileno()

    def _redirect_stdout(to_fd):
        """Redirect stdout to the given file descriptor."""
        # Flush the C-level buffer stdout
        libc.fflush(c_stdout)
        # Flush and close sys.stdout - also closes the file descriptor (fd)
        sys.stdout.close()
        # Make original_stdout_fd point to the same file as to_fd
        os.dup2(to_fd, original_stdout_fd)
        # Create a new sys.stdout that points to the redirected fd
        sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, 'wb'))

    # Save a copy of the original stdout fd in saved_stdout_fd
    saved_stdout_fd = os.dup(original_stdout_fd)
    try:
        # Create a temporary file and redirect stdout to it
        tfile = tempfile.TemporaryFile(mode='w+b')
        _redirect_stdout(tfile.fileno())
        # Yield to caller, then redirect stdout back to the saved fd
        yield
        _redirect_stdout(saved_stdout_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stdout_fd)


@contextmanager
def stderr_redirector(stream):
    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stderr_fd = sys.stderr.fileno()

    def _redirect_stderr(to_fd):
        """Redirect stdout to the given file descriptor."""
        # Flush the C-level buffer stdout
        libc.fflush(c_stderr)
        # Flush and close sys.stdout - also closes the file descriptor (fd)
        sys.stderr.close()
        # Make original_stdout_fd point to the same file as to_fd
        os.dup2(to_fd, original_stderr_fd)
        # Create a new sys.stdout that points to the redirected fd
        sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, 'wb'))

    # Save a copy of the original stdout fd in saved_stdout_fd
    saved_stderr_fd = os.dup(original_stderr_fd)
    tfile = tempfile.TemporaryFile(mode='w+b')
    try:
        # Create a temporary file and redirect stdout to it
        _redirect_stderr(tfile.fileno())
        # Yield to caller, then redirect stdout back to the saved fd
        yield
        _redirect_stderr(saved_stderr_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stderr_fd)


if __name__ == "__main__":

    print("blabla\r\n")
    print("new line")
    # log_file = LogFile()
    #
    # with log_file.stderr_redirector():
    #     print('foobar')
    #     print(12)
    #     try:
    #         m = log_file.h
    #     except AttributeError:
    #         pass
    #     libc.puts(b'this comes from C')
    #     os.system('echo and this is from echo')
    # print('Got stdout: "{0}"'.format(f.getvalue().decode('utf-8')))
