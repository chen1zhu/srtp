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

def analyze_image_sequence(image_paths: list[str]):
    """
    接收一个图片路径列表，并使用OpenRouter的Qwen视觉AI模型进行时序分析。

    :param image_paths: 要按顺序分析的图片文件的路径列表。
    :return: 模型的文本分析结果。
    """
    print(f"--- 正在分析图片序列 ---")
    
    images_for_api = []
    for image_path in image_paths:
        if not os.path.exists(image_path):
            print(f"警告: 文件 '{image_path}' 不存在，已跳过。")
            continue
        try:
            # 动态识别MIME类型
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/png"  # 如果无法识别，默认为png

            # 读取并编码图片
            with open(image_path, "rb") as image_file:
                base64_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            images_for_api.append({"mime_type": mime_type, "base64": base64_string})
            print(f"   - 文件 '{image_path}' 已成功编码 (类型: {mime_type})。")
        except Exception as e:
            print(f"错误: 处理文件 '{image_path}' 时出错: {e}")

    if not images_for_api:
        print("错误：没有可供分析的有效图片。")
        return

    # 准备发送给模型的请求
    # 准备发送给模型的请求内容
    content = [
        {
            "type": "text",
            "text": "你是一位专业的GIS（地理信息系统）分析师。这里有几张代表不同时间点的热力图图片，已按时间顺序排列。请你仔细分析这些图片，并详细描述从第一张到最后一张，热力点的空间分布发生了哪些显著的变化趋势？例如：热点区域是如何移动、扩大或缩小的？是否有新的热点出现或消失？请根据图片内容进行回答。"
        }
    ]

    # 将所有编码后的图片添加到请求中
    for image_data in images_for_api:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image_data['mime_type']};base64,{image_data['base64']}"
            }
        })

    messages = [{"role": "user", "content": content}]

    # 发送请求到视觉模型
    try:
        print("   - 正在向OpenRouter (Qwen)视觉模型发送请求...")
        response = client.chat.completions.create(
            temperature=0.8,  # 降低模型的随机性
            model="qwen/qwen2.5-vl-32b-instruct",
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
    # ==========================================================================
    # 请在这里修改你要分析的图片文件名列表！
    # ==========================================================================
    image_filenames = [
        "heatmap_0800_1000.png",  # 示例：请替换为你的文件名
        "heatmap_1000_1200.png",  # 示例：请替换为你的文件名
        "heatmap_1200_1400.png"   # 示例：请替换为你的文件名
    ]
    # ==========================================================================
    
    # 获取脚本所在的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建完整的图片路径列表
    image_paths_to_test = [os.path.join(script_dir, OUTPUT_DIR, fname) for fname in image_filenames]

    # 调用函数进行分析
    analyze_image_sequence(image_paths_to_test)