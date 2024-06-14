import base64
import cv2
import sys
import pyshine as ps
from datetime import datetime, timedelta
from definition import *
from utils_mobile.xml_tool import UIXMLTree
from colorama import Fore, Style
from zhipuai import ZhipuAI
import backoff



def time_within_ten_secs(time1, time2):
    def parse_time(t):
        if "+" in t:
            t = t.split()[1]
            t = t.split('.')[0] + '.' + t.split('.')[1][:6]  # 仅保留到微秒
            format = "%H:%M:%S.%f"
        else:
            format = "%H:%M:%S"
        return datetime.strptime(t, format)

    # 解析两个时间
    time1_parsed = parse_time(time1)
    time2_parsed = parse_time(time2)

    # 计算时间差并判断
    time_difference = abs(time1_parsed - time2_parsed)

    return time_difference <= timedelta(seconds=10)


def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    elif color == "white":
        print(Fore.WHITE + text)
    elif color == "black":
        print(Fore.BLACK + text)
    else:
        print(text)
    print(Style.RESET_ALL)


def draw_grid(img_path, output_path):
    def get_unit_len(n):
        for i in range(1, n + 1):
            if n % i == 0 and 120 <= i <= 180:
                return i
        return -1

    image = cv2.imread(img_path)
    height, width, _ = image.shape
    color = (255, 116, 113)
    unit_height = get_unit_len(height)
    if unit_height < 0:
        unit_height = 120
    unit_width = get_unit_len(width)
    if unit_width < 0:
        unit_width = 120
    thick = int(unit_width // 50)
    rows = height // unit_height
    cols = width // unit_width
    for i in range(rows):
        for j in range(cols):
            label = i * cols + j + 1
            left = int(j * unit_width)
            top = int(i * unit_height)
            right = int((j + 1) * unit_width)
            bottom = int((i + 1) * unit_height)
            cv2.rectangle(image, (left, top), (right, bottom), color, thick // 2)
            cv2.putText(image, str(label), (left + int(unit_width * 0.05) + 3, top + int(unit_height * 0.3) + 3), 0,
                        int(0.01 * unit_width), (0, 0, 0), thick)
            cv2.putText(image, str(label), (left + int(unit_width * 0.05), top + int(unit_height * 0.3)), 0,
                        int(0.01 * unit_width), color, thick)
    cv2.imwrite(output_path, image)
    return rows, cols


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def draw_bbox_multi(img_path, output_path, elem_list, record_mode=False, dark_mode=False):
    imgcv = cv2.imread(img_path)
    count = 1
    for elem in elem_list:
        try:
            top_left = elem.bbox[0]
            bottom_right = elem.bbox[1]
            left, top = top_left[0], top_left[1]
            right, bottom = bottom_right[0], bottom_right[1]
            label = str(count)
            if record_mode:
                if elem.attrib == "clickable":
                    color = (250, 0, 0)
                elif elem.attrib == "focusable":
                    color = (0, 0, 250)
                else:
                    color = (0, 250, 0)
                imgcv = ps.putBText(imgcv, label, text_offset_x=(left + right) // 2 + 10,
                                    text_offset_y=(top + bottom) // 2 + 10,
                                    vspace=10, hspace=10, font_scale=1, thickness=2, background_RGB=color,
                                    text_RGB=(255, 250, 250), alpha=0.5)
            else:
                text_color = (10, 10, 10) if dark_mode else (255, 250, 250)
                bg_color = (255, 250, 250) if dark_mode else (10, 10, 10)
                if (left + right) // 2 + 10 > imgcv.shape[1] or (top + bottom) // 2 + 10 > imgcv.shape[0]:
                    continue
                imgcv = ps.putBText(imgcv, label, text_offset_x=(left + right) // 2 + 10,
                                    text_offset_y=(top + bottom) // 2 + 10,
                                    vspace=10, hspace=10, font_scale=1, thickness=2, background_RGB=bg_color,
                                    text_RGB=text_color, alpha=0.5)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            print((left + right) // 2 + 10)
            print((top + bottom) // 2 + 10)
            print(imgcv.shape)
            print(f"ERROR: An exception occurs while labeling the image\n{e}")
        count += 1
    cv2.imwrite(output_path, imgcv)
    return imgcv


def get_compressed_xml(xml_path):
    xml_parser = UIXMLTree()
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_str = f.read()
    try:
        compressed_xml = xml_parser.process(xml_str, level=1, str_type="json").strip()
    except Exception as e:
        compressed_xml = None
        print(f"XML compressed failure: {e}")
    return compressed_xml


def get_xml_list(xml_path):
    xml_parser = UIXMLTree()
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_str = f.read()
    try:
        compressed_xml = xml_parser.process(xml_str, level=1, str_type="list")
    except Exception as e:
        compressed_xml = None
        print(f"XML compressed failure: {e}")
    return compressed_xml


def dump_xml(controller, device_name=None, accessiblity=False, task_id="0"):
    save_dir = "logs/auto-test/xmls"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    if accessiblity:
        controller.get_ac_xml(prefix=task_id, save_dir=save_dir)
    else:
        controller.get_xml(prefix=task_id, save_dir=save_dir)
    xml_path = os.path.join(save_dir, f"{task_id}.xml")
    xml_compressed = get_compressed_xml(xml_path)
    print(xml_compressed)
    return json.loads(xml_compressed)


def get_current_compressed_xml():
    controller, device_name = get_mobile_device_and_name()
    output_json = dump_xml(controller, device_name, False, "0")
    return output_json


def extract_bounds(node, path=""):
    result = []
    for key, value in node.items():
        current_path = f"{path}{key} "
        if isinstance(value, dict):
            result.extend(extract_bounds(value, current_path))
        elif key == "bounds":
            result.append({"key": path.strip(), "value": value})
    return result
