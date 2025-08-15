import argparse
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Iterable


def get_first(it: Iterable[Any], pred: Callable[[Any], bool]):
    return next((x for x in it if pred(x)), None)


def determine_year_and_semester(pub_date: datetime) -> str:
    if pub_date.month <= 6:
        sem = "I"
    else:
        sem = "II"
    year = pub_date.year - 1
    return f"{sem} семестр {year}/{year + 1}"


def parse_message_history(
    messages: list[dict[str, Any]],
) -> Iterable[tuple[str, str, str]]:
    for message in messages:
        text = message["text"]
        if isinstance(text, list):
            text = get_first(
                text,
                lambda item: isinstance(item, str)
                and item.splitlines()
                and len(item.splitlines()[0].split()) == 3,
            )
        if not text:
            continue

        text = text.splitlines()[0].strip()

        name_parts = text.split()
        if len(name_parts) == 3 and all(
            map(lambda p: len(p) >= 4 and str.isupper(p[0]), name_parts)
        ):
            pub_date = datetime.strptime(message["date"], "%Y-%m-%dT%H:%M:%S")
            str_sem = determine_year_and_semester(pub_date)

            # corner cases
            text = text.translate({"ʼ": "'", "`": "'"})
            text = text.replace("Наказной", "Наказний")

            yield text, message["id"], str_sem


def get_channel_link_part(channel_id: str) -> str:
    id2username = {
        1198212824: "analyticsFTI",
        1896101333: "ipt_sight",
        2451504931: "ipt_bee",
    }
    return id2username.get(channel_id, f"c/{channel_id}")


def gather_links(jsons: list[str], out_path: str):
    links_dict: dict[str, list[dict[str, str]]] = {}
    for path in jsons:
        with open(path) as file:
            history = json.load(file)
            channel_name = history["name"]
            channel_id = history["id"]

        for name, id, sem_year in parse_message_history(history["messages"]):
            info = {
                "link": f"https://t.me/{get_channel_link_part(channel_id)}/{id}",
                "channel_name": channel_name,
                "semester": sem_year,
            }
            if name in links_dict:
                links_dict[name].append(info)
            else:
                links_dict[name] = [info]

    with open(out_path, "w") as file:
        json.dump(links_dict, file, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--exported_jsons",
        nargs="+",
        type=str,
        required=True,
        help="Paths to the exported as JSON file history of telegram channels with previous survey result",
    )
    parser.add_argument(
        "--out_path",
        type=str,
        required=True,
        help="Path to the file where gathered links will be saved",
    )

    args = parser.parse_args()

    gather_links(args.exported_jsons, args.out_path)
