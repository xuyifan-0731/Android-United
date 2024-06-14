from evaluation_auto_test import *
import concurrent.futures
import jsonlines
import pandas as pd
from collections import defaultdict


def evaluate_input_dir(input_dir, task_yamls, create_time, args):
    test_name = input_dir.split('/')[-1]
    output_root_dir = os.path.join(args.output_folder, test_name + "_" + create_time)
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    task_files = find_all_task_files(task_yamls)
    traces = find_all_traces_files(input_dir)

    tasks = []
    print("> Loading task configs")
    for app_task_config_path in task_files:
        app_config = AppConfig(app_task_config_path, output_dir=output_root_dir)
        app_task = Evaluation_Task(app_config, traces, detail=True)
        print(f"    Evaluation_Task '{app_task.name}' loaded from config {app_task_config_path}")
        tasks.append(app_task)
    print(f"> Successfully load {len(tasks)} task{'s' if len(tasks) > 1 else ''}")
    evaluate_all_tasks(tasks)

def output_to_excel(args):
    output_df = pd.DataFrame()
    base_folder = args.output_folder
    outputs = os.listdir(base_folder)

    for output in outputs:
        output_folder = os.path.join(base_folder, output)
        agent_name = output.split("_2024")[0]
        if not os.path.exists(os.path.join(output_folder, "total.jsonl")):
            continue
        with jsonlines.open(os.path.join(output_folder, "total.jsonl")) as f:
            dict = defaultdict(list)
            tt = 0
            for line in f:
                total = line["Total"]
                App = line["App"]
                for key, value in line.items():
                    if key == "App":
                        dict["App"].append(1)
                    elif key == "Total":
                        dict[key].append(value)
                        tt += value
                    elif "Sum_" in key or key == "Complete_Correct":
                        dict[key].append(value)
            tt_correct = sum(dict["Complete_Correct"])
            output_dict = {}
            output_dict["agent_name"] = agent_name
            for key, value in dict.items():
                if key == "App":
                    output_dict[key] = len(value)
                elif key == "Total":
                    output_dict[key] = sum(value)
                elif key == "Sum_RRR":
                    output_dict[key] = 100 * sum(value) / tt_correct
                elif key == "Complete_Correct" or "Sum_" in key:
                    output_dict[key] = 100 * sum(value) / tt
                #else:
                    #output_dict[key] = sum(value) / tt
            print(output_dict)
            #output_dict["Acc"] = output_dict["Complete_Correct"] / output_dict["Total"]
            output_dict["Acc"] = tt_correct / tt
            output_dict["correct"] = tt_correct
            output_df = output_df._append(output_dict, ignore_index=True)
    output_df.to_excel(args.output_excel)
    print(output_df)

def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_argument_group("evaluation", "Evaluation configurations")
    group.add_argument("--input_folder", type=str, required=True)
    group.add_argument("--output_folder", type=str, required=True)
    group.add_argument("--output_excel", type=str, required=True)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    task_yamls = os.listdir('evaluation/config')
    task_yamls = ["evaluation/config/" + i for i in task_yamls if i.endswith(".yaml")]
    create_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    input_folder = args.input_folder

    input_dirs = [os.path.join(input_folder, input_dir) for input_dir in os.listdir(input_folder)]

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    already_output = os.listdir(args.output_folder)
    agent_list = []
    for output in already_output:
        agent_name = output.split("_2024")[0]
        agent_list.append(agent_name)
    for input_dir in input_dirs:
        for agent in agent_list:
            if agent == input_dir.split('/')[-1]:
                input_dirs.remove(input_dir)
                break



    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(evaluate_input_dir, input_dir, task_yamls, create_time, args) for input_dir in input_dirs]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    output_to_excel(args)

if __name__ == "__main__":
    main()
