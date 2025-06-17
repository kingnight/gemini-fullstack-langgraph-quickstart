from langchain_openai import ChatOpenAI

def aliyun_qwenMax(response_json_format: bool = False):
    base_config = {
        "api_key": "sk-391115e658964ef79aafc8ab58432e8b",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max"
    }
    
    if response_json_format:
        base_config["model_kwargs"] = {
            "response_format": {"type": "json_object"}
        }
    
    return ChatOpenAI(**base_config)    

def aliyun_qwenPlus():
    model = ChatOpenAI(
        api_key="sk-391115e658964ef79aafc8ab58432e8b",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus-latest",
        model_kwargs={
            "response_format": {"type": "json_object"}
        }
    )
    return model

def openrouter_chatGPT4o(response_json_format: bool = False):
    base_config = {
        "api_key": "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",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o"
    }
    
    if response_json_format:
        base_config["model_kwargs"] = {
            "response_format": {"type": "json_object"}
        }
    
    return ChatOpenAI(**base_config)    


def volcengine_doubao15pro32k(response_json_format: bool = False):
    base_config = {
        "api_key": "5cf950b6-17b5-4f74-9a60-4af6f987635b",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-1-5-pro-32k-250115"
    }
    
    if response_json_format:
        base_config["model_kwargs"] = {
            "response_format": {"type": "json_object"}
        }
    
    return ChatOpenAI(**base_config)