import os
import time
import base64
import getpass
import subprocess
import xml.etree.ElementTree as ET
from utils_mobile.xml_tool import UIXMLTree
import os, json, sys, time, re, math, random, datetime, argparse, requests
from typing import List, Dict, Tuple, Union, Optional, Any, Callable, Iterable, TypeVar, Generic, Sequence, Mapping, Set, Deque

# from config import load_config
from utils_mobile.utils import print_with_color, time_within_ten_secs
from templates.packages import *



def execute_adb(adb_command):
    # print(adb_command)
    env = os.environ.copy()
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/platform-tools:" + env["PATH"]
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/tools:" + env["PATH"]
    result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            executable='/bin/zsh', env=env)
    if result.returncode == 0:
        return result.stdout.strip()
    print_with_color(f"Command execution failed: {adb_command}", "red")
    print_with_color(result.stderr, "red")
    return "ERROR"


def execute_adb_no_output(adb_command):
    # print(adb_command)
    env = os.environ.copy()
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/platform-tools:" + env["PATH"]
    env["PATH"] = f"/Users/{getpass.getuser()}/Library/Android/sdk/tools:" + env["PATH"]
    result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            executable='/bin/zsh', env=env)
    if result.returncode == 0:
        return result.stdout.strip()
    return "ERROR"


def list_all_devices():
    adb_command = "adb devices"
    device_list = []
    result = execute_adb(adb_command)
    if result != "ERROR":
        devices = result.split("\n")[1:]
        for d in devices:
            device_list.append(d.split()[0])

    return device_list


