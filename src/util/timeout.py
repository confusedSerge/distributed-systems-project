import signal


class Timeout:
    """A timeout class that can be used as a context manager.

    Example usage:

        with Timeout(5):
            # do stuff

    If the code inside the context manager takes longer than 5 seconds to
    execute, a TimeoutError will be raised, if throw_exception is set.
    """

    def __init__(self, seconds: int, throw_exception: bool = False):
        """Initializes the timeout class.

        Args:
            seconds (int): The number of seconds to wait before raising a TimeoutError.
            throw_exception (bool, optional): Whether to throw a TimeoutError or not. Defaults to False.
        """
        self.seconds: int = seconds
        self.throw_exception: int = throw_exception

    def _handle_timeout(self, signum, frame):
        raise TimeoutError("Timed out after {} seconds".format(self.seconds))

    def __enter__(self):
        signal.signal(signal.SIGALRM, self._handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)
        return not self.throw_exception
