from typing import Optional

from src.forms.generation import Granularity
from src.teachers_db import Group, Speciality, Stream, TeacherDB


def get_filter_func(
    form_granularity: Granularity,
    requested_granularity: Granularity,
    query: Optional[str | Speciality | Stream],
    db: TeacherDB,
):
    match (requested_granularity, form_granularity):
        case (Granularity.GROUP, Granularity.GROUP):

            def filter_func(teacher_name, form_info):
                return form_info["group"] == query

        case (Granularity.GROUP, Granularity.STREAM):

            def filter_func(teacher_name, form_info):
                req_group = Group(query)
                stream = Stream(Speciality(form_info["speciality"]), form_info["year"])
                return (
                    req_group.stream == stream and req_group in db[teacher_name].groups
                )

        case (Granularity.GROUP, Granularity.SPECIALITY):

            def filter_func(teacher_name, form_info):
                req_group = Group(query)
                return (
                    Speciality(form_info["speciality"]) == req_group.speciality
                    and req_group in db[teacher_name].groups
                )

        case (Granularity.GROUP, Granularity.FACULTY):

            def filter_func(teacher_name, form_info):
                req_group = Group(query)
                return req_group in db[teacher_name].groups

        case (Granularity.STREAM, Granularity.GROUP):

            def filter_func(teacher_name, form_info):
                return Group(form_info["group"]).stream == query

        case (Granularity.STREAM, Granularity.STREAM):

            def filter_func(teacher_name, form_info):
                return (
                    form_info["speciality"] == query.speciality
                    and form_info["year"] == query.year
                )

        case (Granularity.STREAM, Granularity.SPECIALITY):

            def filter_func(teacher_name, form_info):
                return (
                    Speciality(form_info["speciality"]) == query.speciality
                    and query in db[teacher_name].streams
                )

        case (Granularity.STREAM, Granularity.FACULTY):

            def filter_func(teacher_name, form_info):
                return query in db[teacher_name].streams

        case (Granularity.SPECIALITY, Granularity.GROUP):

            def filter_func(teacher_name, form_info):
                return Group(form_info["group"]).speciality == query

        case (Granularity.SPECIALITY, Granularity.STREAM):

            def filter_func(teacher_name, form_info):
                stream = Stream(Speciality(form_info["speciality"]), form_info["year"])
                return stream.speciality == query

        case (Granularity.SPECIALITY, Granularity.SPECIALITY):

            def filter_func(teacher_name, form_info):
                return form_info["speciality"] == query

        case (Granularity.SPECIALITY, Granularity.FACULTY):

            def filter_func(teacher_name, form_info):
                return query in db[teacher_name].specialities

        case (Granularity.FACULTY, _):

            def filter_func(teacher_name, form_info):
                return True

    return filter_func


def fitler_urls(
    forms_granularity: Granularity,
    requested_granularity: Granularity,
    query: Optional[str | Speciality | Stream],
    forms_dict: dict[str, list[dict[str, str]]],
    db: TeacherDB,
):
    filter_func = get_filter_func(
        form_granularity=forms_granularity,
        requested_granularity=requested_granularity,
        query=query,
        db=db,
    )
    for teacher_name, forms in forms_dict.items():
        for form in forms:
            if filter_func(teacher_name, form):
                yield (teacher_name, form["resp_url"])


def get_max_student_for_granularity(
    granularity: Granularity,
    query: Optional[str | Speciality | Stream],
    db: TeacherDB,
    teacher_name: str,
):
    teacher = db[teacher_name]
    match granularity:
        case Granularity.GROUP:
            max_num_responses = teacher.num_students_for_group(query)
        case Granularity.STREAM:
            max_num_responses = teacher.num_students_for_stream(query)
        case Granularity.SPECIALITY:
            max_num_responses = teacher.num_students_for_spec(query)
        case Granularity.FACULTY:
            max_num_responses = teacher.num_students

    return max_num_responses
