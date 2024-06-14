from text_only_auto_test import *
from templates.android_screenshot_template import *
from page_executor.simple_vision_executor import VisionExecutor
import templates.seeact_screenshot_prompts as SeeActPrompts

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

class ScreenshotTask(TextOnlyTask):
    def run_step(self, round_count):
        self.record.update_before(controller=self.controller, need_screenshot=True, ac_status=self.accessibility, need_labeled=True)
        prompt = f"" if round_count == 0 else "** XML **\n"
        try:
            xml = self.record.get_latest_xml()
            image_path = self.record.labeled_current_screenshot_path
            current_message = self.agent.prompt_to_message(prompt, [image_path])
            rsp = self.agent.act([*self.record.history, current_message])
        except Exception as e:
            import traceback
            print(traceback.print_exc())
            #print_with_color(f"Error: {e}", "red")

        exe_res = self.page_executor(get_code_snippet(rsp))
        self.record.update_after(exe_res, rsp)
        self.record.turn_number += 1

    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT_ANDROID_MLLM_DIRECT + f"\n\nTask Instruction: {instruction}"
        }]

class CogAgentTask(TextOnlyTask):
    def run_step(self, round_count):
        self.record.update_before(controller=self.controller, need_screenshot=True, ac_status=self.accessibility, need_labeled=True)
        prompt = f"" if round_count == 0 else json.dumps({"current_app": self.controller.get_current_app()}, ensure_ascii=False)
        try:
            image_path = self.page_executor.current_screenshot
            current_message = self.agent.prompt_to_message(prompt, [image_path])
            rsp = self.agent.act([*self.record.history, current_message])
        except Exception as e:
            import traceback
            print(traceback.print_exc())
            #print_with_color(f"Error: {e}", "red")

        exe_res = self.page_executor(get_code_snippet(rsp))
        self.record.update_after(exe_res, rsp)
        self.record.turn_number += 1

    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT_ANDROID_MLLM_CogAgent + f"\n\nTask Instruction: {instruction}"
        }]



class ScreenshotReactTask(ScreenshotTask):
    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT_ANDROID_MLLM_DIRECT_REACT + f"\n\nTask Instruction: {instruction}"
        }]


class ScreenSeeActTask(TextOnlyTask):

    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SeeActPrompts.QUERY_SYSTEM_PROMPT
        }]
        self.stage_one_record = []
        self.instruction = instruction

    def run_step(self, round_count):
        self.record.update_before(controller=self.controller, need_screenshot=True, ac_status=self.accessibility,
                                  need_labeled=False)
        try:
            xml_tree = self.record.get_latest_xml_tree()
            choices_list = extract_bounds(xml_tree)
            image_path = self.page_executor.current_screenshot
            system_prompt = SeeActPrompts.QUERY_SYSTEM_PROMPT
            query_user_prompt = SeeActPrompts.QUERY_USER_PROMPT.format(
                task=self.instruction,
                previous_actions=("\n\n".join(self.stage_one_record) or "None")
            )
            query_message = self.agent.prompt_to_message(query_user_prompt, [image_path])
            referring_user_prompt = SeeActPrompts.REFERRING_USER_PROMPT.format(
                option_prompt="\n".join(f"{item['key']} | {item['value']}" for item in choices_list)
            )

            messages = [
                {"role": "system", "content": system_prompt},
                query_message,
            ]

            # Stage 1. Query
            print(">> Stage 1. Query")
            with open("monitor.log", "w") as f:
                f.write(json.dumps(messages, indent=4))
            description = self.agent.act(messages)
            print(description, end="\n\n")
            with open("monitor.log", "w") as f:
                f.write(description)
            messages.append({"role": "assistant", "content": description})
            messages.append({"role": "user", "content": referring_user_prompt})

            # Stage 2. Referring
            print(">> Stage 2. Referring")
            with open("monitor.log", "w") as f:
                f.write(json.dumps(messages, indent=4))
            referring = self.agent.act(messages)
            print(referring, end="\n\n")
            with open("monitor.log", "w") as f:
                f.write(referring)


        except Exception as e:
            import traceback
            print(traceback.print_exc())
            # print_with_color(f"Error: {e}", "red")
            # exit(1)

        exe_res = self.page_executor(get_code_snippet(referring))
        self.stage_one_record.append(description)
        self.record.update_after(exe_res, description + "\n\n==========\n\n" + referring)
        self.record.turn_number += 1


class TextOnlyReactTask(TextOnlyTask):
    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT_ANDROID_TEXT_ReAct + f"\n\nTask Instruction: {instruction}"
        }]

class TextOnlyFineTuneTask(TextOnlyTask):
    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT_ANDROID_TEXT_GLM_v1_5 + f"\n\nTask Instruction: {instruction}"
        }]

    def run_step(self, round_count):
        self.record.update_before(controller=self.controller, need_screenshot=True, ac_status=self.accessibility)
        compressed_xml_json = self.record.get_latest_xml()

        #prompt = f"" if round_count == 0 else "** XML **\n"
        try:
            app_info = f"{json.dumps({'current_app': self.controller.get_current_app()}, ensure_ascii=False)}\n"
            current_message = {"role": "user", "content": app_info + compressed_xml_json}
            rsp = self.agent.act([*self.record.history, current_message])
        except Exception as e:
            print_with_color(f"Error: {e}", "red")

        exe_res = self.page_executor(get_code_snippet(rsp))
        self.record.update_after(exe_res, rsp)
        self.record.turn_number += 1

