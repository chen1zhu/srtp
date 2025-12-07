from . import __init__  # noqa: F401

from ..reporting.report_builder import generate_analysis_report
from ..tools.analytics import (
    create_gif_from_images,
    create_heatmap,
    kmeans_cluster,
    visualize_clusters,
)
from ..tools.preprocessing import get_overall_bounds, preprocess_vehicle_data

available_functions = {
    "preprocess_vehicle_data": preprocess_vehicle_data,
    "get_overall_bounds": get_overall_bounds,
    "kmeans_cluster": kmeans_cluster,
    "create_heatmap": create_heatmap,
    "create_gif_from_images": create_gif_from_images,
    "visualize_clusters": visualize_clusters,
    "generate_analysis_report": generate_analysis_report,
}


tools_description = [
    {
        "type": "function",
        "function": {
            "name": "preprocess_vehicle_data",
            "description": "根据用户指定的点类型（起点或终点）、时间戳范围或地理位置，对车辆轨迹XLSX数据进行预处理和筛选。此函数还会生成并返回一个包含数据地理范围的JSON文件的路径，用于后续的地图生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "需要处理的源数据XLSX文件路径，例如 'my_vehicle_data.xlsx'。"},
                    "point_type": {
                        "type": "string",
                        "description": "要筛选的点的类型。'start' 代表起点 (type=0)，'end' 代表终点 (type=1)。",
                        "enum": ["start", "end"],
                    },
                    "start_time": {
                        "type": "string",
                        "description": "筛选数据的开始时间。可以是代表“当日秒数”的整数（如 '3600'），也可以是“HH:MM:SS”格式的字符串（如 '08:00:00'）。",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "筛选数据的结束时间。可以是代表“当日秒数”的整数（如 '7200'），也可以是“HH:MM:SS”格式的字符串（如 '09:30:00'）。",
                    },
                    "bbox": {
                        "type": "array",
                        "description": "地理边界框，一个包含四个数字的列表：[最小经度, 最小纬度, 最大经度, 最大纬度]。",
                        "items": {"type": "number"},
                    },
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_overall_bounds",
            "description": "计算整个原始数据集（XLSX文件）的总体地理边界，并将其保存到一个JSON文件中。这个函数应该在所有其他处理之前被调用，以确保所有后续的地图都有一个统一的、一致的地理范围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "需要计算边界的源数据XLSX文件路径。"},
                    "output_bounds_path": {"type": "string", "description": "输出的边界JSON文件的路径，例如 'overall_bounds.json'。"},
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kmeans_cluster",
            "description": "对地理坐标数据进行K-Means聚类分析。自动识别经纬度列（支持longitude/lon/lng/long/x和latitude/lat/y等多种命名方式）。如果用户没有指定聚类数量(n_clusters)，你必须向用户提问以获取此信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_filepath": {
                        "type": "string",
                        "description": "包含经纬度列的输入CSV文件的路径。函数会自动识别常见的经纬度列名（如longitude/lon/lng/long/x和latitude/lat/y等）。通常是数据预处理步骤的输出。",
                    },
                    "n_clusters": {"type": "integer", "description": "要形成的聚类数量（K值）。"},
                    "output_shapefile": {"type": "string", "description": "输出的Shapefile文件的路径，例如 'clusters.shp'。"},
                },
                "required": ["input_filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_heatmap",
            "description": "基于输入的CSV点数据，生成一张带有在线地图背景的热力图。支持通过边界文件设定固定的地图范围，以确保不同热力图之间具有可比性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_filepath": {"type": "string", "description": "输入的点数据CSV文件路径。函数会自动识别常见的经纬度列名。通常是数据预处理步骤的输出。"},
                    "output_image_path": {"type": "string", "description": "输出的热力图图片文件路径。例如, 'heatmap.png'。"},
                    "map_title": {"type": "string", "description": "要显示在热力图顶部的标题。"},
                    "bounds_filepath": {
                        "type": "string",
                        "description": "一个包含地图边界的JSON文件的路径。通常由preprocess_vehicle_data函数生成。如果提供，热力图将使用这个固定的地理范围。",
                    },
                },
                "required": ["input_filepath"],
            },
        },
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
                        "items": {"type": "string"},
                    },
                    "output_gif_path": {"type": "string", "description": "输出的GIF文件的路径。例如, 'animation.gif'。"},
                    "fps": {"type": "integer", "description": "GIF的帧率（每秒播放的图片数量），决定了动画的速度。"},
                },
                "required": ["image_files", "output_gif_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_clusters",
            "description": "为K-Means聚类的结果（一个Shapefile）生成一张带有底图、指北针和比例尺的、按不同颜色区分簇的可视化图片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_shapefile": {
                        "type": "string",
                        "description": "输入的点数据Shapefile文件路径, 必须包含'cluster'列。通常是kmeans_cluster函数的输出。",
                    },
                    "output_image_path": {"type": "string", "description": "输出的可视化图片文件路径。例如, 'cluster_map.png'。"},
                    "map_title": {"type": "string", "description": "要显示在图片顶部的标题。"},
                },
                "required": ["input_shapefile"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_analysis_report",
            "description": "收集所有分析结果（如背景、数据源、范围和从会话历史中提取的已生成文件），并生成一份图文并茂的综合性Markdown分析报告。应该在所有的数据处理和可视化步骤都完成之后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "background": {"type": "string", "description": "由用户提供或AI总结的研究背景。"},
                    "data_source": {"type": "string", "description": "对所用数据来源的简要描述。"},
                    "research_scope": {"type": "string", "description": "对研究范围（地理或时间）的简要说明。"},
                    "output_filename": {"type": "string", "description": "最终输出的Markdown报告文件名, 例如 'final_report.md'。"},
                },
                "required": ["background", "data_source", "research_scope"],
            },
        },
    },
]
