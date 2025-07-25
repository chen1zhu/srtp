import os
import json
import pandas as pd
from openai import OpenAI

# ==============================================================================
# 0. 配置和客户端设置
# ==============================================================================

# 定义输出目录 - 确保与main.py中的outputs目录一致
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 客户端设置：连接到 DeepSeek API
try:
    # 确保你已经设置了环境变量 DEEPSEEK_API_KEY
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1"
    )
except Exception as e:
    print("错误：请确保你已经设置了 DEEPSEEK_API_KEY 环境变量。")
    exit()

# ==============================================================================
# 1. 我们的工具函数：数据预处理 (无需修改，可直接使用)
# ==============================================================================
def preprocess_vehicle_data(filepath: str, point_type: str = None, start_time: str = None, end_time: str = None, bbox: list = None):
    """
    预处理XLSX格式的车辆轨迹点数据。
    它可以根据点类型（起点/终点）、时间范围和地理边界框进行筛选。
    
    :param filepath: 原始数据的文件路径 (XLSX格式)。
    :param point_type: 筛选的点类型。可选值为 'start' (起点), 'end' (终点)。默认为不过滤。
    :param start_time: 筛选的开始时间戳 (整数)。
    :param end_time: 筛选的结束时间戳 (整数)。
    :param bbox: 地理边界框，格式为 [min_lon, min_lat, max_lon, max_lat]。
    :return: 一个JSON字符串，包含处理结果的摘要。
    """
    def _convert_time_to_seconds(time_str: str) -> int:
        """将 HH:MM:SS 或秒字符串转换为当日秒数"""
        if time_str is None:
            return None
        try:
            return int(time_str)
        except ValueError:
            parts = list(map(int, time_str.split(':')))
            seconds = parts[0] * 3600
            if len(parts) > 1:
                seconds += parts[1] * 60
            if len(parts) > 2:
                seconds += parts[2]
            return seconds

    print(f"--- Python函数 `preprocess_vehicle_data` 被执行 ---")
    print(f"参数: filepath='{filepath}', point_type='{point_type}', start_time='{start_time}', end_time='{end_time}', bbox={bbox}")
    
    # 检查文件是否存在
    if not os.path.exists(filepath):
        print(f"错误：文件 '{filepath}' 不存在。请检查文件名和路径。")
        return json.dumps({"status": "error", "message": f"File not found: {filepath}"})

    try:
        column_names = ['timestamp', 'longitude', 'latitude', 'type', 'label']
        df = pd.read_excel(filepath, header=None, names=column_names, engine='openpyxl')
        original_rows = len(df)
        
        if point_type == 'start':
            df = df[df['type'] == 0]
        elif point_type == 'end':
            df = df[df['type'] == 1]
            
        start_seconds = _convert_time_to_seconds(start_time)
        end_seconds = _convert_time_to_seconds(end_time)

        if start_seconds is not None:
            df = df[df['timestamp'] >= start_seconds]
        if end_seconds is not None:
            df = df[df['timestamp'] <= end_seconds]
            
        if bbox and len(bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = bbox
            df = df[
                (df['longitude'] >= min_lon) & (df['longitude'] <= max_lon) &
                (df['latitude'] >= min_lat) & (df['latitude'] <= max_lat)
            ]
            
        filtered_rows = len(df)
        output_filename = os.path.join(OUTPUT_DIR, "filtered_" + os.path.splitext(os.path.basename(filepath))[0] + ".csv")
        df.to_csv(output_filename, index=False)
        
        result = {
            "status": "success",
            "original_rows": original_rows,
            "filtered_rows": filtered_rows,
            "output_filepath": os.path.basename(output_filename),  # 只返回文件名
            "filters_applied": {"point_type": point_type, "time_range": [start_time, end_time], "bbox": bbox}
        }
        
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        
    return json.dumps(result)

def kmeans_cluster(input_filepath: str, n_clusters: int = 8, output_shapefile: str = "cluster_results.shp"):
    """
    对给定的CSV数据进行K-Means聚类，并输出为Shapefile。

    :param input_filepath: 输入的CSV文件路径 (需要包含经纬度列，支持多种命名方式)。
    :param n_clusters: 要创建的聚类数量 (K值)。
    :param output_shapefile: 输出的Shapefile文件路径。
    :return: 包含聚类结果摘要的JSON字符串。
    """
    print(f"--- Python函数 `kmeans_cluster` 被执行 ---")
    print(f"参数: input_filepath='{input_filepath}', n_clusters={n_clusters}, output_shapefile='{output_shapefile}'")

    # 确保output_shapefile保存到outputs目录
    if not os.path.dirname(output_shapefile):
        output_shapefile = os.path.join(OUTPUT_DIR, output_shapefile)

    def _find_coordinate_columns(df):
        """
        自动识别经纬度列名
        返回 (longitude_col, latitude_col) 或 (None, None) 如果未找到
        """
        # 常见的经度列名
        longitude_aliases = ['longitude', 'lon', 'lng', 'long', 'x', 'X', 'Longitude', 'LON', 'LNG', 'LONG']
        # 常见的纬度列名  
        latitude_aliases = ['latitude', 'lat', 'y', 'Y', 'Latitude', 'LAT']
        
        longitude_col = None
        latitude_col = None
        
        # 查找经度列
        for col in df.columns:
            if col in longitude_aliases:
                longitude_col = col
                break
        
        # 查找纬度列
        for col in df.columns:
            if col in latitude_aliases:
                latitude_col = col
                break
                
        return longitude_col, latitude_col

    try:
        from sklearn.cluster import KMeans
        import geopandas as gpd

        # 读取数据
        df = pd.read_csv(input_filepath)
        
        # 自动识别经纬度列
        longitude_col, latitude_col = _find_coordinate_columns(df)
        
        if longitude_col is None or latitude_col is None:
            available_columns = list(df.columns)
            return json.dumps({
                "status": "error", 
                "message": f"无法识别经纬度列。可用列名: {available_columns}。支持的经度列名: longitude, lon, lng, long, x。支持的纬度列名: latitude, lat, y。"
            })
        
        print(f"   识别到经度列: '{longitude_col}', 纬度列: '{latitude_col}'")

        # 执行K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10)
        df['cluster'] = kmeans.fit_predict(df[[longitude_col, latitude_col]])

        # 创建GeoDataFrame
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df[longitude_col], df[latitude_col])
        )
        
        # 设置坐标参考系统 (WGS84)
        gdf.set_crs(epsg=4326, inplace=True)

        # 保存为Shapefile
        gdf.to_file(output_shapefile, driver='ESRI Shapefile')

        # 收集所有生成的 Shapefile 相关文件（返回相对路径）
        base_name = os.path.splitext(output_shapefile)[0]
        shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
        generated_shapefile_files = []
        for ext in shapefile_extensions:
            file_path = base_name + ext
            if os.path.exists(file_path):
                # 只返回文件名，不包含路径
                generated_shapefile_files.append(os.path.basename(file_path))

        # 准备结果摘要
        cluster_summary = df['cluster'].value_counts().to_dict()
        result = {
            "status": "success",
            "output_filepath": os.path.basename(output_shapefile), # 只返回文件名
            "generated_files": generated_shapefile_files, # 添加所有相关文件的列表
            "n_clusters": n_clusters,
            "cluster_point_counts": cluster_summary,
            "coordinate_columns_used": {"longitude": longitude_col, "latitude": latitude_col}
        }

    except ImportError as e:
        result = {"status": "error", "message": f"Missing required library: {e}. Please install scikit-learn and geopandas."}
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    return json.dumps(result)
def create_heatmap(input_filepath: str, output_image_path: str = "heatmap.png", map_title: str = "Taxies Hotspot Analysis Heatmap"):
    """
    根据输入的CSV点数据生成一张带有底图的热力图。

    :param input_filepath: 输入的CSV文件路径 (需要包含经纬度列，支持多种命名方式)。
    :param output_image_path: 输出的热力图图片文件路径 (PNG格式)。
    :param map_title: 地图的标题。
    :return: 包含操作状态和图片路径的JSON字符串。
    """
    print(f"--- Python函数 `create_heatmap` 被执行 ---")
    print(f"参数: input_filepath='{input_filepath}', output_image_path='{output_image_path}', map_title='{map_title}'")

    # 确保output_image_path保存到outputs目录
    if not os.path.dirname(output_image_path):
        output_image_path = os.path.join(OUTPUT_DIR, output_image_path)

    def _find_coordinate_columns(df):
        """
        自动识别经纬度列名
        返回 (longitude_col, latitude_col) 或 (None, None) 如果未找到
        """
        # 常见的经度列名
        longitude_aliases = ['longitude', 'lon', 'lng', 'long', 'x', 'X', 'Longitude', 'LON', 'LNG', 'LONG']
        # 常见的纬度列名  
        latitude_aliases = ['latitude', 'lat', 'y', 'Y', 'Latitude', 'LAT']
        
        longitude_col = None
        latitude_col = None
        
        # 查找经度列
        for col in df.columns:
            if col in longitude_aliases:
                longitude_col = col
                break
        
        # 查找纬度列
        for col in df.columns:
            if col in latitude_aliases:
                latitude_col = col
                break
                
        return longitude_col, latitude_col

    try:
        import geopandas as gpd
        import matplotlib.pyplot as plt
        import contextily as ctx
        import seaborn as sns

        # 从CSV创建GeoDataFrame
        df = pd.read_csv(input_filepath)
        
        # 自动识别经纬度列
        longitude_col, latitude_col = _find_coordinate_columns(df)
        
        if longitude_col is None or latitude_col is None:
            available_columns = list(df.columns)
            return json.dumps({
                "status": "error", 
                "message": f"无法识别经纬度列。可用列名: {available_columns}。支持的经度列名: longitude, lon, lng, long, x。支持的纬度列名: latitude, lat, y。"
            })
        
        print(f"   识别到经度列: '{longitude_col}', 纬度列: '{latitude_col}'")
        
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df[longitude_col], df[latitude_col])
        ).set_crs(epsg=4326)

        # 确保坐标系为Web Mercator (EPSG:3857) 以便匹配底图
        gdf = gdf.to_crs(epsg=3857)

        # 创建图表
        # 设置支持中文的字体
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体为黑体
        plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像是负号'-'显示为方块的问题

        fig, ax = plt.subplots(1, 1, figsize=(12, 12))

        # 使用seaborn的kdeplot创建核密度估计图
        sns.kdeplot(
            x=gdf.geometry.x,
            y=gdf.geometry.y,
            fill=True,
            cmap="Reds",
            alpha=0.5,
            ax=ax
        )
        
        # 添加底图
        # 定义并使用高德地图作为底图
        gaode_map_provider = {
            "url": "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            "attribution": "© 高德地图",
        }
        ctx.add_basemap(ax, source=gaode_map_provider['url'], crs=gdf.crs.to_string())

        # --- 添加地图元素 ---
        # 1. 添加比例尺
        from matplotlib_scalebar.scalebar import ScaleBar
        ax.add_artist(ScaleBar(1, location='lower right'))

        # 2. 添加指北针
        x, y, arrow_len = 0.95, 0.95, 0.07
        ax.annotate('N', xy=(x, y), xytext=(x, y - arrow_len),
                    arrowprops=dict(facecolor='black', width=4, headwidth=10),
                    ha='center', va='center', fontsize=20,
                    xycoords=ax.transAxes)

        # 设置标题和样式
        ax.set_title(map_title, fontsize=16)
        ax.set_axis_off() # 关闭坐标轴

        # 保存图表
        plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
        plt.close(fig) # 关闭图表以释放内存

        result = {
            "status": "success",
            "output_image_path": os.path.basename(output_image_path),  # 只返回文件名
        }

    except ImportError as e:
        result = {"status": "error", "message": f"Missing required library: {e}. Please install geopandas, matplotlib, contextily, and seaborn."}
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    return json.dumps(result)
def create_gif_from_images(image_files: list, output_gif_path: str = "animated_result.gif", fps: int = 2):
    """
    将一系列输入的图片文件合成为一个GIF动图。

    :param image_files: 一个包含输入图片文件路径的列表。
    :param output_gif_path: 输出的GIF文件路径。
    :param fps: 生成的GIF的帧率（每秒的帧数）。
    :return: 包含操作状态和GIF路径的JSON字符串。
    """
    print(f"--- Python函数 `create_gif_from_images` 被执行 ---")
    print(f"参数: image_files={image_files}, output_gif_path='{output_gif_path}', fps={fps}")

    # 确保output_gif_path保存到outputs目录
    if not os.path.dirname(output_gif_path):
        output_gif_path = os.path.join(OUTPUT_DIR, output_gif_path)

    try:
        from PIL import Image

        if not image_files:
            return json.dumps({"status": "error", "message": "Image file list cannot be empty."})

        frames = [Image.open(f) for f in image_files]
        
        if not frames:
            return json.dumps({"status": "error", "message": "Could not open any images from the provided list."})

        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=1000 / fps,
            loop=0
        )
        
        result = {"status": "success", "output_gif_path": os.path.basename(output_gif_path), "image_count": len(frames)}  # 只返回文件名

    except ImportError:
        result = {"status": "error", "message": "Missing required library: Pillow (PIL). Please install it."}
    except FileNotFoundError as e:
        result = {"status": "error", "message": f"File not found: {e.filename}"}
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    return json.dumps(result)
def visualize_clusters(input_shapefile: str, output_image_path: str = "cluster_visualization.png", map_title: str = "Cluster Analysis Visualization"):
    """
    根据输入的Shapefile点数据（包含'cluster'字段），生成一张带有底图、指北针和比例尺的可视化图。

    :param input_shapefile: 输入的Shapefile文件路径，必须包含 'cluster' 字段。
    :param output_image_path: 输出的图片文件路径 (PNG格式)。
    :param map_title: 地图的标题。
    :return: 包含操作状态和图片路径的JSON字符串。
    """
    print(f"--- Python函数 `visualize_clusters` 被执行 ---")
    print(f"参数: input_shapefile='{input_shapefile}', output_image_path='{output_image_path}', map_title='{map_title}'")

    # 确保output_image_path保存到outputs目录
    if not os.path.dirname(output_image_path):
        output_image_path = os.path.join(OUTPUT_DIR, output_image_path)

    try:
        import geopandas as gpd
        import matplotlib.pyplot as plt
        import contextily as ctx
        from matplotlib_scalebar.scalebar import ScaleBar

        # 读取Shapefile
        gdf = gpd.read_file(input_shapefile)
        if 'cluster' not in gdf.columns:
            return json.dumps({"status": "error", "message": "Input Shapefile must contain a 'cluster' column."})

        # 确保坐标系为Web Mercator (EPSG:3857)
        gdf = gdf.to_crs(epsg=3857)

        # --- 绘图 ---
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))

        # 按 'cluster' 列对点进行分类着色
        gdf.plot(column='cluster', ax=ax, legend=True, markersize=10, cmap='tab20', categorical=True)
        
        # 添加高德底图
        gaode_map_provider = {
            "url": "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            "attribution": "© 高德地图",
        }
        ctx.add_basemap(ax, source=gaode_map_provider['url'], crs=gdf.crs.to_string())
        
        # --- 添加地图元素 ---
        # 1. 添加比例尺
        ax.add_artist(ScaleBar(1, location='lower right'))

        # 2. 添加指北针
        x, y, arrow_len = 0.95, 0.95, 0.07
        ax.annotate('N', xy=(x, y), xytext=(x, y - arrow_len),
                    arrowprops=dict(facecolor='black', width=4, headwidth=10),
                    ha='center', va='center', fontsize=20,
                    xycoords=ax.transAxes)

        # --- 设置标题和样式 ---
        ax.set_title(map_title, fontsize=16)
        ax.set_axis_off()

        # 保存图表
        plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        result = {"status": "success", "output_image_path": os.path.basename(output_image_path)}  # 只返回文件名

    except ImportError as e:
        result = {"status": "error", "message": f"Missing required library: {e}. Please install matplotlib-scalebar."}
    except Exception as e:
        result = {"status": "error", "message": str(e)}

    return json.dumps(result)
