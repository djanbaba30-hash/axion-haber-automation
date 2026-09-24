import time


def retry_transient(fn, attempts=3, base_delay=1.0):
    last=None
    for n in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last=exc
            name=type(exc).__name__.lower()
            msg=str(exc).lower()
            transient=any(x in name+msg for x in ("timeout","rate", "429", "connection", "502", "503", "504", "temporar"))
            if not transient or n==attempts-1:
                raise
            time.sleep(base_delay*(2**n))
    raise last
