"""
Render 서버가 UTC로 돌아가서(로컬 개발 PC는 KST), `datetime.datetime.now()`를 그냥 쓰면
서버에서는 시각이 9시간 밀려서 나옵니다 - 그래서 배포본에서는 낮에도 항상 새벽 시간대로
계산되어 음식점 혼잡도/대기시간이 하나도 안 뜨는 버그가 있었습니다 (로컬에서는 멀쩡해서
처음엔 몰랐음). 시스템 타임존에 기대지 않고 항상 한국 시간을 명시적으로 씁니다.
"""
import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime.datetime:
    return datetime.datetime.now(KST)


def from_epoch_ms_kst(epoch_ms: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=KST)