# ==============================================================================
# 2. 为LLM定义工具的描述 (无需修改)
# ==============================================================================
tools_description = [
    {
        "type": "function",
        "function": {
            "name": "preprocess_vehicle_data",
            "description": "根据用户指定的点类型（起点或终点）、时间戳范围或地理位置，对车辆轨迹XLSX数据进行预处理和筛选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": { "type": "string", "description": "需要处理的源数据XLSX文件路径，例如 'my_vehicle_data.xlsx'。"},
                    "point_type": { "type": "string", "description": "要筛选的点的类型。'start' 代表起点 (type=0)，'end' 代表终点 (type=1)。", "enum": ["start", "end"]},
                    "start_time": { "type": "string", "description": "筛选数据的开始时间。可以是代表“当日秒数”的整数（如 '3600'），也可以是“HH:MM:SS”格式的字符串（如 '08:00:00'）。"},
                    "end_time": { "type": "string", "description": "筛选数据的结束时间。可以是代表“当日秒数”的整数（如 '7200'），也可以是“HH:MM:SS”格式的字符串（如 '09:30:00'）。"},
                    "bbox": { "type": "array", "description": "地理边界框，一个包含四个数字的列表：[最小经度, 最小纬度, 最大经度, 最大纬度]。", "items": {"type": "number"}}
                },
                "required": ["filepath"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kmeans_cluster",
            "description": "对地理坐标数据进行K-Means聚类分析。自动识别经纬度列（支持longitude/lon/lng/long/x和latitude/lat/y等多种命名方式）。如果用户没有指定聚类数量(n_clusters)，你必须向用户提问以获取此信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_filepath": { "type": "string", "description": "包含经纬度列的输入CSV文件的路径。函数会自动识别常见的经纬度列名（如longitude/lon/lng/long/x和latitude/lat/y等）。通常是数据预处理步骤的输出。"},
                    "n_clusters": { "type": "integer", "description": "要形成的聚类数量（K值）。"},
                    "output_shapefile": { "type": "string", "description": "输出的Shapefile文件的路径，例如 'clusters.shp'。"}
                },
                "required": ["input_filepath"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_heatmap",
            "description": "基于输入的CSV点数据，生成一张带有在线地图背景的热力图，并保存为PNG图片。自动识别经纬度列（支持多种命名方式）。用于地理空间数据的可视化分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_filepath": { "type": "string", "description": "输入的点数据CSV文件路径。函数会自动识别常见的经纬度列名（如longitude/lon/lng/long/x和latitude/lat/y等）。通常是数据预处理步骤的输出。"},
                    "output_image_path": { "type": "string", "description": "输出的热力图图片文件路径。例如, 'heatmap.png'。"},
                    "map_title": { "type": "string", "description": "要显示在热力图顶部的标题。"}
                },
                "required": ["input_filepath"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_gif_from_images",
            "description": "将一个图片文件路径列表中的所有图片合成为一个GIF动图。用于创建数据随时间变化的动态可视化。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_files": {
                        "type": "array",
                        "description": "一个包含按顺序排列的、要被合并成GIF的图片文件路径的列表。",
                        "items": {"type": "string"}
                    },
                    "output_gif_path": { "type": "string", "description": "输出的GIF文件的路径。例如, 'animation.gif'。"},
                    "fps": { "type": "integer", "description": "GIF的帧率（每秒播放的图片数量），决定了动画的速度。"}
                },
                "required": ["image_files", "output_gif_path"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_clusters",
            "description": "为K-Means聚类的结果（一个Shapefile）生成一张带有底图、指北针和比例尺的、按不同颜色区分簇的可视化图片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_shapefile": { "type": "string", "description": "输入的点数据Shapefile文件路径, 必须包含'cluster'列。通常是kmeans_cluster函数的输出。"},
                    "output_image_path": { "type": "string", "description": "输出的可视化图片文件路径。例如, 'cluster_map.png'。"},
                    "map_title": { "type": "string", "description": "要显示在图片顶部的标题。"}
                },
                "required": ["input_shapefile"],
            },
        }
    }
]

