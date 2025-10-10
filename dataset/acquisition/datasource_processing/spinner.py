import itertools
import sys
import threading
import time


class Spinner:
    def __init__(self):
        self.spinner_chars = ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠧", "⠇", "⠏", "⠍"]
        self.spinner = itertools.cycle(self.spinner_chars)
        self.busy = False
        self.delay = 0.1
        self.spinner_visible = False
        self.thread = None

    def write_next(self):
        with self._screen_lock:
            if not self.spinner_visible:
                sys.stdout.write(next(self.spinner))
                self.spinner_visible = True
                sys.stdout.flush()

    def remove_spinner(self, cleanup=False):
        with self._screen_lock:
            if self.spinner_visible:
                sys.stdout.write('\b')
                self.spinner_visible = False
                if cleanup:
                    sys.stdout.write(' ')
                    sys.stdout.write('\b')
                sys.stdout.flush()

    def spinner_task(self):
        while self.busy:
            self.write_next()
            time.sleep(self.delay)
            self.remove_spinner()

    def __enter__(self):
        if sys.stdout.isatty():
            self._screen_lock = threading.Lock()
            self.busy = True
            self.thread = threading.Thread(target=self.spinner_task)
            self.thread.daemon = True
            self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if sys.stdout.isatty():
            self.busy = False
            time.sleep(self.delay)
            self.remove_spinner(cleanup=True)
            if self.thread:
                self.thread.join()