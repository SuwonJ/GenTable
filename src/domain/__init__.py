# 도메인 패키지는 시간표 생성에 필요한 핵심 모델을 공개한다.
# 과목, 강의, 시간 슬롯, 학생 프로필, 시간표 객체를 한곳에서 가져올 수 있다.
# 수강대상 객체는 모델 내부에서 연결되어 수강 가능 여부 판정에 사용된다.
# 공개 목록은 다른 계층이 의존해도 되는 모델 범위를 제한한다.
# 도메인 모델은 화면 상태에 직접 의존하지 않는다.
from src.domain.models import CourseCategory, Lecture, Schedule, StudentProfile, Subject, TimeSlot

__all__ = ["CourseCategory", "Lecture", "Schedule", "StudentProfile", "Subject", "TimeSlot"]
