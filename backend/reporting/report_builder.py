import json
import os
from typing import List

from ..config import OUTPUT_DIR, call_llm_for_section
from ..vision_analyzer_test import analyze_image_sequence


def generate_analysis_report(
    background: str,
    data_source: str,
    research_scope: str,
    session_generated_files: List[str],
    output_filename: str = "analysis_report.md",
) -> str:
    """根据中间成果生成最终 Markdown 报告。"""

    print("--- Python函数 `generate_analysis_report` 被执行 ---")
    print("   - 正在从会话生成的文件中查找图片...")

    heatmap_images = sorted([f for f in session_generated_files if 'heatmap' in f and f.endswith('.png')])
    cluster_images = sorted([f for f in session_generated_files if 'cluster' in f and f.endswith('.png')])

    print(f"   - 找到 {len(heatmap_images)} 张热力图: {heatmap_images}")
    print(f"   - 找到 {len(cluster_images)} 张聚类图: {cluster_images}")

    if not os.path.dirname(output_filename):
        output_filename = os.path.join(OUTPUT_DIR, output_filename)

    try:
        print("   - 正在生成报告的文本内容...")
        background_prompt = (
            "请根据以下初步描述，详细、专业地撰写“研究背景”部分，至少300字。初步描述：\n---\n" + background
        )
        generated_background = call_llm_for_section(background_prompt)

        datasource_prompt = (
            "请根据以下数据来源信息，详细、专业地撰写“研究数据来源”部分。请说明数据格式、可能的字段和数据的重要性。数据来源：\n---\n"
            + data_source
        )
        generated_data_source = call_llm_for_section(datasource_prompt)

        scope_prompt = (
            "请根据以下信息，详细、专业地撰写“研究范围”部分，解释该范围设定的意义。研究范围：\n---\n"
            + research_scope
        )
        generated_scope = call_llm_for_section(scope_prompt)

        print("   - 正在调用视觉模型分析图片...")
        image_paths_for_analysis = []
        for img in heatmap_images + cluster_images:
            full_path = os.path.join(OUTPUT_DIR, img)
            if os.path.exists(full_path):
                image_paths_for_analysis.append(full_path)

        if image_paths_for_analysis:
            visual_analysis_conclusion = analyze_image_sequence(image_paths_for_analysis)
        else:
            visual_analysis_conclusion = "未能找到有效的图片进行视觉分析。"
            print("   - 警告: 未能找到任何有效的图片进行分析。")

        print("   - 正在整合所有内容到最终报告中...")
        heatmap_md = "\n".join([f"![热力图]({img})" for img in heatmap_images]) if heatmap_images else "未生成热力图。"
        cluster_md = "\n".join([f"![聚类图]({img})" for img in cluster_images]) if cluster_images else "未生成聚类图。"

        report_content = f"""
# 综合分析报告

## 一、研究背景
{generated_background}

## 二、研究数据来源
{generated_data_source}

## 三、研究范围
{generated_scope}

## 四、研究结果
本部分展示了通过数据分析生成的可视化结果。

### 4.1 热力图分析
下图展示了研究区域内的热点分布情况。
{heatmap_md}

### 4.2 聚类分析
下图展示了数据点的空间聚类结果。
{cluster_md}

## 五、研究结论
基于以上可视化结果，我们利用视觉AI大模型进行深度分析，得出以下结论：
{visual_analysis_conclusion}
"""

        with open(output_filename, 'w', encoding='utf-8') as file:
            file.write(report_content)

        print(f"   - 报告已成功生成并保存为: {output_filename}")
        result = {"status": "success", "report_filepath": os.path.basename(output_filename)}
    except Exception as exc:
        print(f"   - 生成报告时出错: {exc}")
        result = {"status": "error", "message": str(exc)}

    return json.dumps(result)
