import json
import os
from typing import List, Optional

import pandas as pd

from ..config import OUTPUT_DIR

def kmeans_cluster(input_filepath: str, n_clusters: int = 8, output_shapefile: str = "cluster_results.shp") -> str:
    """对 CSV 数据执行 K-Means 聚类并输出 Shapefile。"""

    print("--- Python函数 `kmeans_cluster` 被执行 ---")
    print(f"参数: input_filepath='{input_filepath}', n_clusters={n_clusters}, output_shapefile='{output_shapefile}'")

    if not os.path.dirname(output_shapefile):
        output_shapefile = os.path.join(OUTPUT_DIR, output_shapefile)

    def _find_coordinate_columns(df):
        longitude_aliases = ['longitude', 'lon', 'lng', 'long', 'x', 'X', 'Longitude', 'LON', 'LNG', 'LONG']
        latitude_aliases = ['latitude', 'lat', 'y', 'Y', 'Latitude', 'LAT']
        longitude_col = None
        latitude_col = None
        for col in df.columns:
            if col in longitude_aliases:
                longitude_col = col
                break
        for col in df.columns:
            if col in latitude_aliases:
                latitude_col = col
                break
        return longitude_col, latitude_col

    try:
        from sklearn.cluster import KMeans
        import geopandas as gpd

        full_input_path = os.path.join(OUTPUT_DIR, os.path.basename(input_filepath))
        df = pd.read_csv(full_input_path)

        longitude_col, latitude_col = _find_coordinate_columns(df)
        if longitude_col is None or latitude_col is None:
            available_columns = list(df.columns)
            return json.dumps({
                "status": "error",
                "message": (
                    "无法识别经纬度列。可用列名: {}。支持的经度列名: longitude, lon, lng, long, x。支持的纬度列名: latitude, lat, y。".format(
                        available_columns
                    )
                ),
            })

        print(f"   识别到经度列: '{longitude_col}', 纬度列: '{latitude_col}'")

        kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10)
        df['cluster'] = kmeans.fit_predict(df[[longitude_col, latitude_col]])

        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[longitude_col], df[latitude_col]))
        gdf.set_crs(epsg=4326, inplace=True)
        gdf.to_file(output_shapefile, driver='ESRI Shapefile')

        base_name = os.path.splitext(output_shapefile)[0]
        shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
        generated_shapefile_files = []
        for ext in shapefile_extensions:
            file_path = base_name + ext
            if os.path.exists(file_path):
                generated_shapefile_files.append(os.path.basename(file_path))

        cluster_summary = df['cluster'].value_counts().to_dict()
        result = {
            "status": "success",
            "output_filepath": os.path.basename(output_shapefile),
            "generated_files": generated_shapefile_files,
            "n_clusters": n_clusters,
            "cluster_point_counts": cluster_summary,
            "coordinate_columns_used": {"longitude": longitude_col, "latitude": latitude_col},
        }
    except ImportError as exc:
        result = {
            "status": "error",
            "message": f"Missing required library: {exc}. Please install scikit-learn and geopandas.",
        }
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)


def create_heatmap(
    input_filepath: str,
    output_image_path: str = "heatmap.png",
    map_title: str = "Taxies Hotspot Analysis Heatmap",
    bounds_filepath: Optional[str] = None,
) -> str:
    """基于 CSV 数据生成带底图的热力图。"""

    print("--- Python函数 `create_heatmap` 被执行 ---")
    print(f"参数: input_filepath='{input_filepath}', output_image_path='{output_image_path}', map_title='{map_title}'")

    if not os.path.dirname(output_image_path):
        output_image_path = os.path.join(OUTPUT_DIR, output_image_path)

    def _find_coordinate_columns(df):
        longitude_aliases = ['longitude', 'lon', 'lng', 'long', 'x', 'X', 'Longitude', 'LON', 'LNG', 'LONG']
        latitude_aliases = ['latitude', 'lat', 'y', 'Y', 'Latitude', 'LAT']
        longitude_col = None
        latitude_col = None
        for col in df.columns:
            if col in longitude_aliases:
                longitude_col = col
                break
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
        from pyproj import Transformer
        from matplotlib_scalebar.scalebar import ScaleBar

        full_input_path = os.path.join(OUTPUT_DIR, os.path.basename(input_filepath))
        df = pd.read_csv(full_input_path)

        longitude_col, latitude_col = _find_coordinate_columns(df)
        if longitude_col is None or latitude_col is None:
            available_columns = list(df.columns)
            return json.dumps({
                "status": "error",
                "message": (
                    "无法识别经纬度列。可用列名: {}。支持的经度列名: longitude, lon, lng, long, x。支持的纬度列名: latitude, lat, y。".format(
                        available_columns
                    )
                ),
            })

        print(f"   识别到经度列: '{longitude_col}', 纬度列: '{latitude_col}'")

        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[longitude_col], df[latitude_col])).set_crs(epsg=4326)
        gdf = gdf.to_crs(epsg=3857)

        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        ax.set_aspect('equal')

        sns.kdeplot(x=gdf.geometry.x, y=gdf.geometry.y, fill=True, cmap="Reds", alpha=0.5, ax=ax)

        gaode_map_provider = {
            "url": "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            "attribution": "© 高德地图",
        }

        if bounds_filepath:
            bounds_path = os.path.join(OUTPUT_DIR, bounds_filepath)
            with open(bounds_path, 'r') as bounds_file:
                bounds = json.load(bounds_file)

            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            min_x, min_y = transformer.transform(bounds['min_lon'], bounds['min_lat'])
            max_x, max_y = transformer.transform(bounds['max_lon'], bounds['max_lat'])
            ax.set_xlim(min_x, max_x)
            ax.set_ylim(min_y, max_y)
            ctx.add_basemap(ax, source=gaode_map_provider['url'], crs=gdf.crs.to_string())
        else:
            ctx.add_basemap(ax, source=gaode_map_provider['url'], crs=gdf.crs.to_string())

        ax.add_artist(ScaleBar(1, location='lower right'))
        x, y, arrow_len = 0.95, 0.95, 0.07
        ax.annotate(
            'N',
            xy=(x, y),
            xytext=(x, y - arrow_len),
            arrowprops=dict(facecolor='black', width=4, headwidth=10),
            ha='center',
            va='center',
            fontsize=20,
            xycoords=ax.transAxes,
        )

        ax.set_title(map_title, fontsize=16)
        ax.set_axis_off()

        plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        result = {"status": "success", "output_image_path": os.path.basename(output_image_path)}
    except ImportError as exc:
        result = {
            "status": "error",
            "message": f"Missing required library: {exc}. Please install geopandas, matplotlib, contextily, and seaborn.",
        }
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)


