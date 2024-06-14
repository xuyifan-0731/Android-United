from agent.model import *
from transformers import LlamaTokenizer, PreTrainedTokenizerFast
from transformers import AutoTokenizer
from PIL import Image
import os
from templates.android_screenshot_template import SYSTEM_PROMPT_ANDROID_MLLM_CogAgent
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def format_bbox(bbox, window):
    # For x1, y1, x2, y2 format bbox
    x1 = min(int(bbox[0] / window[0] * 1000), 999)
    y1 = min(int(bbox[1] / window[1] * 1000), 999)
    x2 = min(int(bbox[2] / window[0] * 1000), 999)
    y2 = min(int(bbox[3] / window[1] * 1000), 999)
    return f"[{x1:03d},{y1:03d},{x2:03d},{y2:03d}]"

def remove_leading_zeros_in_string(s):
    # 使用正则表达式匹配列表中的每个数值并去除前导零
    return re.sub(r'\b0+(\d)', r'\1', s)

def format_response(content, window_size):
    # 1. Check if linebreak in response
    if len(content.split('\n')) > 1:
        # print(f"Response `{content}` is not a valid code. Replace all `\\n` with `\\\\n`.")
        content = content.replace('\n', '\\n')

    # 2. Check if element exists and replace to relative bbox
    element = re.search(r"element=(\[\d+,\d+,\d+,\d+\])", content)
    if element is not None:
        absolute_bbox = eval(remove_leading_zeros_in_string(element.group(1)))
        relative_bbox = format_bbox(absolute_bbox, window_size)
        content = content.replace(element.group(0), f"element={relative_bbox}")

    return content

class CogagentAgent(OpenAIAgent):
    def __init__(
            self,
            url: str,
            max_new_tokens: int = 512,
            temperature: float = 0,
            top_p: float = 0.7,
            **kwargs
    ) -> None:
        self.url = url
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.kwargs = kwargs
        self.name = "Cogagent"
        self.tokenizer = PreTrainedTokenizerFast.from_pretrained("agent/model/Meta-Llama-3-8B-Instruct")


    @backoff.on_exception(
        backoff.expo, Exception,
        on_backoff=handle_backoff,
        on_giveup=handle_giveup,
        max_tries=10
    )
    def act(self, messages: List[Dict[str, Any]]) -> str:
        messages = self.format_message(messages)
        try:
            response = requests.post(self.url, files=messages[0], data=messages[1], timeout=480)
            response = response.json()
        except Exception as e:
            return str(e)

        if "error" in response:
            return response["error"]["message"]
        response["response"] = response["response"].split("<|end_of_text|>")[0]
        return response["response"]

    def system_prompt(self, instruction) -> str:
        return SYSTEM_PROMPT_ANDROID_MLLM_CogAgent + f"\n\nTask Instruction: {instruction}"

    def prompt_to_message(self, prompt, images):
        content = [{
            "type": "text",
            "text": prompt
        }]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img}",
                    "detail": "high"
                }
            })
        message = {
            "role": "user",
            "content": content
        }
        return message

    def format_message(self, messages):
        # TODO: support note and observation
        history = []

        messages = replace_image_url(messages, throw_details=True, keep_path=True)
        images = []
        for message in messages:
            if message["role"] == "user":
                if isinstance(message["content"], str):
                    continue
                for content in message["content"]:
                    if content.get("image_url"):
                        images.append(content["image_url"]["url"].split("file://")[-1])
        window_size = Image.open(images[0]).size
        images = [open(image, "rb") for image in images]


        system_prompt = messages[0]["content"]
        index = len([message for message in messages if message["role"] == "user"]) - 1
        status = messages[-1]["content"][0]["text"] if index > 0 else "{}"
        current_turn = f"Round {index}\n\n<|user|>\n{status}\n\n<|assistant|>\n"
        for i in range(index - 1, -1, -1):
            turn = messages[i * 2 + 2]
            text = turn["content"] if isinstance(turn["content"], str) else turn["content"][0]["text"]
            text = format_response(text, window_size)
            processed_turn_text = f"Round {i}\n\n<|user|>\n** SCREENSHOT **\n\n<|assistant|>\n{text}"
            length = len(self.tokenizer.tokenize(
                "\n\n".join([system_prompt,
                             "** Earlier trajectory has been truncated **", processed_turn_text] + history + [
                                current_turn])))
            if (length > 8192 - 2304 - 50 - 512):
                history = ["** Earlier trajectory has been truncated **"] + history
                #print(f"Task {self.task_id} truncated at turn {index} due to length ({length}).")
                break
            else:
                history = [processed_turn_text] + history
        history = [f"<|system|>\n{system_prompt}"] + history
        history.append(current_turn)
        prompt = "\n\n".join(history)


        new_messages = [
            {"image": images[0]},
            {"prompt": prompt}
        ]
        return new_messages

if __name__ == "__main__":
    agent = CogagentAgent("http://172.18.192.61:24024/v1/android")
    path_to_image = "/Users/xuyifan/Desktop/agent/pipeline-mobile/logs/pic/glm-v1.2/clock_1_2024-05-10_19-59-39_final_combined_image.png"
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Please response concisely."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What can you see?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{path_to_image}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]
    print(agent.act(messages))