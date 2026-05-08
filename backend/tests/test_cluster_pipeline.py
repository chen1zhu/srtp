"""Utility test script for chaining `kmeans_cluster` and `visualize_clusters`.

Steps performed:
1. Convert one of the Excel uploads into a filtered CSV inside `outputs/`.
2. Run `kmeans_cluster` against that CSV to produce a Shapefile.
3. Call `visualize_clusters` on the generated Shapefile to verify a map image is produced.

Run from the project root:
    python backend/tests/test_cluster_pipeline.py --excel 64b3...xlsx --clusters 6
"""

import argparse
import json
import os
import sys
from typing import Any, Dict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.config import OUTPUT_DIR  # noqa: E402
from backend.tools.preprocessing import preprocess_vehicle_data  # noqa: E402
from backend.tools.analytics import kmeans_cluster, visualize_clusters  # noqa: E402


def _parse_response(label: str, payload: str) -> Dict[str, Any]:
    """Decode JSON payload and ensure the tool reported success."""

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned invalid JSON: {exc}") from exc

    if data.get("status") != "success":
        raise RuntimeError(f"{label} failed: {data.get('message')}")
    return data


def run_cluster_visualization(
    excel_filename: str,
    point_type: str | None,
    start_time: str | None,
    end_time: str | None,
    n_clusters: int,
    map_title: str,
) -> Dict[str, str]:
    """Execute preprocess -> kmeans -> visualize pipeline and return artifact paths."""

    uploads_path = os.path.join(REPO_ROOT, "uploads", excel_filename)
    if not os.path.exists(uploads_path):
        raise FileNotFoundError(f"Excel source not found: {uploads_path}")

    preprocess_result = _parse_response(
        "preprocess_vehicle_data",
        preprocess_vehicle_data(
            uploads_path,
            point_type=point_type,
            start_time=start_time,
            end_time=end_time,
            bbox=None,
        ),
    )
    csv_basename = preprocess_result["output_filepath"]
    csv_path = os.path.join(OUTPUT_DIR, csv_basename)

    cluster_output_name = f"clusters_{os.path.splitext(csv_basename)[0]}_k{n_clusters}.shp"
    cluster_result = _parse_response(
        "kmeans_cluster",
        kmeans_cluster(
            csv_path,
            n_clusters=n_clusters,
            output_shapefile=cluster_output_name,
        ),
    )
    shapefile_basename = cluster_result["output_filepath"]
    shapefile_path = os.path.join(OUTPUT_DIR, shapefile_basename)

    visualization_name = f"{os.path.splitext(shapefile_basename)[0]}_viz.png"
    visualization_result = _parse_response(
        "visualize_clusters",
        visualize_clusters(
            shapefile_path,
            output_image_path=visualization_name,
            map_title=map_title,
        ),
    )

    return {
        "csv": csv_path,
        "shapefile": shapefile_path,
        "image": os.path.join(OUTPUT_DIR, visualization_result["output_image_path"]),
        "bounds": os.path.join(OUTPUT_DIR, preprocess_result["bounds_filepath"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end test for the clustering visualization pipeline.")
    parser.add_argument("--excel", required=True, help="Excel filename located in the uploads directory.")
    parser.add_argument(
        "--point-type",
        choices=["start", "end", "all"],
        default="start",
        help="Whether to keep only start or end points (all keeps every record).",
    )
    parser.add_argument("--start-time", default=None, help="Optional lower bound for timestamp filtering (e.g., 080000).")
    parser.add_argument("--end-time", default=None, help="Optional upper bound for timestamp filtering (e.g., 100000).")
    parser.add_argument("--clusters", type=int, default=6, help="Number of clusters to create in K-Means.")
    parser.add_argument(
        "--map-title",
        default="Cluster Analysis Visualization",
        help="Title to display on the generated map.",
    )
    args = parser.parse_args()

    selected_point_type = None if args.point_type == "all" else args.point_type

    artifact_paths = run_cluster_visualization(
        excel_filename=args.excel,
        point_type=selected_point_type,
        start_time=args.start_time,
        end_time=args.end_time,
        n_clusters=args.clusters,
        map_title=args.map_title,
    )

    print("\nPipeline finished. Generated artifacts:")
    for label, path in artifact_paths.items():
        print(f"  - {label}: {path}")


if __name__ == "__main__":
    main()
