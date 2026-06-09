# This module defines an image scraper for sphinx-gallery
# https://sphinx-gallery.github.io/
# which can be used by projects using plotly in their documentation.
import os
from pathlib import Path, PurePath

import plotly

plotly.io.renderers.default = "sphinx_gallery_png"


# 模块级 buffer：Sphinx Gallery 渲染器将生成的内容 push 到这里
# scraper 在脚本执行完毕后从这里取出内容并落盘
# 每个元素是一个 dict: {"html": str, "png": bytes|None, "include_plotlyjs": str|bool}
_sphinx_gallery_figures = []


def _enqueue_fig(html_content, png_bytes=None, include_plotlyjs=True):
    """
    由 Sphinx Gallery 渲染器调用，将生成的图内容放入 buffer。

    Parameters
    ----------
    html_content : str
        生成的完整 HTML 字符串
    png_bytes : bytes or None
        生成的 PNG 图像字节（SphinxGalleryOrcaRenderer 提供），无则为 None
    include_plotlyjs : str or bool
        include_plotlyjs 参数，用于 scraper 判断是否需要复制 bundle
    """
    _sphinx_gallery_figures.append({
        "html": html_content,
        "png": png_bytes,
        "include_plotlyjs": include_plotlyjs,
    })


def _dequeue_fig():
    """
    由 scraper 调用，从 buffer 取出最早放入的图内容。
    FIFO 顺序与 Sphinx Gallery 代码块执行顺序一致。
    """
    if _sphinx_gallery_figures:
        return _sphinx_gallery_figures.pop(0)
    return None


def _clear_fig_queue():
    """清空 buffer，用于测试或重置。"""
    _sphinx_gallery_figures.clear()


def _write_fig_to_disk(fig_data, image_path_iterator, gallery_src_dir):
    """
    将 buffer 中的图内容写入最终输出位置。

    统一负责：
    1. 从 image_path_iterator 获取最终输出路径
    2. 写入 HTML 文件
    3. 写入 PNG 文件（如果有）
    4. include_plotlyjs="directory" 时复制 plotly.min.js 到最终目录

    Parameters
    ----------
    fig_data : dict
        buffer 中的图数据：{"html", "png", "include_plotlyjs"}
    image_path_iterator : iterator
        Sphinx Gallery 提供的图像路径迭代器
    gallery_src_dir : str
        Sphinx 文档源目录（gallery_conf["src_dir"]）

    Returns
    -------
    str or None
        写入的 HTML 文件绝对路径，供 figure_rst 生成引用
    """
    from plotly.io._html import _prepare_plotlyjs_bundle
    from plotly.offline.offline import get_plotlyjs

    # 从迭代器获取 Sphinx Gallery 指定的最终输出路径（.png）
    this_image_path_png = next(image_path_iterator)
    this_image_path_html = os.path.splitext(this_image_path_png)[0] + ".html"

    html_path = Path(this_image_path_html)
    output_dir = html_path.parent

    # 规范化 include_plotlyjs
    include_plotlyjs = fig_data["include_plotlyjs"]
    if isinstance(include_plotlyjs, str):
        include_plotlyjs_normalized = include_plotlyjs.lower()
    else:
        include_plotlyjs_normalized = include_plotlyjs

    # 处理 directory 模式：复制 plotly.min.js 到最终输出目录
    if include_plotlyjs_normalized == "directory":
        # 确保输出目录存在
        if output_dir and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = output_dir / "plotly.min.js"
        if not bundle_path.exists():
            bundle_path.write_text(get_plotlyjs(), encoding="utf-8")
        # HTML 中已经是 src="plotly.min.js"（由 to_html 生成时的默认值），无需修改
        html_content = fig_data["html"]
    else:
        # 非 directory 模式，直接使用原始 HTML
        html_content = fig_data["html"]

    # 确保输出目录存在
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # 写入 HTML 文件
    html_path.write_text(html_content, encoding="utf-8")

    # 写入 PNG 文件（如果有）
    if fig_data["png"] is not None:
        png_path = Path(this_image_path_png)
        png_path.write_bytes(fig_data["png"])

    return this_image_path_html


def plotly_sg_scraper(block, block_vars, gallery_conf, **kwargs):
    """Scrape Plotly figures for galleries of examples using
    sphinx-gallery.

    Examples should use ``plotly.io.show()`` to display the figure with
    the custom sphinx_gallery renderer.

    The renderer pushes figure content to a module-level buffer. This
    scraper pops content from the buffer and writes it to the final
    output directory managed by Sphinx Gallery.

    Parameters
    ----------
    block : tuple
        A tuple containing the (label, content, line_number) of the block.
    block_vars : dict
        Dict of block variables. Contains:
        - "src_file": absolute path to the current example .py file
        - "image_path_iterator": iterator yielding target file paths
        - "example_globals": globals dict of the executed script
    gallery_conf : dict
        Contains the configuration of Sphinx-Gallery. Contains:
        - "src_dir": absolute path of Sphinx documentation sources
    **kwargs : dict
        Additional keyword arguments to pass to
        :meth:`~matplotlib.figure.Figure.savefig`, e.g. ``format='svg'``.
        The ``format`` kwarg in particular is used to set the file extension
        of the output file (currently only 'png' and 'svg' are supported).

    Returns
    -------
    rst : str
        The ReSTructuredText that will be rendered to HTML containing
        the images.

    Notes
    -----
    Add this function to the image scrapers
    """
    image_path_iterator = block_vars["image_path_iterator"]
    gallery_src_dir = gallery_conf["src_dir"]

    image_names = list()

    # 从 buffer 中取出所有在本代码块生成的图
    # 注意：Sphinx Gallery 对每个代码块调用一次 scraper，因此 buffer 中剩余的
    # 内容都属于当前代码块
    while True:
        fig_data = _dequeue_fig()
        if fig_data is None:
            break
        html_path = _write_fig_to_disk(
            fig_data, image_path_iterator, gallery_src_dir
        )
        if html_path:
            image_names.append(html_path)

    # Use the `figure_rst` helper function to generate rST for image files
    return figure_rst(image_names, gallery_src_dir)


def figure_rst(figure_list, sources_dir):
    """Generate RST for a list of PNG filenames.

    Depending on whether we have one or more figures, we use a
    single rst call to 'image' or a horizontal list.

    Parameters
    ----------
    figure_list : list
        List of strings of the figures' absolute paths.
    sources_dir : str
        absolute path of Sphinx documentation sources

    Returns
    -------
    images_rst : str
        rst code to embed the images in the document
    """

    figure_paths = [
        os.path.relpath(figure_path, sources_dir).replace(os.sep, "/").lstrip("/")
        for figure_path in figure_list
    ]
    images_rst = ""
    if not figure_paths:
        return images_rst
    figure_name = figure_paths[0]
    figure_path = os.path.join("images", os.path.basename(figure_name))
    images_rst = SINGLE_HTML % figure_path
    return images_rst


SINGLE_HTML = """
.. raw:: html
    :file: %s
"""
