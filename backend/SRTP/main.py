import uvicorn
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict

# 从我们的代理脚本中导入核心功能
from .deepseek_agent import run_agent_conversation

app = FastAPI(
    title="Conversational Geo-Analysis AI Agent API",
    description="一个能通过多轮对话与用户交互，进行地理空间数据分析的智能代理。",
    version="1.1.0",
)

# --- 会话存储 (用于演示，生产环境应使用Redis, DB等) ---
conversations: Dict[str, List[Dict]] = {}

# --- 请求和响应模型 ---

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    requires_follow_up: bool
    generated_files: List[str]

# --- API 端点 ---

@app.get("/")
async def read_root():
    """
    根端点，返回一个欢迎信息。
    """
    return {"message": "欢迎使用多轮对话地理空间分析智能代理 API！"}

def format_response(result: dict, conversation_id: str):
    """辅助函数，用于将agent结果格式化为API响应。"""
    base_url = "http://localhost:8000/outputs/"
    file_urls = [f"{base_url}{f}" for f in result.get("generated_files", [])]
    
    return {
        "conversation_id": conversation_id,
        "answer": result.get("answer"),
        "requires_follow_up": result.get("requires_follow_up", False),
        "generated_files": file_urls
    }

@app.post("/chat/start", response_model=ChatResponse, status_code=201)
async def start_chat(request: ChatRequest):
    """
    开启一个新的对话会话。
    """
    conversation_id = str(uuid.uuid4())
    print(f"--- 开启新会话: {conversation_id} ---")
    
    # 调用agent，不传递任何历史消息
    result = run_agent_conversation(user_prompt=request.query, messages=None)
    
    # 存储这次对话的完整历史记录
    conversations[conversation_id] = result.get("messages", [])
    
    return format_response(result, conversation_id)

@app.post("/chat/continue/{conversation_id}", response_model=ChatResponse)
async def continue_chat(conversation_id: str, request: ChatRequest):
    """
    继续一个已存在的对话会话。
    """
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation ID not found")
    
    print(f"--- 继续会话: {conversation_id} ---")

    # 获取之前的对话历史
    messages = conversations[conversation_id]
    
    # 调用agent，并传入历史消息
    result = run_agent_conversation(user_prompt=request.query, messages=messages)
    
    # 更新并存储对话历史
    conversations[conversation_id] = result.get("messages", [])
    
    return format_response(result, conversation_id)

# --- 静态文件服务 ---
# 挂载一个静态文件目录，用于提供生成的图片、shp等文件
app.mount("/outputs", StaticFiles(directory="."), name="outputs")

if __name__ == "__main__":
    # 使用 uvicorn 启动服务，监听在 8000 端口
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # 注意：直接运行此文件将不再启动服务器，正确的启动方式是
    # 在父目录运行: uvicorn SRTP.main:app --reload
    print("要启动服务器, 请在项目根目录运行: uvicorn SRTP.main:app --reload")