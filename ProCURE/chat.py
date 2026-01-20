from openai import OpenAI
import time
import os
from log import logger
from typing import Dict, List

# os.environ['http_proxy'] = 'http://172.16.64.133:7890'
# os.environ['https_proxy'] = 'http://172.16.64.133:7890'

GPT_MODEL = "gpt-4o"
GPT_TEMPERATURE = 1.0

client = OpenAI(
    api_key = "sk-yec8lDudGbKdrSHj7baSlcOuVVejIJLF9GGmGj3Ova7VF7Er",
    base_url = "https://yunwu.ai/v1"
)


def openai_model(prompt: List[Dict], model = GPT_MODEL, temp = GPT_TEMPERATURE):
    max_attempts = 5
    wait_time = 60
    attempt = 0

    while attempt < max_attempts:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=prompt,
                temperature=temp,
            )
            content = completion.choices[0].message.content
            # print(content)
            completion_usage = completion.usage.completion_tokens
            prompt_usage = completion.usage.prompt_tokens
            usage = completion_usage + prompt_usage

            return content, usage
        except Exception as e:
            logger.error(e)
            if attempt < max_attempts - 1:
                time.sleep(wait_time)
                attempt += 1
            else:
                return None   
    return None, 0
