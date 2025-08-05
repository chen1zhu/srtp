import os
import base64
from openai import OpenAI
import mimetypes

# ==============================================================================
# 1. 配置和客户端设置
# ==============================================================================

# 从环境变量中获取API Key，并连接到OpenRouter API
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "https://github.com/StartPoint-AI/GIS-Agent", # 推荐填写你的项目地址
            "X-Title": "GIS-Agent Vision Test", # 推荐填写你的项目名称
        },
    )
except Exception as e:
    print("错误：请确保你已经设置了 OPENROUTER_API_KEY 环境变量。")
    exit()

# 定义包含GIF文件的目录
OUTPUT_DIR = "outputs"

# ==============================================================================
# 2. 图像分析函数
# ==============================================================================

def analyze_gif_with_vision(gif_path: str):
    """
    使用OpenRouter的Qwen视觉AI模型分析GIF动图。

    :param gif_path: 要分析的GIF文件的路径。
    :return: 模型的文本分析结果。
    """
    print(f"--- 正在分析GIF文件: {gif_path} ---")

    # 检查文件是否存在
    if not os.path.exists(gif_path):
        error_message = f"错误: 文件 '{gif_path}' 不存在。"
        print(error_message)
        return error_message

    # 将GIF文件编码为Base64
    try:
        # 自动识别MIME类型
        mime_type, _ = mimetypes.guess_type(gif_path)
        if mime_type is None:
            mime_type = "image/gif" # 默认值

        with open(gif_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        print(f"   - 文件已成功编码为Base64字符串。")
        print(f"   - MIME Type: {mime_type}")

    except Exception as e:
        error_message = f"错误: 编码文件时出错: {e}"
        print(error_message)
        return error_message

    # 准备发送给模型的请求
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "这是一个城市交通热力图随时间变化的GIF。请你分析这个动图，并描述热力点的空间分布变化趋势。例如，热点区域是如何移动、扩大或缩小的？"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    # 发送请求到视觉模型
    try:
        print("   - 正在向OpenRouter (Qwen)视觉模型发送请求...")
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-32B-Instruct",  # 使用Qwen 2.5 视觉模型
            messages=messages,
            max_tokens=2048
        )
        analysis_result = response.choices[0].message.content
        print("\n✅ AI分析结果:\n")
        print(analysis_result)
        return analysis_result

    except Exception as e:
        error_message = f"错误: 调用API时出错: {e}"
        print(error_message)
        return error_message

# ==============================================================================
# 3. 测试入口
# ==============================================================================

if __name__ == '__main__':
    # 假设这是我们之前生成的GIF动画
    # 注意：运行此脚本时，请确保工作目录是 srtp/backend/
    gif_to_test = os.path.join(OUTPUT_DIR, "start_points_heatmap_animation.gif")
    
    # 检查文件是否存在于 `outputs` 目录中。
    if not os.path.exists(gif_to_test):
        print(f"测试失败：找不到用于测试的GIF文件 '{gif_to_test}'。")
        print("请先运行主程序生成一个名为 'start_points_heatmap_animation.gif' 的文件并将其放在 'outputs' 文件夹中。")
    else:
        analyze_gif_with_vision(gif_to_test)