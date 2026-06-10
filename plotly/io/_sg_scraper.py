# This module defines an image scraper for sphinx-gallery
# https://sphinx-gallery.github.io/
# which can be used by projects using plotly in their documentation.
from glob import glob
import os
import shutil

import plotly
from plotly.offline.offline import get_plotlyjs

plotly.io.renderers.default = "sphinx_gallery_png"

_sg_html_store = []


def _store_sg_html(html_content, include_plotlyjs):
    _sg_html_store.append((html_content, include_plotlyjs))


def _get_sg_html():
    items = list(_sg_html_store)
    _sg_html_store.clear()
    return items


def plotly_sg_scraper(block, block_vars, gallery_conf, **kwargs):
    """Scrape Plotly figures for galleries of examples using
    sphinx-gallery.

    Examples should use ``plotly.io.show()`` to display the figure with
    the custom sphinx_gallery renderer.

    This scraper handles two renderer types:
    - SphinxGalleryHtmlRenderer: HTML content is passed via module-level store
    - SphinxGalleryOrcaRenderer: HTML/PNG files are written to disk

    File output paths are managed entirely by the scraper using the
    gallery-provided image_path_iterator, ensuring bundle placement and
    HTML references are consistent with the final output directory.

    Parameters
    ----------
    block : tuple
        A tuple containing the (label, content, line_number) of the block.
    block_vars : dict
        Dict of block variables.
    gallery_conf : dict
        Contains the configuration of Sphinx-Gallery
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
    examples_dir = os.path.dirname(block_vars["src_file"])
    image_path_iterator = block_vars["image_path_iterator"]
    image_names = list()

    stored_items = _get_sg_html()
    images_dir = None

    for html_content, include_plotlyjs in stored_items:
        this_image_path_png = next(image_path_iterator)
        this_image_path_html = os.path.splitext(this_image_path_png)[0] + ".html"
        image_names.append(this_image_path_html)

        images_dir = os.path.dirname(this_image_path_html)
        os.makedirs(images_dir, exist_ok=True)

        with open(this_image_path_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        if include_plotlyjs == "directory":
            bundle_dst = os.path.join(images_dir, "plotly.min.js")
            if not os.path.exists(bundle_dst):
                with open(bundle_dst, "w", encoding="utf-8") as f:
                    f.write(get_plotlyjs())

    pngs = sorted(glob(os.path.join(examples_dir, "*.png")))
    htmls = sorted(glob(os.path.join(examples_dir, "*.html")))
    seen = set()
    bundle_src = os.path.join(examples_dir, "plotly.min.js")

    for html, png in zip(htmls, pngs):
        if png not in seen:
            seen |= set(png)
            this_image_path_png = next(image_path_iterator)
            this_image_path_html = os.path.splitext(this_image_path_png)[0] + ".html"
            image_names.append(this_image_path_html)
            shutil.move(png, this_image_path_png)
            shutil.move(html, this_image_path_html)

            if images_dir is None:
                images_dir = os.path.dirname(this_image_path_html)

    if os.path.exists(bundle_src) and images_dir is not None:
        bundle_dst = os.path.join(images_dir, "plotly.min.js")
        if not os.path.exists(bundle_dst):
            shutil.move(bundle_src, bundle_dst)

    return figure_rst(image_names, gallery_conf["src_dir"])


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