def create_gif_from_images(image_files: List[str], output_gif_path: str = "animated_result.gif", fps: int = 2) -> str:
    """将多个图片合成为 GIF。"""

    print("--- Python函数 `create_gif_from_images` 被执行 ---")
    print(f"参数: image_files={image_files}, output_gif_path='{output_gif_path}', fps={fps}")

    if not os.path.dirname(output_gif_path):
        output_gif_path = os.path.join(OUTPUT_DIR, output_gif_path)

    try:
        from PIL import Image

        if not image_files:
            return json.dumps({"status": "error", "message": "Image file list cannot be empty."})

        full_image_paths = [os.path.join(OUTPUT_DIR, os.path.basename(f)) for f in image_files]
        frames = [Image.open(path) for path in full_image_paths]
        if not frames:
            return json.dumps({"status": "error", "message": "Could not open any images from the provided list."})

        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=1000 / fps,
            loop=0,
        )

        result = {
            "status": "success",
            "output_gif_path": os.path.basename(output_gif_path),
            "image_count": len(frames),
        }
    except ImportError:
        result = {"status": "error", "message": "Missing required library: Pillow (PIL). Please install it."}
    except FileNotFoundError as exc:
        result = {"status": "error", "message": f"File not found: {exc.filename}"}
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)


def visualize_clusters(
    input_shapefile: str,
    output_image_path: str = "cluster_visualization.png",
    map_title: str = "Cluster Analysis Visualization",
) -> str:
    """根据聚类 Shapefile 生成底图可视化。"""

    print("--- Python函数 `visualize_clusters` 被执行 ---")
    print(f"参数: input_shapefile='{input_shapefile}', output_image_path='{output_image_path}', map_title='{map_title}'")

    if not os.path.dirname(output_image_path):
        output_image_path = os.path.join(OUTPUT_DIR, output_image_path)

    try:
        import geopandas as gpd
        import matplotlib.pyplot as plt
        import contextily as ctx
        from matplotlib_scalebar.scalebar import ScaleBar

        full_input_path = os.path.join(OUTPUT_DIR, os.path.basename(input_shapefile))
        gdf = gpd.read_file(full_input_path)
        if 'cluster' not in gdf.columns:
            return json.dumps({"status": "error", "message": "Input Shapefile must contain a 'cluster' column."})

        gdf = gdf.to_crs(epsg=3857)

        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        gdf.plot(column='cluster', ax=ax, legend=True, markersize=10, cmap='tab20', categorical=True)

        gaode_map_provider = {
            "url": "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            "attribution": "© 高德地图",
        }
        ctx.add_basemap(ax, source=gaode_map_provider['url'], crs=gdf.crs.to_string())

        ax.add_artist(ScaleBar(1, location='lower right'))
        x, y, arrow_len = 0.95, 0.95, 0.07
        ax.annotate(
            'N',
            xy=(x, y),
            xytext=(x, y - arrow_len),
            arrowprops=dict(facecolor='black', width=4, headwidth=10),
            ha='center',
            va='center',
            fontsize=20,
            xycoords=ax.transAxes,
        )

        ax.set_title(map_title, fontsize=16)
        ax.set_axis_off()
        plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        result = {"status": "success", "output_image_path": os.path.basename(output_image_path)}
    except ImportError as exc:
        result = {"status": "error", "message": f"Missing required library: {exc}. Please install matplotlib-scalebar."}
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)
