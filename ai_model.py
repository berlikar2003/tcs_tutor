import requests

TOGETHER_API_KEY = "ea5499153d5b88c28b668720874814c6cd35054073b7665cffe8015b30c614ef"
TOGETHER_API_URL = "https://api.together.xyz/v1/completions"
MODEL = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"

HEADERS = {
    "Authorization": f"Bearer {TOGETHER_API_KEY}",
    "Content-Type": "application/json"
}

def get_chatbot_response(user_input):
    payload = {
        "model": MODEL,
        "prompt": f"<|begin_of_text|><|user|>\n{user_input}<|end_of_text|>\n<|assistant|>",
        "max_tokens": 200,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    response = requests.post(TOGETHER_API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        result = response.json()
        raw_text = result.get("choices", [{}])[0].get("text", "No response generated.")
        clean_text = raw_text.replace("<think>", "").replace("</think>", "").strip()
        return clean_text
    else:
        return f"Error from Together API: {response.status_code} - {response.text}"
