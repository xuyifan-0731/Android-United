import os
import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, Callable, Type, TypeVar

import argparse

from os.path import join, isdir, isfile, relpath
from glob import glob

from evaluation.configs import AppConfig
from evaluation.task import Evaluation_Task


def find_all_task_files(all_task_config_path) -> List[str]:
    # print(type(all_task_config_path), all_task_config_path)
    tasks = []
    for task in all_task_config_path:
        if isdir(task):
            tasks += [relpath(path, ".") for path in glob(join(task, "**/*.yaml"), recursive=True)]
        elif isfile(task):
            tasks.append(task)
        else:
            print(f"'{task}' is not a valid file or directory, ignored.")
    return tasks

def find_all_traces_files(traces_path_fold) -> Dict[str, Dict[str, str]]:
    # print(type(all_task_config_path), all_task_config_path)
    traces_path = os.listdir(traces_path_fold)
    traces = {}
    for trace in traces_path:
        app_name = trace.split('_')[0]
        app_id = trace.split('_')[1]
        task_id = f"{app_name}_{app_id}"
        trace_root = os.path.join(traces_path_fold, trace)
        trace_file = os.path.join(trace_root, "traces", "trace.jsonl")
        xml_path = os.path.join(trace_root, "xml")
        trace_item = {
            "task_id": task_id,
            "trace_file": trace_file,
            "xml_path": xml_path,
            "trace_root": trace_root
        }
        traces[task_id] = trace_item
    return traces


def evaluate_all_tasks(tasks: List[Evaluation_Task]):
    for task in tasks:
        task.evaluate()
        del task

def parse_args():
    task_yamls = os.listdir('evaluation/config')
    task_yamls = ["evaluation/config/" + i for i in task_yamls if i.endswith(".yaml")]
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_argument_group("evaluation", "Evaluation configurations")
    group.add_argument("--task", nargs="+", default=task_yamls, help="All task config(s) to load")
    group.add_argument("--input_dir", type=str, required=True, help="Agent config to load")
    group.add_argument("--output_dir", type=str, default="outputs", help="Output root directory")
    group.add_argument("--task_id", nargs="+", default=None)
    group.add_argument("--detail_metrics", action="store_true", default=False, help="Show detailed metrics")
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    create_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    test_name = args.input_dir.split('/')[-1]
    output_root_dir = os.path.join(args.output_dir, test_name + "_" + create_time)
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    task_files = find_all_task_files(args.task)
    traces = find_all_traces_files(args.input_dir)

    tasks = []
    print("> Loading task configs")
    for app_task_config_path in task_files:
        app_config = AppConfig(app_task_config_path, output_dir = output_root_dir)
        app_task = Evaluation_Task(app_config, traces, detail = args.detail_metrics)
        print(f"    Evaluation_Task '{app_task.name}' loaded from config {app_task_config_path}")
        tasks.append(app_task)
    print(f"> Successfully load {len(tasks)} task{'s' if len(tasks) > 1 else ''}")
    evaluate_all_tasks(tasks)


if __name__ == "__main__":
    main()