class AndroidController:
    def __init__(self, device):
        self.device = device
        self.screenshot_dir = "/sdcard"
        self.xml_dir = "/sdcard"
        self.ac_xml_dir = "/sdcard/Android/data/com.example.android.xml_parser/files"
        self.width, self.height = self.get_device_size()
        self.viewport_size = (self.width, self.height)
        self.backslash = "\\"

    def get_device_size(self):
        command = f"adb -s {self.device} shell wm size"
        output = execute_adb(command)
        resolution = output.split(":")[1].strip()
        width, height = resolution.split("x")
        return int(width), int(height)

    def get_screenshot(self, prefix, save_dir):
        cap_command = f"adb -s {self.device} shell screencap -p " \
                      f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.png')}"
        result = execute_adb(cap_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return os.path.join(save_dir, prefix + ".png")
            return result
        return result

    def save_screenshot(self, save_path):
        prefix = os.path.basename(save_path).replace('.png', '')
        remote_path = f"{os.path.join(self.screenshot_dir, f"{prefix}.png").replace(self.backslash, '/')}"

        cap_command = f"adb -s {self.device} shell screencap -p {remote_path}"
        pull_command = f"adb -s {self.device} pull {remote_path} {save_path}"
        print(remote_path, save_path)
        result = execute_adb(cap_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return save_path
            return result
        return result

    def get_xml(self, prefix, save_dir):
        remote_path = os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')
        local_path = os.path.join(save_dir, prefix + '.xml')
        dump_command = f"adb -s {self.device} shell uiautomator dump {remote_path}"
        pull_command = f"adb -s {self.device} pull {remote_path} {local_path}"

        def is_file_empty(file_path):
            return os.path.exists(file_path) and os.path.getsize(file_path) == 0

        for attempt in range(5):
            result = execute_adb(dump_command)
            if result == "ERROR":
                time.sleep(2)
                continue

            result = execute_adb(pull_command)
            if result == "ERROR" or is_file_empty(local_path):
                time.sleep(2)
                continue

            return local_path

        # Final attempt after 3 retries
        result = execute_adb(dump_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR" and not is_file_empty(local_path):
                return local_path

        return result

    def get_ac_xml(self, prefix, save_dir):
        remote_path = f"{os.path.join(self.ac_xml_dir, 'ui.xml').replace(self.backslash, '/')}"
        local_path = os.path.join(save_dir, prefix + '.xml')
        pull_command = f"adb -s {self.device} pull {remote_path} {local_path}"

        def is_file_empty(file_path):
            return os.path.exists(file_path) and os.path.getsize(file_path) == 0

        for attempt in range(5):
            result = execute_adb(pull_command)
            if result != "ERROR" and not is_file_empty(local_path):
                return local_path
            time.sleep(2)

        # Final attempt after 3 retries
        result = execute_adb(pull_command)
        if result != "ERROR" and not is_file_empty(local_path):
            return local_path

        return result

    def get_current_activity(self):
        adb_command = "adb -s {device} shell dumpsys window | grep mCurrentFocus | awk -F '/' '{print $1}' | awk '{print $NF}'"
        adb_command = adb_command.replace("{device}", self.device)
        result = execute_adb(adb_command)
        if result != "ERROR":
            return result
        return 0

    def get_current_app(self):
        activity = self.get_current_activity()
        app = find_app(activity)
        return app

    def back(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
        ret = execute_adb(adb_command)
        return ret

    def enter(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_ENTER"
        ret = execute_adb(adb_command)
        return ret

    def home(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_HOME"
        ret = execute_adb(adb_command)
        return ret

    def tap(self, x, y):
        adb_command = f"adb -s {self.device} shell input tap {x} {y}"
        ret = execute_adb(adb_command)
        return ret

    def text(self, input_str):
        # adb_command = f'adb -s {self.device} input keyevent KEYCODE_MOVE_END'
        # ret = execute_adb(adb_command)
        adb_command = f'adb -s {self.device} shell input keyevent --press $(for i in {{1..100}}; do echo -n "67 "; done)'
        ret = execute_adb(adb_command)
        chars = input_str
        charsb64 = str(base64.b64encode(chars.encode('utf-8')))[1:]
        adb_command = f"adb -s {self.device} shell am broadcast -a ADB_INPUT_B64 --es msg {charsb64}"
        ret = execute_adb(adb_command)
        return ret

    def long_press(self, x, y, duration=1000):
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def kill_package(self, package_name):
        command = f"adb -s {self.device} shell am force-stop {package_name}"
        execute_adb(command)

    def swipe(self, x, y, direction, dist: Union[str, int] = "medium", quick=False):
        if x is None:
            x = self.width // 2
        if y is None:
            y = self.height // 2
        if isinstance(dist, str):
            unit_dist = int(self.width / 10)
            if dist == "long":
                unit_dist *= 10
            elif dist == "medium":
                unit_dist *= 2
        elif isinstance(dist, int):
            unit_dist = dist
        if direction == "up":
            offset = 0, -2 * unit_dist
        elif direction == "down":
            offset = 0, 2 * unit_dist
        elif direction == "left":
            offset = -1 * unit_dist, 0
        elif direction == "right":
            offset = unit_dist, 0
        else:
            return "ERROR"
        duration = 100 if quick else 400
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x + offset[0]} {y + offset[1]} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def swipe_precise(self, start, end, duration=400):
        start_x, start_y = start
        end_x, end_y = end
        adb_command = f"adb -s {self.device} shell input swipe {start_x} {start_x} {end_x} {end_y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def launch_app(self, package_name):
        command = f"adb -s {self.device} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        ret = execute_adb(command)
        return ret

    def start_screen_record(self, prefix):
        print("Starting screen record")
        command = f'adb -s {self.device} shell screenrecord /sdcard/{prefix}.mp4'
        return subprocess.Popen(command, shell=True)

    def launch_package(self, package_name):
        command = f"adb -s {self.device} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        execute_adb(command)

    def run_command(self, command):
        command = command.replace("adb", f"adb -s {self.device} ")
        return execute_adb(command)

    def check_ac_survive(self):
        try:
            time_command = f"adb -s {self.device} shell stat -c %y /sdcard/Android/data/com.example.android.xml_parser/files/ui.xml"
            time_phone_command = f"adb -s {self.device} shell date +\"%H:%M:%S\""
            result = time_within_ten_secs(execute_adb(time_command), execute_adb(time_phone_command))
        except Exception as e:
            print(e)
            return False
        return result


if __name__ == '__main__':
    And = AndroidController("emulator-5554")
    And.text("北京南站")
