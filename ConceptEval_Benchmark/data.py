from typing import Iterable, Dict
import gzip
import json
import os


ROOT = os.path.dirname(os.path.abspath(__file__))
HUMAN_EVAL = os.path.join(ROOT, "HumanEval.jsonl")
MBPP = os.path.join(ROOT, "MBPP.jsonl")
CODECONTESTS = os.path.join(ROOT, "CodeContests.jsonl")


def read_problems(evalset_file: str = HUMAN_EVAL) -> Dict[str, Dict]:
    return {task["task_id"]: task for task in stream_jsonl(evalset_file)}


def stream_jsonl(filename: str) -> Iterable[Dict]:
    """
    Parse each jsonl line and yield it as a dictionary
    """
    with open(filename, "r") as fp:
        for line in fp:
            if any(not x.isspace() for x in line):
                yield json.loads(line)


def write_jsonl(filename: str, data: Iterable[Dict], append: bool = False):
    """
    Write an iterable of dictionaries to jsonl
    """
    mode = 'a' if append else 'w'
    filename = os.path.expanduser(filename)
    with open(filename, mode) as fp:
        for x in data:
            fp.write((json.dumps(x) + "\n"))
