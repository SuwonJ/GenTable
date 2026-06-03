# 화면 패키지는 표시용 변환 함수를 공개한다.
# 시간표 후보를 표 형태로 바꾸는 함수만 외부에 노출한다.
# 화면 세션 상태 조작은 별도 상태 파일에서 직접 가져다 쓴다.
# 공개 목록은 표시 계층의 공개 범위를 명확하게 유지한다.
# 생성 엔진은 이 패키지를 알지 못해 도메인 로직과 화면 로직이 분리된다.
from src.presentation.dataframe_exporter import timetable_to_frame

__all__ = ["timetable_to_frame"]
