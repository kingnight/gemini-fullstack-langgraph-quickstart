from langgraph.graph import Graph
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

# def renderGraph(graph: Graph, name="graph.png"):
#     """
#     生成Mermaid图函数，默认存储图片名为"graph.png
#     ```
#     import common.render
#     common.render.renderGraph(graph)
#     ```
#     """
#     img_bytes = graph.get_graph().draw_mermaid_png()
#     with open(name, "wb") as f:
#         f.write(img_bytes)
#     print(f"图片已保存为{name}")


def getMermaid(graph: Graph):
    """convert a graph class into Mermaid syntax"""
    mermaid = graph.get_graph().draw_mermaid()
    return mermaid

# import nest_asyncio
# def renderGraphPyppeteer(graph: Graph, name="graph.png"):
#     """
#     生成Mermaid图函数,默认存储图片名为"graph.png
#     """
#     nest_asyncio.apply()
#     img_bytes = graph.get_graph().draw_mermaid_png(
#             curve_style=CurveStyle.LINEAR,
#             node_colors=NodeStyles(first="#ffdfba", last="#baffc9", default="#fad7de"),
#             wrap_label_n_words=9,
#             output_file_path=None,
#             draw_method=MermaidDrawMethod.PYPPETEER,
#             background_color="white",
#             padding=10,
#         )
#     with open(name, "wb") as f:
#         f.write(img_bytes)
#     print(f"图片已保存为{name}")


def renderGraph(graph: Graph, name="graph.png"):
    """
    生成Graphviz图函数,默认存储图片名为"graph.png
    """
    img_bytes = graph.get_graph().draw_png()
    with open(name, "wb") as f:
        f.write(img_bytes)
    print(f"图片已保存为{name}")    