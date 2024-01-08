import signal


class Timeout:
    """A timeout class that can be used as a context manager.

    Example usage:

        with Timeout(5):
            # do stuff

    If the code inside the context manager takes longer than 5 seconds to
    execute, a TimeoutError will be raised.
    """

    def __init__(self, seconds: int, throw_exception: bool = False):
        self.seconds = seconds
        self.throw_exception = throw_exception

    def handle_timeout(self, signum, frame):
        raise TimeoutError("Timed out after {} seconds".format(self.seconds))

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)
        return not self.throw_exception


class TimeoutError(Exception):
    """Timeout error class."""

    pass