# ==============================================================================
# 3. 主流程：与 DeepSeek V2 模型交互
# ==============================================================================
def run_agent_conversation(user_prompt: str, messages: list = None):
    """
    运行一个可能包含多轮对话的Agent流程。

    :param user_prompt: 用户的当前请求字符串。
    :param messages: 之前的对话历史。如果为None，则开始一个新对话。
    :return: 一个字典，包含模型的回答、是否需要继续对话，以及当前的对话历史。
    """
    if messages is None:
        print("--- 开启新对话 ---")
        # 为模型设置角色和行为准则
        system_prompt = (
            "你是一个专业的、友好的地理空间分析AI助手。"
            "你的任务是帮助用户分析地理数据。"
            "当用户的指令不明确或缺少执行工具所需的必要参数时，你必须向用户提问以澄清问题。"
            "在调用任何工具之前，请确保所有必需的参数都已从用户那里获得。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    else:
        print("--- 继续对话 ---")
        messages.append({"role": "user", "content": user_prompt})

    print(f"\n👤 用户: {user_prompt}\n")
    generated_files = []

    print("🤖 正在向 DeepSeek V2 发送请求...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools_description,
        tool_choice="auto",
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    while True:
        if not tool_calls:
            final_answer = response_message.content
            # 检查这是否是一个问题
            is_question = "?" in final_answer or "？" in final_answer
            if is_question:
                print(f"\n🤔 模型提出问题: {final_answer}")
            else:
                print(f"\n✅ DeepSeek V2 最终的回答:\n\n{final_answer}")
            
            messages.append({"role": "assistant", "content": final_answer})
            return {
                "answer": final_answer,
                "generated_files": list(set(generated_files)),
                "requires_follow_up": is_question,
                "messages": messages
            }

        print("✅ DeepSeek V2 决定调用一个或多个函数！")
        # 将模型的工具调用决策添加到历史记录中
        messages.append(response_message.model_dump())
        
        # 执行所有工具调用
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments)
                print(f"   - 函数名: {function_name}")
                print(f"   - 模型解析出的参数: {function_args}")

                available_functions = {
                    "preprocess_vehicle_data": preprocess_vehicle_data,
                    "kmeans_cluster": kmeans_cluster,
                    "create_heatmap": create_heatmap,
                    "create_gif_from_images": create_gif_from_images,
                    "visualize_clusters": visualize_clusters,
                }
                function_to_call = available_functions.get(function_name)
                
                if function_to_call:
                    function_response_str = function_to_call(**function_args)
                    response_data = json.loads(function_response_str)

                    # 收集所有输出的文件路径
                    for key, value in response_data.items():
                        if 'path' in key and isinstance(value, str):
                            generated_files.append(value)
                        elif key == 'generated_files' and isinstance(value, list):
                            generated_files.extend(value)
                    
                    if response_data.get("status") == "error":
                        print(f"❌ 函数执行失败: {response_data.get('message')}")
                    
                    # 将成功的工具执行结果添加到历史记录
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response_str,
                    })
                else:
                    raise ValueError(f"未知函数: {function_name}")

            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
                # 如果参数解析失败或函数执行出错，向模型报告错误
                print(f"❌ 调用函数 '{function_name}' 时出错: {e}")
                error_message = f"Error calling function {function_name}: {str(e)}. Please check your arguments."
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"status": "error", "message": error_message}),
                })
                # 跳过本次循环中剩余的工具调用，让模型根据错误报告决定下一步
                break
        
        print("\n🔄 已执行本地函数，将结果返回给 DeepSeek V2 以决定下一步...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools_description,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

if __name__ == '__main__':
    # --- 模拟一个多轮对话场景 ---
    # 1. 用户发起一个不完整的请求
    initial_prompt = f"你好，请使用 'SRTP/20200101_binjiang_point.xlsx' 文件帮我对起点数据做个聚类分析。"
    
    # 2. 第一次调用agent
    conversation_history = None
    result = run_agent_conversation(initial_prompt, conversation_history)
    conversation_history = result['messages']

    # 3. 检查agent是否需要追问
    if result['requires_follow_up']:
        print("\n--- 需要用户提供更多信息 ---")
        # 4. 模拟用户回答问题
        user_response = "好的，请帮我分成5类。"
        
        # 5. 带着用户的回答和对话历史，再次调用agent
        result = run_agent_conversation(user_response, conversation_history)
        conversation_history = result['messages']

    # --- 最终结果 ---
    print("\n\n===== 对话结束 =====")
    if not result['requires_follow_up']:
        print(f"最终回答: {result['answer']}")
        if result['generated_files']:
            print(f"生成的文件: {result['generated_files']}")
    else:
        print(f"对话未完成，模型仍在提问: {result['answer']}")

