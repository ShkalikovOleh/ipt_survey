import json
from enum import Flag, auto
from dataclasses import dataclass


class Role(Flag):
    lecturer = auto()
    practice = auto()
    both = practice | lecturer


@dataclass
class Audience:
    year: int
    department: str
    is_elective: bool
    num_students: int

    def __post_init__(self):
        assert self.num_students > 0


@dataclass
class Course:
    name: str
    audiences: list[Audience]
    role: Role

    @property
    def total_num_students(self) -> int:
        return sum(map(lambda aud: aud.num_students, self.audiences))

    def __post_init__(self):
        assert len(self.name.split()) > 1


def parse_courses(
    courses_info: dict[str, str | int | bool], year: int, department: str
) -> dict[str, Course]:
    courses = {}
    for course_info in courses_info:
        name = course_info["name"]

        match course_info["role"]:
            case "Лектор":
                role = Role.lecturer
            case "Практик":
                role = Role.practice
            case "Лектор і практик":
                role = Role.both
            case _:
                raise AssertionError("Unknown role is provided")

        course = Course(
            name,
            [
                Audience(
                    year,
                    department,
                    course_info["is_elective"],
                    course_info["num_students"],
                )
            ],
            role,
        )

        if name in courses:
            raise AssertionError("Duplicated course")
        courses[name] = course

    return courses


def parse_teacher_json(path: str):
    with open(path, "r") as file:
        data = json.load(file)

    year = data["year"]
    assert year in range(1, 5)

    department = data["department"]

    teachers = {
        info["name"]: parse_courses(info["courses"], year, department)
        for info in data["teachers"]
    }

    return year, department, teachers


def add_to_db(
    teacher_db: dict[str, dict[str, Course]],
    new_data: dict[str, dict[str, Course]],
):
    for teacher_name, courses in new_data.items():
        curr_teacher_courses = teacher_db.get(teacher_name, None)
        if curr_teacher_courses is not None:
            for course_name, course in courses.items():
                curr_course = curr_teacher_courses.get(course_name, None)
                if course_name in curr_teacher_courses:
                    curr_course.audiences.extend(course.audiences)
                    curr_course.role |= course.role
                else:
                    curr_teacher_courses[course_name] = course
        else:
            teacher_db[teacher_name] = courses


def load_teacher_db(paths: list[str]):
    teacher_db = {}
    for path in paths:
        year, dep, data = parse_teacher_json(path)
        add_to_db(teacher_db, data, year, dep)

    return teacher_db


def nan_or(arg1, arg2):
    if arg1 is None:
        return arg2
    return arg1 | arg2


def get_teacher_with_max_role_for_year(
    teacher_db: dict[str, dict[str, Course]], year: int
):
    results = {}
    for teacher_name, courses in teacher_db.items():
        max_role = None
        for course_name, course in courses.items():
            for aud in course.audiences:
                if year == aud.year:
                    max_role = nan_or(max_role, course.role)
        if max_role is not None:
            results[teacher_name] = max_role
    return results