def extract_bounds(node, path=""):
    result = []
    for key, value in node.items():
        current_path = key
        # 如果要展示完整路径，可以改成{path}{key}
        if isinstance(value, dict):
            result.extend(extract_bounds(value, current_path))
        elif key == "bounds":
            result.append({"key": path.strip(), "value": value})
    return result

class ScreenshotMobileTask_AutoTest(TextOnlyMobileTask_AutoTest):
    def __init__(self, config: AutoTest_TaskConfig) -> None:
        self.config = config

    def get_agent(self):
        task_agent = ScreenshotTask(self.instruction, self.controller, self.page_executor, self.llm_agent, self.record, self.command_per_step)
        return task_agent

    def get_executor(self):
        return VisionExecutor(self.controller, self.config)

class CogAgentTask_AutoTest(TextOnlyMobileTask_AutoTest):
    def get_agent(self):
        task_agent = CogAgentTask(self.instruction, self.controller, self.page_executor, self.llm_agent, self.record, self.command_per_step)
        return task_agent

    def get_executor(self):
        return VisionExecutor(self.controller, self.config)

class ScreenSeeActTask_AutoTest(TextOnlyMobileTask_AutoTest):
    def get_agent(self):
        task_agent = ScreenSeeActTask(self.instruction, self.controller, self.page_executor, self.llm_agent, self.record, self.command_per_step)
        return task_agent


class ScreenReactTask_AutoTest(TextOnlyMobileTask_AutoTest):
    def get_agent(self):
        task_agent = ScreenshotReactTask(self.instruction, self.controller, self.page_executor, self.llm_agent,
                                        self.record, self.command_per_step)
        return task_agent

    def get_executor(self):
        return VisionExecutor(self.controller, self.config)

class TextOnlyReactTask_AutoTest(TextOnlyMobileTask_AutoTest):
    def get_agent(self):
        task_agent = TextOnlyReactTask(self.instruction, self.controller, self.page_executor, self.llm_agent,
                                        self.record, self.command_per_step)
        return task_agent

class TextOnlyFineTuneTask_AutoTest(TextOnlyMobileTask_AutoTest):
    def get_agent(self):
        task_agent = TextOnlyFineTuneTask(self.instruction, self.controller, self.page_executor, self.llm_agent,
                                        self.record, self.command_per_step)
        return task_agent

# python text_only_auto_test.py -n glm-v1.3 -c config-eva-glm.yaml --task_id map_1
if __name__ == '__main__':
    task_yamls = os.listdir('evaluation/config')
    task_yamls = ["evaluation/config/" + i for i in task_yamls if i.endswith(".yaml")]

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-n", "--name", default="test", type=str)
    arg_parser.add_argument("-c", "--config", default="config-mllm-0409.yaml", type=str)
    arg_parser.add_argument("--task_config", nargs="+", default=task_yamls, help="All task config(s) to load")
    arg_parser.add_argument("--task_id", nargs="+", default=None)
    arg_parser.add_argument("--debug", action="store_true", default=False)
    arg_parser.add_argument("--app", nargs="+", default=None)

    args = arg_parser.parse_args()
    with open(args.config, "r") as file:
        yaml_data = yaml.safe_load(file)

    agent_config = yaml_data["agent"]
    task_config = yaml_data["task"]
    eval_config = yaml_data["eval"]

    autotask_class = task_config["class"] if "class" in task_config else "ScreenshotMobileTask_AutoTest"

    config = AutoTest_TaskConfig(**task_config["args"])
    config = config.add_config(eval_config)
    if "True" == agent_config.get("relative_bbox"):
        config.is_relative_bbox = True
    agent = get_agent(agent_config["name"], **agent_config["args"])

    task_files = find_all_task_files(args.task_config)
    if os.path.exists(os.path.join(config.save_dir, args.name)):
        already_run = os.listdir(os.path.join(config.save_dir, args.name))
        already_run = [i.split("_")[0] + "_" + i.split("_")[1] for i in already_run]
    else:
        already_run = []

    for app_task_config_path in task_files:
        app_config = AppConfig(app_task_config_path)
        if args.task_id is None:
            task_ids = list(app_config.task_name.keys())
        else:
            task_ids = args.task_id
        for task_id in task_ids:
            if task_id in already_run:
                print(f"Task {task_id} already run, skipping")
                continue
            if task_id not in app_config.task_name:
                print(f"Task {task_id} not found in config, skipping")
                continue
            task_instruction = app_config.task_name[task_id].strip()
            app = app_config.APP
            if args.app is not None:
                print(app, args.app)
                if app not in args.app:
                    continue
            package = app_config.package
            command_per_step = app_config.command_per_step.get(task_id, None)
            class_ = globals().get(autotask_class)
            if class_ is None:
                raise AttributeError(f"在全局命名空间中没有找到类 {autotask_class}。请确保类名正确。")

            task = class_(config.subdir_config(args.name, task_id=task_id))
            task_instruction = f"You should use {app} to complete the following task: {task_instruction}"
            task.start(agent, task_instruction, package, command_per_step=command_per_step, app = app)
            if args.debug:
                exit()
