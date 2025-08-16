from dataclasses import dataclass
from enum import Enum, StrEnum
from functools import total_ordering
from typing import Any, Optional

from googleapiclient.discovery import Resource

from src.teachers_db import Role, Teacher


class QuestionType(Enum):
    RATING_QUESTION = 0
    OPEN_QUESTION = 1


@total_ordering
class Granularity(StrEnum):
    GROUP = "group"
    STREAM = "stream"
    SPECIALITY = "speciality"
    FACULTY = "faculty"

    def __lt__(self, other):
        if isinstance(other, Granularity):
            return self._member_names_.index(self.name) > self._member_names_.index(
                other.name
            )
        raise NotImplementedError


@dataclass(frozen=True)
class Question:
    question: str
    description: str = ""
    required: bool = True
    type: QuestionType = QuestionType.RATING_QUESTION


def adapt_form_from_template(
    teacher: Teacher,
    forms_service: Resource,
    drive_service: Resource,
    template_id: str,
    dest_folder_id: str,
    insert_loc: Optional[int] = None,
    stats_granularity: Optional[Granularity] = None,
) -> tuple[str, str]:
    form_id = copy_form(teacher.name, drive_service, template_id, dest_folder_id)
    form = get_form(forms_service, form_id)

    max_loc = len(form["items"])
    section_itemids = [
        (i, item["itemId"])
        for i, item in enumerate(form["items"])
        if "pageBreakItem" in item
    ]  # [(loc, id)]
    assert len(section_itemids) == 3, "Expected 3 section for optional questions"

    requests = [
        {
            "updateFormInfo": {
                "info": {
                    "title": teacher.name,
                },
                "updateMask": "title",
            }
        }
    ]

    section_roles = [Role.PRACTICE, Role.LECTURER, Role.BOTH]
    roles = teacher.roles
    if len(roles) == 1:
        role = teacher.overall_role
        if not insert_loc:
            # find first choice question
            insert_loc = next(
                (
                    i
                    for i, item in enumerate(form["items"])
                    if "questionItem" in item
                    and "choiceQuestion" in item["questionItem"]["question"]
                ),
                max_loc,
            )

        idx_role = section_roles.index(role)
        start_sec_loc = section_itemids[idx_role][0]
        end_sec_loc = section_itemids[idx_role + 1][0] if idx_role < 2 else max_loc
        for loc in range(start_sec_loc + 1, end_sec_loc):
            move_item(loc, insert_loc, requests)
            insert_loc += 1

        redudant_sec_loc = section_itemids[0][0] + end_sec_loc - start_sec_loc - 1
        for i in range(redudant_sec_loc, max_loc):
            delete_item(
                redudant_sec_loc, requests
            )  # bug with location in GoogleFormsAPI (after every delete loc changes)
    else:
        options_to_nextid = {
            str(srole): item_id
            for srole, (_, item_id) in zip(section_roles, section_itemids)
            if srole in roles
        }
        append_branching_question(
            "Ким для вас був цей викладач?", options_to_nextid, requests
        )

        sections_to_delete = [
            i for i, srole in enumerate(section_roles) if srole not in roles
        ]
        for i in sections_to_delete:
            start_sec_loc = section_itemids[i][0]
            end_sec_loc = section_itemids[i + 1][0] if i < 2 else max_loc
            for _ in range(start_sec_loc, end_sec_loc):
                delete_item(
                    start_sec_loc + 1, requests
                )  # bug with location in GoogleFormsAPI (after every delete loc changes)

    if stats_granularity:
        append_optional_stats_question(teacher, stats_granularity, requests)

    update_form_body(requests, forms_service, form_id, ret_form=False)
    return form_id, form["responderUri"]


def generate_form(
    teacher: Teacher,
    generall_questions: list[Question],
    lecturer_questions: list[Question],
    practice_questions: list[Question],
    forms_service: Resource,
    drive_service: Resource,
    template_id: str,
    dest_folder_id: str,
) -> tuple[str, str]:
    form_id = copy_form(teacher.name, drive_service, template_id, dest_folder_id)

    requests = [
        {
            "updateFormInfo": {
                "info": {
                    "title": teacher.name,
                },
                "updateMask": "title",
            }
        }
    ]

    for question in generall_questions:
        append_question(question, requests)

    roles = teacher.roles
    if len(roles) == 1:
        append_optional_questions(
            teacher.overall_role, lecturer_questions, practice_questions, requests
        )
    else:
        for role in roles:
            append_optional_chapter_for_role(
                role, lecturer_questions, practice_questions, requests
            )

    form_upd_res = update_form_body(requests, forms_service, form_id)
    if len(roles) > 1:
        section_items = filter(
            lambda item: "pageBreakItem" in item, form_upd_res["form"]["items"]
        )
        options = [str(role) for role in roles]
        options_to_nextid = {
            option: item["itemId"] for option, item in zip(options, section_items)
        }
        requests.clear()
        append_branching_question(
            "Ким для вас був цей викладач?", options_to_nextid, requests
        )
        update_form_body(requests, forms_service, form_id, ret_form=False)

    return form_id, form_upd_res["form"]["responderUri"]


