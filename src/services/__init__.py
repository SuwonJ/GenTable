# 서비스 패키지는 앱에서 호출하는 주요 유스케이스를 공개한다.
# 시간표 생성은 생성 서비스 파일의 공개 함수가 담당한다.
# 대체 강의 추천은 필요할 때 대체 추천 파일에서 직접 가져온다.
# 공개 목록은 기본 진입점을 시간표 생성으로 제한한다.
# 서비스 계층은 화면 입력을 엔진과 도메인 모델이 이해할 수 있게 변환한다.
from src.services.scheduler_service import generate_timetables

__all__ = ["generate_timetables"]
