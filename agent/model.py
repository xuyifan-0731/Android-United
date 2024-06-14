import os, json, sys, time, re, math, random, datetime, argparse, requests
from typing import List, Dict, Tuple, Union, Optional, Any, Callable, Iterable, TypeVar, Generic, Sequence, Mapping, Set, Deque
from openai import OpenAI
import traceback
import backoff
from agent.utils import *
from templates.text_only_mobile import *
from templates.android_screenshot_template import *


def handle_giveup(details):
    print(
        "Backing off {wait:0.1f} seconds afters {tries} tries calling function {target} "
        "with args {args} and kwargs {kwargs}"
        .format(**details))


def handle_backoff(details):
    args = str(details['args'])[:1000]
    print(f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries "
          f"calling function {details['target'].__name__} with args {args} and kwargs ")

    import traceback
    print(traceback.format_exc())


class Agent:
    name: str

    @backoff.on_exception(
        backoff.expo, Exception,
        on_backoff=handle_backoff,
        on_giveup=handle_giveup,
    )
    def act(self, messages: List[Dict[str, Any]]) -> str:
        raise NotImplementedError

    def prompt_to_message(self, prompt, images):
        raise NotImplementedError

    def system_prompt(self, instruction) -> str:
        raise NotImplementedError



class OpenAIAgent(Agent):
    def __init__(
            self,
            api_key: str,
            api_base: str = '',
            model_name: str = '',
            max_new_tokens: int = 16384,
            temperature: float = 0,
            top_p: float = 0.7,
            **kwargs
    ) -> None:
        if api_base != '':
            self.client = OpenAI(api_key=api_key, base_url=api_base)
        else:
            self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.kwargs = kwargs
        self.name = "OpenAIAgent"

    @backoff.on_exception(
        backoff.expo, Exception,
        on_backoff=handle_backoff,
        on_giveup=handle_giveup,
        max_tries=10
    )
    def act(self, messages: List[Dict[str, Any]]) -> str:
        r = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p
        )
        return r.choices[0].message.content

    def prompt_to_message(self, prompt, images):
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        for img in images:
            base64_img = image_to_base64(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            })
        message = {
            "role": "user",
            "content": content
        }
        return message

    def system_prompt(self, instruction) -> str:
        return SYSTEM_PROMPT_ANDROID_MLLM_DIRECT + f"\n\nTask Instruction: {instruction}"

