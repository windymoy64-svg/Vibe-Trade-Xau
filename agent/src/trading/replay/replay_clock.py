from datetime import datetime, timezone

class ReplayClock:
    def __init__(self, start=None): self._time = _aware(start) if start else None
    def current_time(self):
        if self._time is None: raise RuntimeError("replay clock has not advanced")
        return self._time
    def advance(self, timestamp=None):
        value = _aware(timestamp)
        if self._time is not None and value < self._time: raise ValueError("clock cannot move backwards")
        self._time = value; return value
def _aware(value):
    if not isinstance(value, datetime): raise TypeError("clock time must be datetime")
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)