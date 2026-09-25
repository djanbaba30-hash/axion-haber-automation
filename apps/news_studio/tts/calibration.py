import json

from ..config import BASE_CPS, BASE_SPEED, CALIBRATION_PATH


def key(voice_id: str, speed: float) -> str:
    return f"{voice_id}|{speed:.2f}"


def load() -> dict[str,float]:
    try:
        data=json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        return {str(k):float(v) for k,v in data.items() if float(v)>0}
    except (OSError,ValueError,TypeError):
        return {}


def save(data: dict[str,float]) -> None:
    try:
        CALIBRATION_PATH.parent.mkdir(parents=True,exist_ok=True)
        CALIBRATION_PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    except OSError:
        pass


def cps(data: dict[str,float], voice_id: str, speed: float) -> float:
    return data.get(key(voice_id,speed), BASE_CPS*(speed/BASE_SPEED))


def estimate(data, voice_id, speed, duration_range):
    value=cps(data,voice_id,speed)
    lo,hi=duration_range
    return round(lo*value), round(((lo+hi)/2)*value), round(hi*value), value


def update(data, voice_id, speed, chars, duration_seconds):
    if duration_seconds<=0 or chars<=0: return data
    k=key(voice_id,speed); observed=chars/duration_seconds; old=data.get(k)
    data[k]=observed if not old else old*0.70+observed*0.30
    save(data)
    return data
