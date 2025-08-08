import operator
from collections.abc import Callable, Collection, Iterable, Iterator
from dataclasses import dataclass
from enum import Enum, Flag, auto
from functools import reduce
from itertools import chain
from typing import Optional
from warnings import warn


class Role(Flag):
    LECTURER = auto()
    PRACTICE = auto()
    BOTH = PRACTICE | LECTURER

    def __str__(self):
        return _role_to_str[self]


_role_to_str = {
    Role.LECTURER: "Лектор",
    Role.PRACTICE: "Практик",
    Role.BOTH: "Лектор і практик",
}
_str_to_role = {v: k for k, v in _role_to_str.items()}


class Speciality(Enum):
    APPLIED_MATH = 0
    APPLIED_PHYSICS = 1
    CYBERSECURITY = 2

    def __str__(self):
        return _op_to_str[self]


_op_to_str = {
    Speciality.APPLIED_MATH: "Прикладна математика",
    Speciality.APPLIED_PHYSICS: "Прикладна фізика",
    Speciality.CYBERSECURITY: "Кібербезпека",
}


@dataclass
class Audience:
    group: str
    role: Role
    is_elective: bool = False

    @property
    def speciality(self):
        letter_to_op = {
            "ФІ": Speciality.APPLIED_MATH,
            "ФФ": Speciality.APPLIED_PHYSICS,
            "ФБ": Speciality.CYBERSECURITY,
            "ФE": Speciality.CYBERSECURITY,
        }
        return letter_to_op[self.group[:1]]

    @property
    def enrollment_year(self) -> str:
        return self.group.split("-")[1][0]

    @property
    def stream(self) -> tuple[Speciality, str]:
        return (self.speciality, self.enrollment_year)


@dataclass
class Course:
    name: str
    audiences: list[Audience]

    @property
    def specialities(self) -> Collection[Speciality]:
        return set(aud.speciality for aud in self.audiences)

    @property
    def groups(self) -> Collection[str]:
        return set(aud.group for aud in self.audiences)

    @property
    def enrollment_years(self) -> Collection[str]:
        return set(aud.enrollment_year for aud in self.audiences)

    @property
    def streams(self) -> Collection[tuple[Speciality, str]]:
        return set(aud.stream for aud in self.audiences)

    @property
    def roles(self) -> Collection[Role]:
        return set(aud.role for aud in self.audiences)

    @property
    def max_role(self) -> Role:
        return reduce(operator.or_, [aud.role for aud in self.audiences])


def nan_or(opt_role: Optional[Role], role: Role) -> Role:
    if opt_role:
        return opt_role | role
    else:
        return role


@dataclass
class Teacher:
    name: str
    courses: list[Course]
    student_per_group: dict[str, int]

    @property
    def num_students(self) -> int:
        return sum(self.student_per_group.values())

    @property
    def specialities(self) -> Collection[Speciality]:
        return set(chain.from_iterable(c.specialities for c in self.courses))

    @property
    def groups(self) -> Collection[str]:
        return self.student_per_group.keys()

    @property
    def enrollment_years(self) -> Collection[str]:
        return set(chain.from_iterable(c.enrollment_years for c in self.courses))

    @property
    def streams(self) -> Collection[tuple[Speciality, str]]:
        return set(chain.from_iterable(c.streams for c in self.courses))

    @property
    def max_role(self) -> Role:
        return reduce(operator.or_, [c.max_role for c in self.courses])

    def __max_role_for(self, predicate: Callable[[Audience], bool]) -> Optional[Role]:
        all_audiences = (aud for c in self.courses for aud in c.audiences)
        return reduce(nan_or, filter(predicate, all_audiences), None)

    def max_role_for_group(self, group: str) -> Optional[Role]:
        return self.__max_role_for(lambda aud: aud.group == group)

    @property
    def roles(self) -> Collection[Role]:
        all_roles = set()
        all_audiences = list(aud for c in self.courses for aud in c.audiences)
        for group in self.groups:
            if len(all_roles) == 3:
                break

            group_auds = list(filter(lambda aud: aud.group == group, all_audiences))
            mandatory_auds = filter(lambda aud: not aud.is_elective, group_auds)
            role = reduce(nan_or, (aud.role for aud in mandatory_auds), None)
            if role:
                all_roles.add(role)
            if role != Role.BOTH:
                elective_auds_new_roles = filter(
                    lambda aud: aud.is_elective and aud.role != role, group_auds
                )
                for aud in elective_auds_new_roles:
                    all_roles.add(aud.role)

        return all_roles

    def max_role_for_spec(self, speciality: Speciality) -> Optional[Role]:
        return self.__max_role_for(lambda aud: aud.speciality == speciality)

    def max_role_for_enrollment_year(self, year: str) -> Optional[Role]:
        return self.__max_role_for(lambda aud: aud.enrollment_year == year)

    def max_role_for_stream(self, speciality: Speciality, year: str) -> Optional[Role]:
        return self.__max_role_for(
            lambda aud: aud.speciality == speciality and aud.enrollment_year == year
        )

    def num_students_for_spec(self, speciality: Speciality) -> int:
        num_students = 0
        for course in self.courses:
            for aud in course.audiences:
                if aud.speciality == speciality:
                    num_students += self.student_per_group[aud.group]
        return num_students

    def num_students_for_enrollment_year(self, year: str) -> int:
        num_students = 0
        for course in self.courses:
            for aud in course.audiences:
                if aud.enrollment_year == year:
                    num_students += self.student_per_group[aud.group]
        return num_students

    def num_students_for_stream(self, speciality: Speciality, year: str) -> int:
        num_students = 0
        for course in self.courses:
            for aud in course.audiences:
                if aud.speciality == speciality and aud.enrollment_year == year:
                    num_students += self.student_per_group[aud.group]
        return num_students

    def __post_init__(self):
        assert len(self.name.split()) == 3
        assert self.num_students > 0


