# 会话式地理空间分析AI代理后端服务

本项目是一个基于 FastAPI 和大语言模型（LLM）的后端服务，旨在提供一个能够通过自然语言多轮对话进行复杂地理空间数据分析的智能代理。

## ✨ 功能特性

- **自然语言交互**: 用户可以通过普通对话（如 "帮我分析一下数据"）来驱动复杂的分析流程。
- **多轮对话能力**: 如果用户的指令缺少必要参数（例如，要求聚类但未指定类别数），代理会主动提问以获取信息，而不是猜测或报错。
- **丰富的地理空间分析工具**:
  - **数据预处理**: 根据时间、类型、地理范围筛选数据。
  - **K-Means 聚类**: 识别数据点的空间聚集模式。
  - **热力图生成**: 可视化空间点的密度分布。
  - **GIF 动画合成**: 将多张图片合成为动态可视化结果。
- **可扩展的工具集**: 可以方便地添加更多分析函数作为新工具。

## 🛠️ 技术栈

- **Web框架**: FastAPI
- **数据处理**: Pandas, GeoPandas
- **机器学习**: Scikit-learn
- **地理可视化**: Matplotlib, Seaborn, Contextily, Matplotlib-Scalebar
- **AI模型驱动**: OpenAI SDK (连接到 DeepSeek API)
- **环境管理**: Conda

## ⚙️ 环境设置

### 1. Conda 环境

本项目依赖于一个名为 `devgis` 的 Conda 环境。请按以下步骤创建和激活环境：

```bash
# 创建环境
conda create -n devgis python=3.11 -y

# 激活环境
conda activate devgis
```

### 2. 安装依赖

大部分地理空间相关的库需要从 `conda-forge` 渠道安装，以确保兼容性。

```bash
# 安装核心地理空间库
conda install -c conda-forge geopandas shapely fiona rasterio pyproj rtree -y

# 安装其他Python库
pip install openai "uvicorn[standard]" fastapi pandas openpyxl matplotlib seaborn contextily matplotlib-scalebar Pillow scikit-learn
```

### 3. 设置API密钥

本项目需要连接到 DeepSeek 的 API。请在您的系统中设置一个环境变量 `DEEPSEEK_API_KEY`。

- **Windows (CMD)**:
  ```cmd
  setx DEEPSEEK_API_KEY "你的API密钥"
  ```
  *注意：设置后需要重启终端才能生效。*

- **Linux / macOS**:
  ```bash
  export DEEPSEEK_API_KEY="你的API密钥"
  ```
  *可以将其添加到 `~/.bashrc` 或 `~/.zshrc` 中以永久生效。*

## 🚀 如何运行

在项目根目录下，使用以下命令启动后端服务：

```bash
# 确保你已经激活了 devgis 环境
conda activate devgis

# 启动 Uvicorn 服务器
uvicorn SRTP.main:app --reload --host 0.0.0.0 --port 8000
```

服务器将在 `http://localhost:8000` 上运行。`--reload` 参数会在代码变更后自动重启服务，非常适合开发环境。

## 📚 API 文档

API 提供了两个核心端点来管理对话。

### 1. 开启新对话

- **Endpoint**: `POST /chat/start`
- **Status Code**: `201 Created`
- **描述**: 用于发起一个全新的对话。客户端发送第一个用户请求，服务器会创建一个唯一的 `conversation_id` 并返回第一轮的分析结果。
- **请求体 (Request Body)**:
  ```json
  {
    "query": "你好，请使用 'SRTP/20200101_binjiang_point.xlsx' 文件帮我做个聚类分析。"
  }
  ```
- **成功响应 (Success Response)**:
  ```json
  {
    "conversation_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "answer": "很好！...但我需要知道你希望将这些起点聚成多少个类别？...",
    "requires_follow_up": true,
    "generated_files": [
      "http://localhost:8000/outputs/filtered_file.csv"
    ]
  }
  ```

### 2. 继续对话

- **Endpoint**: `POST /chat/continue/{conversation_id}`
- **描述**: 用于在已有对话的基础上进行下一轮交互。客户端需要在URL中提供从 `/chat/start` 获取的 `conversation_id`。
- **路径参数 (Path Parameter)**:
  - `conversation_id` (string, required): 对话的唯一标识符。
- **请求体 (Request Body)**:
  ```json
  {
    "query": "好的，请帮我分成5类。"
  }
  ```
- **成功响应 (Success Response)**:
  ```json
  {
    "conversation_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "answer": "完成！我已经成功完成了对...数据的K-Means聚类分析...",
    "requires_follow_up": false,
    "generated_files": [
      "http://localhost:8000/outputs/filtered_file.csv",
      "http://localhost:8000/outputs/clusters.shp",
      "http://localhost:8000/outputs/cluster_map.png"
    ]
  }
  ```

### 3. 错误响应

如果提供的 `conversation_id` 无效，服务器将返回 `404 Not Found`。

```json
{
  "detail": "Conversation ID not found"
}
```

### 4. 访问生成的文件

所有由分析过程生成的文件（如 `.png`, `.gif`, `.csv`, `.shp` 等）都可以通过 `/outputs/` 路径访问。URL 由 API 响应中的 `generated_files` 字段提供。

例如: `http://localhost:8000/outputs/cluster_map.png`

## 🔄 多轮对话流程示例 (前端逻辑)

前端需要管理一个简单的状态机来处理对话的交互性。

1.  **发起请求**: 用户输入第一个问题后，前端向 `POST /chat/start` 发送请求。
2.  **渲染回复**: 前端显示 API 响应中的 `answer` 文本。
3.  **检查是否追问**:
    - 如果响应中的 `requires_follow_up` 字段为 `true`，说明 AI 代理正在等待用户提供更多信息。此时，前端应该保持输入框为激活状态，等待用户输入下一句话。
    - 如果 `requires_follow_up` 为 `false`，说明当前任务已经完成。
4.  **继续对话**: 当用户输入了补充信息后，前端将新的输入和第一步获取的 `conversation_id` 一起发送到 `POST /chat/continue/{conversation_id}`。
5.  **循环**: 重复步骤 2-4，直到 `requires_follow_up` 为 `false`。

这个流程确保了用户可以与 AI 代理进行流畅、自然的澄清式对话。