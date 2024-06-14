from utils_mobile.utils import print_with_color
from utils_mobile.and_controller import AndroidController, list_all_devices
from agent import *
import os, json, sys, time, re, math, random, datetime, argparse, requests
import base64
from zhipuai import ZhipuAI
import backoff

def get_code_snippet(content):
    code = re.search(r'```.*?([\s\S]+?)```', content)
    if code is None:
        return content
        #print(content)
        #raise RuntimeError("No available code found!")
    code = code.group(1).strip()
    code = code.split("\n")[-1]

    return code

def get_mobile_device():
    device_list = list_all_devices()
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit()
    print_with_color(f"List of devices attached:\n{str(device_list)}", "yellow")
    if len(device_list) == 1:
        device = device_list[0]
        print_with_color(f"Device selected: {device}", "yellow")
    else:
        print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
        device = input()

    controller = AndroidController(device)
    width, height = controller.get_device_size()
    if not width and not height:
        print_with_color("ERROR: Invalid device size!", "red")
        sys.exit()
    print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

    return controller

def get_mobile_device_and_name():
    device_list = list_all_devices()
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit()
    print_with_color(f"List of devices attached:\n{str(device_list)}", "yellow")
    if len(device_list) == 1:
        device = device_list[0]
        print_with_color(f"Device selected: {device}", "yellow")
    else:
        print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
        device = input()

    controller = AndroidController(device)
    width, height = controller.get_device_size()
    if not width and not height:
        print_with_color("ERROR: Invalid device size!", "red")
        sys.exit()
    print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

    return controller, device




class Task:
    def start(self, agent: Agent, **kwargs):
        raise NotImplementedError


def handle_backoff(details):
    print(f"Retry {details['tries']} for Exception: {details['exception']}")

def handle_giveup(details):
    print(
        "Backing off {wait:0.1f} seconds afters {tries} tries calling fzunction {target} with args {args} and kwargs {kwargs}"
        .format(**details))

def detect_answer(question:str, model_answer: str, standard_answer: str):
    #print(f"Question: {question}\nModel Answer: {model_answer}\nStandard Answer: {standard_answer}")
    detect_prompt = f"You need to judge the model answer is True or False based on Standard Answer we provided. You should whether answer [True] or [False]. \n\nQuestion: {question}\n\nModel Answer: {model_answer}\n\nStandard Answer: {standard_answer}"
    call_time = 0
    while call_time <= 5:
        call_time += 1
        return_message = get_completion(prompt = detect_prompt)
        if "True" in return_message:
            return True
        elif "False" in return_message:
            return False

@backoff.on_exception(backoff.expo,
                      Exception,  # 捕获所有异常
                      max_tries=5,
                      on_backoff=handle_backoff,  # 指定重试时的回调函数
                      giveup=handle_giveup)  # 指定放弃重试时的回调函数
def get_completion(prompt, glm4_key = "your glm sdk key"):
    client = ZhipuAI(api_key=glm4_key)
    response = client.chat.completions.create(
        model="glm-4",  # 填写需要调用的模型名称
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content