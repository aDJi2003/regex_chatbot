import re
from datetime import date

def fmt_number(value):
    if value is None:
        return "N/A"
    try:
        n = int(value)
        return f"{n:,}"
    except (ValueError, TypeError):
        return str(value)

def iso8601_duration_to_readable(duration: str):
    import re
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    m = pattern.match(duration or "")
    if not m:
        return duration or "N/A"
    hours, minutes, seconds = m.groups()
    h = int(hours) if hours else 0
    m_ = int(minutes) if minutes else 0
    s = int(seconds) if seconds else 0
    if h:
        return f"{h}:{m_:02d}:{s:02d}"
    else:
        return f"{m_}:{s:02d}"

def parse_video_arg_and_keyword(arg: str):
    arg = arg.strip()
    m = re.match(r'(\S+)\s+"(.+)"$', arg)
    if m:
        return m.group(1), m.group(2).strip()
    parts = arg.split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1].strip()
    return None, None

def parse_timestamp_to_seconds(ts: str) -> int:
    parts = ts.split(':')
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    elif len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    else:
        raise ValueError("Invalid timestamp format")

def seconds_to_hms(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    else:
        return f"{m}:{s:02d}"
