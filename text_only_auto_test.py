import os
import subprocess
import yaml
from dataclasses import dataclass
from copy import deepcopy

from definition import *
from agent import get_agent
from utils_mobile.xml_tool import UIXMLTree
from templates.text_only_mobile import SYSTEM_PROMPT_ANDROID_TEXT_GPT, SYSTEM_PROMPT_ANDROID_TEXT_GLM_v1_5
from page_executor.utils import plot_bbox
from recorder import JSONRecorder
from utils_mobile.and_controller import AndroidController, list_all_devices, execute_adb_no_output
from page_executor import TextOnlyExecutor
from evaluation_auto_test import *
from evaluation.configs import AppConfig
from templates.packages import find_package

def get_avd_serial_number(avd_name):
    try:
        # 获取所有连接的设备及其序列号
        result = subprocess.run(['adb', 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        devices_output = result.stdout

        # 提取设备序列号
        devices = [line.split()[0] for line in devices_output.splitlines() if 'device' in line and 'List' not in line]

        # 遍历设备，查找对应的AVD名字
        for device in devices:
            result = subprocess.run(['adb', '-s', device, 'emu', 'avd', 'name'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            avd_output = result.stdout.replace("OK", "").strip()
            #print(avd_output.replace("OK", "").strip())

            if avd_output == avd_name:
                return device

        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


@dataclass
class AutoTest_TaskConfig:
    save_dir: str
    max_rounds: int
    mode: Optional[float] = None
    request_interval: Optional[float] = None
    task_id: Optional[str] = None
    avd_name: Optional[str] = None
    avd_log_dir: Optional[str] = None
    avd_base: Optional[str] = None
    android_sdk_path: Optional[str] = None
    is_relative_bbox: Optional[bool] = False

    def subdir_config(self, subdir: str, task_id = None):
        new_config = self.__dict__.copy()
        new_config["save_dir"] = os.path.join(self.save_dir, subdir)
        new_config["task_id"] = task_id
        return AutoTest_TaskConfig(**new_config)

    def add_config(self, config):
        new_config = self.__dict__.copy()
        for key, values in config.items():
            new_config[key] = values
        return AutoTest_TaskConfig(**new_config)

class AutoTask():
    def __init__(self, instruction, controller, page_executor, agent, record, command_per_step,**kwargs):
        self.controller = controller
        self.page_executor = page_executor
        self.agent = agent
        self.record = record
        self.kwargs = kwargs
        self.set_system_prompt(instruction)
        self.record.command_per_step = [command_per_step]
        if "map.me" in instruction or "pimusic" in instruction:
            self.accessibility = self.controller.check_ac_survive()
        else:
            self.accessibility = False

    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": self.agent.system_prompt(instruction)
        }]


    def run_step(self, round_count):
        self.record.update_before(controller=self.controller, need_screenshot=True, ac_status=self.accessibility)
        compressed_xml_json = self.record.get_latest_xml()

        prompt = f"" if round_count == 0 else "** XML **\n"
        try:
            current_message = {"role": "user", "content": prompt + compressed_xml_json}
            if self.agent.name == "GLMModelAgent":
                current_message["current_app"] = self.controller.get_current_activity()
            rsp = self.agent.act([*self.record.history, current_message])
        except Exception as e:
            print_with_color(f"Error: {e}", "red")

        exe_res = self.page_executor(get_code_snippet(rsp))
        self.record.update_after(exe_res, rsp)
        self.record.turn_number += 1

class TextOnlyTask(AutoTask):
    def set_system_prompt(self, instruction):
        self.record.history = [{
            "role": "system",
            "content": SYSTEM_PROMPT_ANDROID_TEXT_GPT + f"\n\nTask Instruction: {instruction}"
        }]


class TextOnlyMobileTask_AutoTest(Task):
    def __init__(self, config: AutoTest_TaskConfig) -> None:
        self.config = config

    def prepare_for_task(self):
        os.makedirs(self.config.save_dir, exist_ok=True)
        demo_timestamp = int(time.time())
        self.config.task_name = self.config.task_id + "_" + datetime.datetime.fromtimestamp(demo_timestamp).strftime("%Y-%m-%d_%H-%M-%S")
        self.config.task_dir = os.path.join(self.config.save_dir, self.config.task_name)
        if not os.path.exists(self.config.task_dir):
            os.mkdir(self.config.task_dir)
        self.config.log_path = os.path.join(self.config.task_dir, f"log_explore_{self.config.task_name}.jsonl")
        self.config.trace_dir = os.path.join(self.config.task_dir, 'traces')
        self.config.screenshot_dir = os.path.join(self.config.task_dir, 'Screen')
        self.config.xml_dir = os.path.join(self.config.task_dir, 'xml')
        os.makedirs(self.config.trace_dir, exist_ok=True)
        os.makedirs(self.config.screenshot_dir, exist_ok=True)
        os.makedirs(self.config.xml_dir, exist_ok=True)
        self.config.glm4_key = "1bb266a2ba7371a1a021e64271026461.BxqveqxxAbHD40CQ"

    def start_emulator(self):
        avd_name = self.config.avd_name
        print_with_color(f"Starting Android Emulator with AVD name: {avd_name}", "blue")
        if not os.path.exists(self.config.avd_log_dir):
            os.makedirs(self.config.avd_log_dir, exist_ok=True)
        out_file = open(os.path.join(self.config.avd_log_dir, 'emulator_output.txt'), 'a')
        emulator_process = subprocess.Popen(["emulator", "-avd", avd_name, "-no-snapshot-save"], stdout=out_file,
                                            stderr=out_file)
        print_with_color(f"Waiting for the emulator to start...", "blue")
        while True:
            try:
                device = get_adb_device_name(avd_name)
            except:
                continue
            if device is not None:
                break
        while True:
            boot_complete = f"adb -s {device} shell getprop init.svc.bootanim"
            boot_complete = execute_adb_no_output(boot_complete)
            if boot_complete == 'stopped':
                print_with_color("Emulator started successfully", "blue")
                break
            time.sleep(1)
        time.sleep(1)
        self.emulator_process = emulator_process
        self.out_file = out_file
        device_list = list_all_devices()
        if len(device_list) == 1:
            device = device_list[0]
            print_with_color(f"Device selected: {device}", "yellow")
        else:
            device = get_avd_serial_number(avd_name)
        controller = AndroidController(device)
        self.controller = controller
        self.controller.run_command("adb root")
        self.controller.run_command("adb emu geo fix -122.156 37.438")
        if "map.me" not in self.instruction:
            self.controller.run_command("adb shell date \"2024-05-10 12:00:00\"")
        #self.controller.run_command("adb shell ime set com.android.adbkeyboard/.AdbIME")
        if self.config.mode == "in_app":
            self.controller.launch_app(find_package(self.app))
            time.sleep(5)

    def stop_emulator(self):
        print_with_color("Stopping Android Emulator...", "blue")
        self.emulator_process.terminate()

        while True:
            try:
                device = get_adb_device_name(self.config.avd_name)
                command = f"adb -s {device} reboot -p"
                ret = execute_adb_no_output(command)
                self.emulator_process.terminate()
            except:
                device = None
            if device is None:
                print_with_color("Emulator stopped successfully", "blue")
                break
            time.sleep(1)
        self.out_file.close()

    def get_agent(self):
        task_agent = TextOnlyTask(self.instruction, self.controller, self.page_executor, self.llm_agent, self.record, self.command_per_step)
        return task_agent

    def get_executor(self):
        return TextOnlyExecutor(self.controller, self.config)


    def start(self, agent: Agent, instruction: str, controller = None, package_name: Optional[str] = None, command_per_step = None, app = None):
        self.instruction = instruction
        self.app = app
        self.command_per_step = command_per_step
        self.prepare_for_task()
        self.start_emulator()
        self.llm_agent = agent


        print_with_color(instruction, "green")
        round_count = 0
        task_complete = False

        self.page_executor = self.get_executor()
        self.record = JSONRecorder(id=self.config.task_name, instruction=instruction, page_executor=self.page_executor,
                              config=self.config)
        task_agent = self.get_agent()

        while round_count < self.config.max_rounds:
            try:
                round_count += 1
                print_with_color(f"Round {round_count}", "yellow")
                task_agent.run_step(round_count)
                print_with_color("Thinking about what to do in the next step...", "yellow")
                time.sleep(self.config.request_interval)

                if task_agent.page_executor.is_finish:
                    print_with_color(f"Completed successfully.", "yellow")
                    task_agent.page_executor.update_screenshot(prefix="end")
                    task_complete = True
                    break
            except Exception as e:
                import traceback
                print(traceback.print_exc())
                print_with_color(f"Error: {e}", "red")
                break

        self.stop_emulator()
        if task_complete:
            print_with_color(f"Completed successfully. {round_count} rounds generated.", "green")
        elif round_count == self.config.max_rounds:
            print_with_color(
                f"Finished due to reaching max rounds. {round_count} rounds generated.",
                "yellow")
        else:
            print_with_color(f"Finished unexpectedly. {round_count} rounds generated.", "red")




def get_adb_device_name(avd_name=None):
    device_list = list_all_devices()
    for device in device_list:
        command = f"adb -s {device} emu avd name"
        ret = execute_adb_no_output(command)
        ret = ret.split("\n")[0]
        if ret == avd_name:
            return device
    return None

# python text_only_auto_test.py -n glm-v1.3 -c config-eva-glm.yaml --task_id map_1
if __name__ == '__main__':
    task_yamls = os.listdir('evaluation/config')
    task_yamls = ["evaluation/config/" + i for i in task_yamls if i.endswith(".yaml")]

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-n", "--name", default="test", type=str)
    arg_parser.add_argument("-c", "--config", default="config-eva-glm.yaml", type=str)
    arg_parser.add_argument("--task_config", nargs="+", default=task_yamls, help="All task config(s) to load")
    arg_parser.add_argument("--task_id", nargs="+", default=None)

    args = arg_parser.parse_args()
    with open(args.config, "r") as file:
        yaml_data = yaml.safe_load(file)

    agent_config = yaml_data["agent"]
    task_config = yaml_data["task"]
    eval_config = yaml_data["eval"]

    config = AutoTest_TaskConfig(**task_config["args"])
    config = config.add_config(eval_config)
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
            package = app_config.package
            command_per_step = app_config.command_per_step.get(task_id, None)
            task = TextOnlyMobileTask_AutoTest(config.subdir_config(args.name, task_id=task_id))
            task_instruction = f"You should use {app} to complete the following task: {task_instruction}"
            task.start(agent, task_instruction, package, command_per_step=command_per_step, app = app)