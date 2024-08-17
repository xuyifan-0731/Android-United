from transformers import PreTrainedTokenizerFast
import json
from agent.model import *


class Llama3_70_Agent(OpenAIAgent):
    def __init__(
            self,
            url: str,
            model_name: str = '',
            max_new_tokens: int = 512,
            temperature: float = 0,
            top_p: float = 0.7,
            **kwargs
    ) -> None:
        self.url = url
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.max_tokens = 8192
        self.temperature = temperature
        self.top_p = top_p
        self.kwargs = kwargs
        self.name = "Llama3_70_Agent"
        self.tokenizer = PreTrainedTokenizerFast.from_pretrained(
            'agent/model/Meta-Llama-3-8B-Instruct')

    def act(self, messages: List[Dict[str, Any]]) -> str:
        messages = self.format_messages(messages)
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        data = {
            "model": "string",
            "messages": messages,
            "do_sample": False,
            "temperature": self.temperature,
            "max_tokens": self.max_new_tokens,
            "stop": "string",
            "stream": False
        }

        response = requests.post(self.url, headers=headers, data=json.dumps(data))

        return response.json()["choices"][0]["message"]["content"]

    def format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        num_turns = len(messages)
        total_tokens = 0
        for i, message in enumerate(messages):
            total_tokens += len(self.tokenizer.tokenize(message["content"]))
        total_tokens = total_tokens + 20 * num_turns
        if total_tokens > self.max_tokens - self.max_new_tokens - 50:
            num_delete = total_tokens - self.max_tokens + self.max_new_tokens + 50
            messages[-1]["content"] = (
                    "".join(self.tokenizer.tokenize(messages[-1]["content"])[:-num_delete]).replace("Ġ",
                                                                                                    " ").replace(
                        "Ċ", " ")
                    + "** truncated because max tokens**")
        return messages



if __name__ == "__main__":
    agent = Llama3_70_Agent(url="", max_new_tokens=32)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Please response concisely."
        },
        {
            "role": "user",
            "content": "Tell me a story."
        }
    ]
    print(agent.act(messages))