def append_optional_questions(
    role: Role,
    lecturer_questions: list[Question],
    practice_questions: list[Question],
    requests: list[dict[str, Any]],
):
    match role:
        case Role.LECTURER:
            role_specific_questions = lecturer_questions
        case Role.PRACTICE:
            role_specific_questions = practice_questions
        case Role.BOTH:
            role_specific_questions = lecturer_questions + practice_questions
    for question in role_specific_questions:
        append_question(question, requests)


def append_branching_question(
    question: str, options_to_nextid: dict[str, str], requests: list[dict[str, Any]]
) -> None:
    options = [
        {"value": option, "goToSectionId": next_id}
        for option, next_id in options_to_nextid.items()
    ]
    requests.append(
        {
            "createItem": {
                "item": {
                    "title": question,
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {"type": "RADIO", "options": options},
                        },
                    },
                },
                "location": {"index": 0},
            }
        }
    )


def get_stats_question(stats_granularity: Granularity):
    match stats_granularity:
        case Granularity.GROUP:
            stats_column = "Оберіть вашу групу"
        case Granularity.SPECIALITY:
            stats_column = "Оберіть вашу спеціальність"
        case Granularity.STREAM:
            stats_column = "Оберіть ваш поток"
    return stats_column


def append_optional_stats_question(
    teacher: Teacher, granularity: Granularity, requests: list[dict[str, Any]]
) -> None:
    match granularity:
        case Granularity.GROUP:
            options = [{"value": group.name} for group in teacher.groups]
        case Granularity.STREAM:
            options = [{"value": str(stream)} for stream in teacher.streams]
        case Granularity.SPECIALITY:
            options = [{"value": str(spec)} for spec in teacher.specialities]
        case Granularity.FACULTY:
            return

    if len(options) < 2:
        print(teacher.name, options)
        return

    requests.append(
        {
            "createItem": {
                "item": {
                    "title": get_stats_question(granularity),
                    "description": "Це питання є необов'язковим, інформація використовуєтьс виключно для "
                    "спостереженням за активністю респондентів",
                    "questionItem": {
                        "question": {
                            "required": False,
                            "choiceQuestion": {"type": "RADIO", "options": options},
                        },
                    },
                },
                "location": {"index": 0},
            }
        }
    )


def append_optional_chapter_for_role(
    role: Role,
    lecturer_questions: list[Question],
    practice_questions: list[Question],
    requests: list[dict[str, Any]],
):
    role_to_title = {
        Role.PRACTICE: "Питання тільки про практика",
        Role.LECTURER: "Питання тільки про лектора",
        Role.BOTH: "Питання про практика і лектора",
    }
    requests.append(
        {
            "createItem": {
                "item": {
                    "title": role_to_title[role],
                    "pageBreakItem": {"goToPage": "SUBMIT"},
                },
                "location": {"index": len(requests) - 1},
            }
        }
    )
    append_optional_questions(role, lecturer_questions, practice_questions, requests)


def append_question(question: Question, requests: list[dict[str, Any]]) -> None:
    question_item: dict[str, Any] = {"required": question.required}
    match question.type:
        case QuestionType.RATING_QUESTION:
            question_item["ratingQuestion"] = {
                "ratingScaleLevel": 5,
                "iconType": "STAR",
            }
        case QuestionType.OPEN_QUESTION:
            question_item["textQuestion"] = {"paragraph": True}
        case _:
            raise ValueError("Unsupported question type")

    requests.append(
        {
            "createItem": {
                "item": {
                    "title": question.question,
                    "description": question.description,
                    "questionItem": {
                        "question": question_item,
                    },
                },
                "location": {"index": len(requests) - 1},
            }
        }
    )


def move_item(prev_loc: int, new_loc: int, requests: list[dict[str, Any]]) -> None:
    requests.append(
        {
            "moveItem": {
                "originalLocation": {"index": prev_loc},
                "newLocation": {"index": new_loc},
            }
        }
    )


def delete_item(loc: int, requests: list[dict[str, Any]]) -> None:
    requests.append(
        {
            "deleteItem": {
                "location": {"index": loc},
            }
        }
    )


def get_form(forms_service, form_id):
    return forms_service.forms().get(formId=form_id).execute()


def update_form_body(
    requests: list[dict[str, Any]],
    forms_service: Resource,
    form_id: str,
    ret_form: bool = True,
) -> dict[str, Any]:
    form_body = {"includeFormInResponse": ret_form, "requests": requests}
    form_upd_res = (
        forms_service.forms().batchUpdate(formId=form_id, body=form_body).execute()  # type: ignore
    )
    return form_upd_res


def copy_form(
    teacher_name: str, drive_service: Resource, template_id: str, dest_folder_id: str
) -> str:
    form_file = {"name": teacher_name, "parents": [dest_folder_id]}
    copy_result = (
        drive_service.files()  # type: ignore
        .copy(fileId=template_id, body=form_file, supportsAllDrives=True)
        .execute()
    )
    form_id = copy_result["id"]
    return form_id
