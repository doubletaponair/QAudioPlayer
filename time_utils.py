"""Time formatting helpers for display and spoken announcements."""


def _split(ms):
    if ms is None or ms < 0:
        ms = 0
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return hours, minutes, seconds


def format_time_clock(ms):
    """Format ms as MM:SS or H:MM:SS - for on-screen display."""
    hours, minutes, seconds = _split(ms)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_time_verbal(ms):
    """Format ms as spoken phrase, e.g. '3 minutes 42 seconds'.

    Units are always spelled out so the screen reader says them as words
    instead of punctuation (e.g. 'colon').
    """
    hours, minutes, seconds = _split(ms)
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)
