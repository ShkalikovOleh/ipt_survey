from collections import defaultdict
import json
from enum import Enum, Flag, auto
from dataclasses import dataclass

import numpy as np
import pandas as pd


class Role(Flag):
    lecturer = auto()
    practice = auto()
    both = practice | lecturer


role_to_str = {
    Role.lecturer: "Лектор",
    Role.practice: "Практик",
    Role.both: "Лектор і практик",
}


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


class PreciseEnum(Enum):
    MANY_ELECTIVES = 0
    ONE_ELECTIVES = 1
    PRECISE = 2


enum2bool = {
    PreciseEnum.MANY_ELECTIVES: False,
    PreciseEnum.ONE_ELECTIVES: True,
    PreciseEnum.PRECISE: True,
}


def calculate_total_num_students_for_year(
    teacher_db: dict[str, dict[str, Course]], year: int
):
    total_nums = defaultdict(lambda: 0)
    precise_res = defaultdict(lambda: True)
    for teacher_name, courses in teacher_db.items():
        num_by_dep = {}
        precise_by_dep = {}
        for course in courses.values():
            for aud in course.audiences:
                if aud.year != year:
                    continue

                dep = aud.department
                if dep not in num_by_dep:  # no prev info
                    num_by_dep[dep] = aud.num_students
                    precise_by_dep[dep] = (
                        PreciseEnum.PRECISE
                        if aud.is_elective
                        else PreciseEnum.ONE_ELECTIVES
                    )
                elif precise_by_dep == PreciseEnum.PRECISE:  # already known
                    continue
                elif not aud.is_elective:
                    num_by_dep[dep] = aud.num_students
                    precise_by_dep[dep] = PreciseEnum.PRECISE
                else:
                    num_by_dep[dep] = max(aud.num_students, num_by_dep[dep])
                    precise_by_dep[dep] = PreciseEnum.MANY_ELECTIVES

        if num_by_dep:  # not empty
            is_precise = np.logical_and.reduce(
                [enum2bool[it] for it in (precise_by_dep.values())]
            )
            total_nums[teacher_name] = sum(num_by_dep.values())
            precise_res[teacher_name] = is_precise

    return total_nums, precise_res


def build_question2item_id_map(id: str, form_service):
    cur_form = form_service.forms().get(formId=id).execute()

    def is_question(item) -> bool:
        return "questionItem" in item

    questions = filter(is_question, cur_form["items"])

    mapping = {
        item["title"]: item["questionItem"]["question"]["questionId"]
        for item in questions
    }
    return mapping


def response_json_to_pandas(
    responses,
    teacher_name: str,
    year: int,
    question2id: dict[str, str],
    column2parser: list[str],
) -> pd.DataFrame:
    data = {}
    N = len(responses["responses"])
    data["name"] = [teacher_name] * N
    data["year"] = [year] * N

    for column, parser in column2parser.items():
        qId = question2id.get(column)
        values = []
        if qId is not None:
            for response in responses["responses"]:
                answer = response["answers"].get(qId)
                if answer:
                    values.append(parser(answer["textAnswers"]["answers"][0]["value"]))
                else:
                    values.append(np.nan)
        else:
            values = [np.nan] * len(responses["responses"])

        data[column] = values

    df = pd.DataFrame.from_dict(data)
    return df
