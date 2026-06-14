#!/usr/bin/env python3
"""将 .mmd 文件渲染为 PNG 和 SVG。"""
import sys
import os

sys.path.insert(0, "/home/doer/miniconda3/envs/py-xiaozhi/lib/python3.12/site-packages")
from mermaid import Mermaid

DIAGRAMS = [
    ("01_system_architecture.mmd", "01_system_architecture"),
    ("02_iot_thing_flow.mmd", "02_iot_thing_flow"),
    ("03_udp_ack_flow.mmd", "03_udp_ack_flow"),
]

def render():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    for mmd_file, name in DIAGRAMS:
        mmd_path = os.path.join(base_dir, mmd_file)
        print(f"\n--- 渲染 {mmd_file} ---")

        with open(mmd_path, "r", encoding="utf-8") as f:
            definition = f.read()

        try:
            m = Mermaid(definition)

            svg_path = os.path.join(out_dir, f"{name}.svg")
            m.to_svg(svg_path)
            svg_size = os.path.getsize(svg_path)
            print(f"  SVG -> {svg_path}  ({svg_size} bytes)")

            png_path = os.path.join(out_dir, f"{name}.png")
            m.to_png(png_path)
            png_size = os.path.getsize(png_path)
            print(f"  PNG -> {png_path}  ({png_size} bytes)")

        except Exception as e:
            print(f"  错误: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    render()
