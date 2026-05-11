import os
from openai import OpenAI

# 定义输出目录 - 确保与 main.py 中的 outputs 目录一致
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )
except Exception:
    print("错误：请确保你已经设置了 DEEPSEEK_API_KEY 环境变量。")
    raise


def call_llm_for_section(prompt: str) -> str:
    """调用 LLM 生成报告所需的单个章节内容。"""
    print("   - 调用LLM生成文本部分...")
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3-4b:free",
            messages=[
                {"role": "system", "content": "你是一位专业的GIS分析报告撰写者。请根据用户的提示，撰写专业、详细、内容丰富的报告部分。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as exc:
        error_message = f"内容生成失败: {exc}"
        print(f"   - LLM调用失败: {exc}")
        return error_message

# JWT / auth 配置（用于本地开发）
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-prod-please-set-a-strong-secret-32+")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
