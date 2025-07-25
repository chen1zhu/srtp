import uvicorn
import uuid
import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json

# 从我们的代理脚本中导入核心功能
from .deepseek_agent import run_agent_conversation

app = FastAPI(
    title="Conversational Geo-Analysis AI Agent API",
    description="一个能通过多轮对话与用户交互，进行地理空间数据分析的智能代理。",
    version="1.1.0",
)

# 配置CORS中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境建议限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# --- 会话存储 (用于演示，生产环境应使用Redis, DB等) ---
conversations: Dict[str, List[Dict]] = {}

# 创建上传文件目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

async def _handle_file_upload(file: Optional[UploadFile], query: Optional[str], conversation_id: str) -> str:
    """处理文件上传的辅助函数"""
    if file:
        # 保存上传的文件
        file_path = os.path.join(UPLOAD_DIR, f"{conversation_id}_{file.filename}")
        
        print(f"保存上传文件: {file.filename} -> {file_path}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 将文件路径添加到查询中，让AI知道有文件需要处理
        if query and query.strip():
            user_prompt = f"{query}\n\n[上传的文件路径: {file_path}]"
        else:
            user_prompt = f"请分析上传的文件: {file_path}"
    else:
        user_prompt = query or ""
    
    return user_prompt

@app.post("/chat/start", response_model=ChatResponse, status_code=201)
async def start_chat(
    request: Request,
    file: Optional[UploadFile] = File(None),
    query: Optional[str] = Form(None)
):
    """
    开启一个新的对话会话。支持文件上传和纯文本请求。
    """
    conversation_id = str(uuid.uuid4())
    print(f"--- 开启新会话: {conversation_id} ---")
    
    # 检查请求的Content-Type来判断请求格式
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # FormData请求（有文件上传）
        print("处理FormData请求")
        user_prompt = await _handle_file_upload(file, query, conversation_id)
    elif "application/json" in content_type:
        # JSON请求（纯文本）
        print("处理JSON请求")
        body = await request.body()
        json_data = json.loads(body)
        user_prompt = json_data.get("query", "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")
    
    # 调用agent，不传递任何历史消息
    result = run_agent_conversation(user_prompt=user_prompt, messages=None)
    
    # 存储这次对话的完整历史记录
    conversations[conversation_id] = result.get("messages", [])
    
    return format_response(result, conversation_id)

@app.post("/chat/continue/{conversation_id}", response_model=ChatResponse)
async def continue_chat(
    conversation_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    query: Optional[str] = Form(None)
):
    """
    继续一个已存在的对话会话。支持文件上传和纯文本请求。
    """
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation ID not found")
    
    print(f"--- 继续会话: {conversation_id} ---")

    # 检查请求的Content-Type来判断请求格式
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # FormData请求（有文件上传）
        print("处理FormData请求")
        user_prompt = await _handle_file_upload(file, query, conversation_id)
    elif "application/json" in content_type:
        # JSON请求（纯文本）
        print("处理JSON请求")
        body = await request.body()
        json_data = json.loads(body)
        user_prompt = json_data.get("query", "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    # 获取之前的对话历史
    messages = conversations[conversation_id]
    
    # 调用agent，并传入历史消息
    result = run_agent_conversation(user_prompt=user_prompt, messages=messages)
    
    # 更新并存储对话历史
    conversations[conversation_id] = result.get("messages", [])
    
    return format_response(result, conversation_id)

# --- 静态文件服务 ---
# 挂载静态文件目录，用于提供生成的图片、shp等文件
app.mount("/outputs", StaticFiles(directory="."), name="outputs")
# 挂载上传文件目录，用于提供上传的文件
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

if __name__ == "__main__":
    # 使用 uvicorn 启动服务，监听在 8000 端口
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # 注意：直接运行此文件将不再启动服务器，正确的启动方式是
    # 在父目录运行: uvicorn SRTP.main:app --reload
    print("要启动服务器, 请在项目根目录运行: uvicorn SRTP.main:app --reload")