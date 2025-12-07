import logging
import os
import shutil
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# 从我们的代理脚本中导入核心功能
from .deepseek_agent import run_agent_conversation, run_agent_conversation_stream

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
    expose_headers=["X-Conversation-ID"],  # 允许前端读取自定义会话ID响应头
)

# --- 会话存储 (用于演示，生产环境应使用Redis, DB等) ---
# 每个会话维护两部分：对话历史(messages)与生成文件列表(generated_files)
ConversationState = Dict[str, Any]
conversations: Dict[str, ConversationState] = {}

# 创建上传文件目录
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
#创建下载文件目录
os.makedirs(OUTPUT_DIR,exist_ok=True)

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
        
        logger.info("[upload] 保存文件: %s -> %s", file.filename, file_path)
        
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
    logger.info("[HTTP] /chat/start 新会话: %s", conversation_id)
    
    # 检查请求的Content-Type来判断请求格式
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # FormData请求（有文件上传）
        logger.debug("[HTTP] 会话 %s 使用 multipart/form-data", conversation_id)
        user_prompt = await _handle_file_upload(file, query, conversation_id)
    elif "application/json" in content_type:
        # JSON请求（纯文本）
        logger.debug("[HTTP] 会话 %s 使用 application/json", conversation_id)
        body = await request.body()
        json_data = json.loads(body)
        user_prompt = json_data.get("query", "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")
    
    # 调用agent，不传递任何历史消息
    result = run_agent_conversation(user_prompt=user_prompt, messages=None)
    
    # 存储这次对话的完整历史记录和生成文件
    conversations[conversation_id] = {
        "messages": result.get("messages", []),
        "generated_files": result.get("generated_files", []),
    }
    logger.info(
        "[HTTP] /chat/start 完成: %s, requires_follow_up=%s",
        conversation_id,
        result.get("requires_follow_up"),
    )
    
    return format_response(result, conversation_id)

@app.post("/chat/stream/start")
async def start_chat_stream(
    request: Request,
    file: Optional[UploadFile] = File(None),
    query: Optional[str] = Form(None)
):
    """开启新会话的流式接口 (SSE-like)。前端使用 fetch(EventSource polyfill) 逐事件解析。"""
    conversation_id = str(uuid.uuid4())
    logger.info("[HTTP] /chat/stream/start 新会话: %s", conversation_id)
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        logger.debug("[HTTP] 流式会话 %s 使用 multipart/form-data", conversation_id)
        user_prompt = await _handle_file_upload(file, query, conversation_id)
    elif "application/json" in content_type:
        logger.debug("[HTTP] 流式会话 %s 使用 application/json", conversation_id)
        body = await request.body()
        json_data = json.loads(body)
        user_prompt = json_data.get("query", "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    session_files: List[str] = []
    last_state: Optional[Dict[str, Any]] = None

    def event_stream():
        nonlocal last_state
        for event in run_agent_conversation_stream(
            user_prompt=user_prompt,
            messages=None,
            session_generated_files=session_files,
        ):
            # 将事件编码为 text/event-stream 格式
            yield f"event: {event['event']}\n"
            yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            if event['event'] == 'final_answer':
                last_state = event['data']
        # 结束
        if last_state:
            conversations[conversation_id] = {
                "messages": last_state.get('messages', []),
                "generated_files": last_state.get('generated_files', session_files),
            }
            logger.info("[HTTP] /chat/stream/start 完成: %s", conversation_id)

    # 由于生成器最终 return 的dict我们拿不到，这里后续如果需要也可扩展消息通道
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"X-Conversation-ID": conversation_id})

@app.post("/chat/stream/continue/{conversation_id}")
async def continue_chat_stream(
    conversation_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    query: Optional[str] = Form(None)
):
    if conversation_id not in conversations:
        logger.warning("[HTTP] 未找到会话 %s", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation ID not found")
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        logger.debug("[HTTP] /chat/stream/continue %s 使用 multipart/form-data", conversation_id)
        user_prompt = await _handle_file_upload(file, query, conversation_id)
    elif "application/json" in content_type:
        logger.debug("[HTTP] /chat/stream/continue %s 使用 application/json", conversation_id)
        body = await request.body()
        json_data = json.loads(body)
        user_prompt = json_data.get("query", "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    state = conversations[conversation_id]
    history = state.get("messages", [])
    session_files = state.setdefault("generated_files", [])

    def event_stream():
        last_result = None
        for event in run_agent_conversation_stream(
            user_prompt=user_prompt,
            messages=history,
            session_generated_files=session_files,
        ):
            yield f"event: {event['event']}\n"
            yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            if event['event'] == 'final_answer':
                last_result = event['data']
        # 结束
        if last_result:
            state['messages'] = last_result.get('messages', history)
            state['generated_files'] = last_result.get('generated_files', session_files)
            logger.info("[HTTP] /chat/stream/continue 完成: %s", conversation_id)
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"X-Conversation-ID": conversation_id})

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
        logger.warning("[HTTP] 未找到会话 %s", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation ID not found")
    
    logger.info("[HTTP] /chat/continue 会话: %s", conversation_id)

    # 检查请求的Content-Type来判断请求格式
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # FormData请求（有文件上传）
        logger.debug("[HTTP] /chat/continue %s 使用 multipart/form-data", conversation_id)
        user_prompt = await _handle_file_upload(file, query, conversation_id)
    elif "application/json" in content_type:
        # JSON请求（纯文本）
        logger.debug("[HTTP] /chat/continue %s 使用 application/json", conversation_id)
        body = await request.body()
        json_data = json.loads(body)
        user_prompt = json_data.get("query", "")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    # 获取之前的对话历史与会话文件
    state = conversations[conversation_id]
    messages = state.get("messages", [])
    session_files = state.setdefault("generated_files", [])
    
    # 调用agent，并传入历史消息
    result = run_agent_conversation(
        user_prompt=user_prompt,
        messages=messages,
        session_generated_files=session_files,
    )
    
    # 更新并存储对话历史与生成文件
    state["messages"] = result.get("messages", messages)
    state["generated_files"] = result.get("generated_files", session_files)
    
    logger.info("[HTTP] /chat/continue 完成: %s", conversation_id)
    return format_response(result, conversation_id)

# --- 静态文件服务 ---
# 挂载静态文件目录，用于提供生成的图片、shp等文件
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
# 挂载上传文件目录，用于提供上传的文件
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

if __name__ == "__main__":
    # 使用 uvicorn 启动服务，监听在 8000 端口
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

    print("要启动服务器, 请在项目根目录运行: uvicorn backend.main:app --reload")