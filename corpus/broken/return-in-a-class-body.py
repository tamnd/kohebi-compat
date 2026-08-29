class Settings:
    """Values read once at import time."""

    retries = 3

    if retries > 0:
        return retries

    def backoff(self):
        return self.retries * 2
