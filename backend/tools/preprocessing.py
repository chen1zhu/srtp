import json
import os
from typing import List, Optional

import pandas as pd

from ..config import OUTPUT_DIR

def preprocess_vehicle_data(
    filepath: str,
    point_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    bbox: Optional[List[float]] = None,
) -> str:
    """按照筛选条件预处理车辆轨迹数据并输出 CSV/边界文件。"""

    def _convert_time_to_seconds(time_str: Optional[str]) -> Optional[int]:
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

    print("--- Python函数 `preprocess_vehicle_data` 被执行 ---")
    print(
        "参数: filepath='{}', point_type='{}', start_time='{}', end_time='{}', bbox={}".format(
            filepath, point_type, start_time, end_time, bbox
        )
    )

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
                (df['longitude'] >= min_lon)
                & (df['longitude'] <= max_lon)
                & (df['latitude'] >= min_lat)
                & (df['latitude'] <= max_lat)
            ]

        filtered_rows = len(df)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        filters_str = ""
        if point_type:
            filters_str += f"_{point_type}"
        if start_time:
            filters_str += f"_{start_time.replace(':', '')}"
        if end_time:
            filters_str += f"_{end_time.replace(':', '')}"
        if not filters_str:
            filters_str = "_all"

        output_filename = os.path.join(OUTPUT_DIR, f"filtered_{base_name}{filters_str}.csv")
        df.to_csv(output_filename, index=False)

        bounds = {
            "min_lon": df['longitude'].min(),
            "min_lat": df['latitude'].min(),
            "max_lon": df['longitude'].max(),
            "max_lat": df['latitude'].max(),
        }
        bounds_filename = os.path.join(OUTPUT_DIR, f"bounds_{base_name}{filters_str}.json")
        with open(bounds_filename, 'w') as file:
            json.dump(bounds, file)

        result = {
            "status": "success",
            "original_rows": original_rows,
            "filtered_rows": filtered_rows,
            "output_filepath": os.path.basename(output_filename),
            "bounds_filepath": os.path.basename(bounds_filename),
            "filters_applied": {
                "point_type": point_type,
                "time_range": [start_time, end_time],
                "bbox": bbox,
            },
        }
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)


def get_overall_bounds(filepath: str, output_bounds_path: str = "overall_bounds.json") -> str:
    """计算整个原始数据集的地理范围并输出 JSON。"""

    print("--- Python函数 `get_overall_bounds` 被执行 ---")
    print(f"参数: filepath='{filepath}', output_bounds_path='{output_bounds_path}'")

    if not os.path.dirname(output_bounds_path):
        output_bounds_path = os.path.join(OUTPUT_DIR, output_bounds_path)

    try:
        column_names = ['timestamp', 'longitude', 'latitude', 'type', 'label']
        df = pd.read_excel(filepath, header=None, names=column_names, engine='openpyxl')

        bounds = {
            "min_lon": df['longitude'].min(),
            "min_lat": df['latitude'].min(),
            "max_lon": df['longitude'].max(),
            "max_lat": df['latitude'].max(),
        }

        with open(output_bounds_path, 'w') as file:
            json.dump(bounds, file)

        result = {"status": "success", "bounds_filepath": os.path.basename(output_bounds_path)}
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)