class TeacherDB:
    def __init__(self):
        self.db: dict[str, Teacher] = {}

    def append_from_group_dict(self, info: dict) -> None:
        """
        The expected structure of the dict:
        {
        "group": "ФІ-81",
        "teachers": [{
                "name": "Surname Name MiddleName",
                "courses": [
                    {
                        "name": "Дискретна математика 1",
                        "is_elective": false,
                        "role": "Лектор"
                    }
                ],
                "num_students": 10
            }]
        }
        """
        group = info["group"]
        for teacher_info in info["teachers"]:
            teacher_name = teacher_info["name"]
            total_students = teacher_info["num_students"]

            course2audience: dict[str, Audience] = {}
            for course_info in teacher_info["courses"]:
                course_name = course_info["name"]
                course2audience[course_name] = Audience(
                    group=group,
                    role=_str_to_role[course_info["role"]],
                    is_elective=course_info.get("is_elective", False),
                )

            if teacher_name in self.db:
                teacher = self.db[teacher_name]
                if group in teacher.groups:
                    warn(
                        f"Info about group {group} for {teacher_name} has already been added before"
                    )

                teacher.student_per_group[group] = total_students
                for course in teacher.courses:
                    if course.name in course2audience:
                        if group in course.groups:
                            raise ValueError(
                                f"Course {course.name} for group {group} has already been added"
                            )
                        course.audiences.append(course2audience[course.name])
                        del course2audience[course.name]
                for new_course_name, audience in course2audience.items():
                    teacher.courses.append(
                        Course(name=new_course_name, audiences=[audience])
                    )
            else:
                courses = [
                    Course(name=name, audiences=[aud])
                    for name, aud in course2audience.items()
                ]
                self.db[teacher_name] = Teacher(
                    name=teacher_name,
                    courses=courses,
                    student_per_group={group: total_students},
                )

    def __getitem__(self, name: str) -> Teacher:
        return self.db[name]

    def get_all_groups(self) -> Iterable[str]:
        return set(chain.from_iterable(teacher.groups for teacher in self))

    def __filter_by(self, predicate: Callable[[Audience], bool]) -> Iterable[Teacher]:
        for teacher in self.db.values():
            filtered_courses = []
            groups = set()
            for course in teacher.courses:
                auds = list(filter(predicate, course.audiences))
                if auds:
                    filtered_courses.append(Course(course.name, audiences=auds))
                    groups = groups.union(aud.group for aud in auds)
            if filtered_courses:
                new_num_stud = {g: teacher.student_per_group[g] for g in groups}
                yield Teacher(teacher.name, filtered_courses, new_num_stud)

    def filter_by_group(self, group: str) -> Iterable[Teacher]:
        yield from self.__filter_by(lambda aud: aud.group == group)

    def filter_by_speciality(
        self, speciality: Speciality
    ) -> Iterable[tuple[Teacher, Iterable[Role]]]:
        yield from self.__filter_by(lambda aud: aud.speciality == speciality)

    def filter_by_stream(self, speciality: Speciality, year: str) -> Iterable[Teacher]:
        yield from self.__filter_by(
            lambda aud: aud.speciality == speciality and aud.enrollment_year == year
        )

    def __iter__(self) -> Iterator[Teacher]:
        return iter(self.db.values())
