import os
import requests
import logging
from django.shortcuts import get_object_or_404
from .models import ControlGroupTab

# 复用已有的 PDF 提取函数，避免重复造轮子
from .LLM_response import extract_text_from_pdf

logger = logging.getLogger(__name__)

def process_control_group_llm(tab_id: int) -> str:
    """
    处理 Control Group 的 LLM 对话逻辑：
    1. 获取 Tab 绑定的 PDF 文件并提取文本。
    2. 构造 System Prompt（设定论文分析者人设）。
    3. 获取该 Tab 下的所有历史消息（包括刚存入的最新一条），拼接为多轮对话格式。
    4. 调用 DeepInfra 接口并返回生成的文本。
    """
    tab = get_object_or_404(ControlGroupTab, id=tab_id)
    
    # --- 1. 提取 PDF 文本 ---
    pdf_text = ""
    if tab.attached_file:
        try:
            # tab.attached_file.path 会返回服务器上的绝对路径
            # 现有的 extract_text_from_pdf 兼容绝对路径
            pdf_text = extract_text_from_pdf(tab.attached_file.path)
            
            # 截断处理，防止论文过长导致超出 LLM 上下文窗口报错 (可根据你使用的模型进行调整)
            max_chars = 100000 
            if len(pdf_text) > max_chars:
                pdf_text = pdf_text[:max_chars] + "\n...[Text Truncated]..."
        except Exception as e:
            logger.error(f"Failed to extract PDF text for tab {tab_id}: {e}")
            pdf_text = f"[Error extracting PDF text: {str(e)}]"

    # --- 2. 构造 System Prompt (预制开头) ---
    system_prompt = (
        "You are an expert academic paper analyzer. Your task is to help the user "
        "analyze, summarize, and understand research papers. "
        "Please respond in the same language that the user uses to ask the question. "
        "Provide helpful, clear, and conversational responses using Markdown formatting. "
    )
    
    # 如果有论文内容，直接将其作为系统背景知识注入
    if pdf_text:
        system_prompt += f"\n\nHere is the text of the currently uploaded paper for your reference:\n\n{pdf_text}"

    # --- 3. 组装多轮对话历史 ---
    # DeepInfra (兼容 OpenAI) 的标准 messages 数组格式
    messages_payload = [{"role": "system", "content": system_prompt}]
    
    # 按时间顺序获取该选项卡下的所有历史消息
    for msg in tab.messages.all().order_by('created_at'):
        # 数据库中我们存的是 'user' 和 'llm'
        # 标准 API 中，AI 的角色通常是 'assistant'
        role = "assistant" if msg.role == "llm" else "user"
        messages_payload.append({"role": role, "content": msg.text})

    # --- 4. 请求 DeepInfra API ---
    api_token = os.getenv("DEEPINFRA_API_TOKEN")
    if not api_token:
        error_msg = "Error: DEEPINFRA_API_TOKEN environment variable not set."
        logger.error(error_msg)
        return error_msg

    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"bearer {api_token}",
        "Content-Type": "application/json",
    }
    
    data = {
        # 注意：这里使用的是你之前 LLM_response.py 中默认的 Mistral 模型
        # 如果你希望支持更长的上下文（比如完整长论文），建议换成支持长上下文的模型
        # 比如 meta-llama/Meta-Llama-3-70B-Instruct 或 Qwen/Qwen2-72B-Instruct
        "model": "mistralai/Mistral-7B-Instruct-v0.3", 
        "messages": messages_payload,
        "temperature": 0.3, # 稍微给一点温度，让对话更自然，但保持学术分析的准确性
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=300)
        resp.raise_for_status()
        result = resp.json()
        
        # 提取 LLM 返回的具体文本内容
        content = result["choices"][0]["message"]["content"]
        return content or "Error: Empty response from LLM."
        
    except requests.RequestException as e:
        body_preview = getattr(e.response, "text", "")[:600] if hasattr(e, "response") and e.response is not None else ""
        logger.error(f"DeepInfra API request failed: {e}\n{body_preview}")
        return f"LLM API request failed: {str(e)}"
    except Exception as e:
        logger.exception("Unexpected error in process_control_group_llm")
        return f"An unexpected error occurred: {str(e)}"