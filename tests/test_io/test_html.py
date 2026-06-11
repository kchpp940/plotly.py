import pytest
import numpy as np
import re
import os
import tempfile
import json
from pathlib import Path


import plotly.graph_objs as go
import plotly.io as pio
from plotly.io._utils import plotly_cdn_url
from plotly.offline.offline import get_plotlyjs
from plotly.io._resource_policy import (
    _generate_sri_hash,
    ResourcePolicySet,
    ResourcePolicyContext,
    ResourceType,
    PolicyType,
    InlinePolicy,
    CdnPolicy,
    DirectoryPolicy,
    UrlPolicy,
    ManifestPolicy,
    ExcludePolicy,
    create_policy_set,
    policy_from_include_plotlyjs,
    policy_from_include_mathjax,
)
import warnings


@pytest.fixture
def fig1(request):
    return go.Figure(
        data=[
            {
                "type": "scatter",
                "y": np.array([2, 1, 3, 2, 4, 2]),
                "marker": {"color": "green"},
            }
        ],
        layout={"title": {"text": "Figure title"}},
    )


def test_versioned_cdn_included(fig1):
    assert plotly_cdn_url() in pio.to_html(fig1, include_plotlyjs="cdn")


def test_html_deterministic(fig1):
    div_id = "plotly-root"
    assert pio.to_html(fig1, include_plotlyjs="cdn", div_id=div_id) == pio.to_html(
        fig1, include_plotlyjs="cdn", div_id=div_id
    )


def test_cdn_includes_integrity_attribute(fig1):
    """Test that the CDN script tag includes an integrity attribute with SHA256 hash"""
    html_output = pio.to_html(fig1, include_plotlyjs="cdn")

    # Check that the script tag includes integrity attribute
    assert 'integrity="sha256-' in html_output
    assert 'crossorigin="anonymous"' in html_output

    # Verify it's in the correct script tag
    cdn_pattern = re.compile(
        r'<script[^>]*src="'
        + re.escape(plotly_cdn_url())
        + r'"[^>]*integrity="sha256-[A-Za-z0-9+/=]+"[^>]*>'
    )
    match = cdn_pattern.search(html_output)
    assert match is not None, "CDN script tag with integrity attribute not found"


def test_outer_wrapper_carries_requested_dimensions(fig1):
    """
    Regression test for https://github.com/plotly/plotly.py/issues/5591.

    The outer wrapper div produced by ``to_html`` must carry the requested
    height/width so that percentage values propagate from a parent container
    down to the figure element. Without this, a default of ``height='100%'``
    collapses to zero (because the wrapper has no height) and plotly.js falls
    back to its hardcoded 450px, breaking any responsive layout.
    """
    html = pio.to_html(fig1, include_plotlyjs="cdn", full_html=False)

    wrapper_match = re.match(r'<div style="([^"]+)">', html)
    assert wrapper_match is not None, (
        "Outer wrapper div is missing inline style; responsive parents cannot "
        "propagate dimensions to the figure."
    )
    wrapper_style = wrapper_match.group(1)
    assert "height:100%" in wrapper_style
    assert "width:100%" in wrapper_style

    inner_match = re.search(
        r'<div id="[^"]+" class="plotly-graph-div" style="([^"]+)">',
        html,
    )
    assert inner_match is not None
    assert "height:100%" in inner_match.group(1)
    assert "width:100%" in inner_match.group(1)


def test_outer_wrapper_respects_explicit_pixel_dimensions(fig1):
    """Explicit pixel dimensions must reach the outer wrapper unchanged."""
    html = pio.to_html(
        fig1,
        include_plotlyjs="cdn",
        full_html=False,
        default_width=600,
        default_height=400,
    )

    wrapper_match = re.match(r'<div style="([^"]+)">', html)
    assert wrapper_match is not None
    wrapper_style = wrapper_match.group(1)
    assert "height:400px" in wrapper_style
    assert "width:600px" in wrapper_style


def test_cdn_integrity_hash_matches_bundled_content(fig1):
    """Test that the SRI hash in CDN script tag matches the bundled plotly.js content"""
    html_output = pio.to_html(fig1, include_plotlyjs="cdn")

    # Extract the integrity hash from the HTML output
    integrity_pattern = re.compile(r'integrity="(sha256-[A-Za-z0-9+/=]+)"')
    match = integrity_pattern.search(html_output)
    assert match is not None, "Integrity attribute not found"
    extracted_hash = match.group(1)

    # Generate expected hash from bundled content
    plotlyjs_content = get_plotlyjs()
    expected_hash = _generate_sri_hash(plotlyjs_content)

    # Verify they match
    assert extracted_hash == expected_hash, (
        f"Hash mismatch: expected {expected_hash}, got {extracted_hash}"
    )


# ============================================================================
# Resource Policy Tests
# ============================================================================


class TestPolicyFromIncludePlotlyjs:
    """Test policy_from_include_plotlyjs function"""

    def test_exclude_false(self):
        policy = policy_from_include_plotlyjs(False)
        assert isinstance(policy, ExcludePolicy)
        assert policy.resource_type == ResourceType.PLOTLYJS

    def test_inline_true(self):
        content = "console.log('test');"
        policy = policy_from_include_plotlyjs(True, plotlyjs_content=content)
        assert isinstance(policy, InlinePolicy)
        assert policy.content == content

    def test_cdn(self):
        cdn_url = "https://cdn.example.com/plotly.min.js"
        content = "console.log('test');"
        policy = policy_from_include_plotlyjs(
            "cdn", plotlyjs_cdn_url=cdn_url, plotlyjs_content=content
        )
        assert isinstance(policy, CdnPolicy)
        assert policy.cdn_url == cdn_url
        assert policy.content == content

    def test_directory_with_source(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("console.log('test');")
            temp_path = f.name

        try:
            policy = policy_from_include_plotlyjs(
                "directory", plotlyjs_source=temp_path
            )
            assert isinstance(policy, DirectoryPolicy)
            assert policy.filename == "plotly.min.js"
        finally:
            os.unlink(temp_path)

    def test_directory_with_content(self):
        content = "console.log('test');"
        policy = policy_from_include_plotlyjs(
            "directory", plotlyjs_content=content
        )
        assert isinstance(policy, DirectoryPolicy)
        assert policy.filename == "plotly.min.js"
        assert policy.content == content

    def test_custom_url(self):
        url = "/static/plotly.min.js"
        policy = policy_from_include_plotlyjs(url)
        assert isinstance(policy, UrlPolicy)
        assert policy.url == url


class TestPolicyFromIncludeMathjax:
    """Test policy_from_include_mathjax function"""

    def test_exclude_false(self):
        policy = policy_from_include_mathjax(False)
        assert policy is None

    def test_cdn(self):
        policy = policy_from_include_mathjax("cdn")
        assert isinstance(policy, UrlPolicy)
        assert "cdn" in policy.url.lower()
        assert "config=TeX-AMS-MML_SVG" in policy.url

    def test_custom_url(self):
        url = "/static/MathJax.js"
        policy = policy_from_include_mathjax(url)
        assert isinstance(policy, UrlPolicy)
        assert policy.url.startswith(url)
        assert "config=TeX-AMS-MML_SVG" in policy.url


class TestCreatePolicySet:
    """Test create_policy_set function"""

    def test_default(self):
        content = "console.log('test');"
        policy_set = create_policy_set(
            include_plotlyjs=True, plotlyjs_content=content
        )
        assert isinstance(policy_set, ResourcePolicySet)
        assert isinstance(policy_set.plotlyjs, InlinePolicy)
        assert policy_set.mathjax is None
        assert policy_set.meta is not None
        assert "charset" in policy_set.meta.content

    def test_with_mathjax_cdn(self):
        policy_set = create_policy_set(
            include_plotlyjs=False, include_mathjax="cdn"
        )
        assert isinstance(policy_set.plotlyjs, ExcludePolicy)
        assert isinstance(policy_set.mathjax, UrlPolicy)

    def test_with_css_content(self):
        css = ".plotly-graph-div { border: 1px solid red; }"
        policy_set = create_policy_set(
            include_plotlyjs=False, css_content=css
        )
        assert isinstance(policy_set.css, InlinePolicy)
        assert policy_set.css.content == css

    def test_with_css_url(self):
        css_url = "/static/custom.css"
        policy_set = create_policy_set(
            include_plotlyjs=False, css_url=css_url
        )
        assert isinstance(policy_set.css, UrlPolicy)
        assert policy_set.css.url == css_url

    def test_with_meta_tags(self):
        meta_tags = {"viewport": "width=device-width, initial-scale=1.0"}
        policy_set = create_policy_set(
            include_plotlyjs=False, meta_tags=meta_tags
        )
        assert policy_set.meta is not None
        assert 'name="viewport"' in policy_set.meta.content
        assert 'content="width=device-width, initial-scale=1.0"' in policy_set.meta.content

    def test_without_meta_charset(self):
        policy_set = create_policy_set(
            include_plotlyjs=False, include_meta_charset=False
        )
        assert policy_set.meta is None


class TestInlinePolicy:
    """Test InlinePolicy"""

    def test_script_inline(self):
        content = "console.log('test');"
        policy = InlinePolicy(
            resource_type=ResourceType.PLOTLYJS, content=content
        )
        ref = policy.get_ref()
        assert content in ref.html
        assert "<script" in ref.html
        assert "</script>" in ref.html
        assert not ref.needs_copy

    def test_css_inline(self):
        css = ".test { color: red; }"
        policy = InlinePolicy(resource_type=ResourceType.CSS, content=css)
        ref = policy.get_ref()
        assert css in ref.html
        assert "<style" in ref.html
        assert "</style>" in ref.html

    def test_meta_inline(self):
        meta = '<meta name="viewport" content="width=device-width" />'
        policy = InlinePolicy(resource_type=ResourceType.META, content=meta)
        ref = policy.get_ref()
        assert ref.html == meta

    def test_none_content(self):
        policy = InlinePolicy(resource_type=ResourceType.PLOTLYJS, content=None)
        ref = policy.get_ref()
        assert ref.html == ""
        assert ref.missing_hint is not None


class TestCdnPolicy:
    """Test CdnPolicy"""

    def test_script_cdn(self):
        url = "https://cdn.example.com/plotly.min.js"
        content = "console.log('test');"
        policy = CdnPolicy(
            resource_type=ResourceType.PLOTLYJS, cdn_url=url, content=content
        )
        ref = policy.get_ref()
        assert url in ref.html
        assert '<script src="' in ref.html
        assert 'integrity="sha256-' in ref.html
        assert 'crossorigin="anonymous"' in ref.html

    def test_css_cdn(self):
        url = "https://cdn.example.com/style.css"
        policy = CdnPolicy(resource_type=ResourceType.CSS, cdn_url=url, sri=False)
        ref = policy.get_ref()
        assert url in ref.html
        assert '<link rel="stylesheet"' in ref.html
        assert "integrity" not in ref.html

    def test_no_sri(self):
        url = "https://cdn.example.com/plotly.min.js"
        policy = CdnPolicy(
            resource_type=ResourceType.PLOTLYJS, cdn_url=url, sri=False
        )
        ref = policy.get_ref()
        assert "integrity" not in ref.html
        assert "crossorigin" not in ref.html


class TestDirectoryPolicy:
    """Test DirectoryPolicy"""

    def test_with_source_path(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("console.log('test');")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                output_path = Path(output_dir) / "test.html"
                policy = DirectoryPolicy(
                    resource_type=ResourceType.PLOTLYJS,
                    filename="plotly.min.js",
                    source_path=temp_path,
                )
                ref = policy.get_ref(output_path=output_path)

                assert ref.needs_copy
                assert ref.relative_path == "plotly.min.js"
                assert ref.copy_target == Path(output_dir) / "plotly.min.js"
                assert ref.copy_source == Path(temp_path)
                assert 'src="plotly.min.js"' in ref.html
        finally:
            os.unlink(temp_path)

    def test_with_content(self):
        content = "console.log('test');"
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "test.html"
            policy = DirectoryPolicy(
                resource_type=ResourceType.PLOTLYJS,
                filename="plotly.min.js",
                content=content,
            )
            ref = policy.get_ref(output_path=output_path)

            assert ref.needs_copy
            assert ref.copy_source is None

            # Test write_content
            target = Path(output_dir) / "plotly.min.js"
            policy.write_content(target)
            assert target.exists()
            assert target.read_text() == content

    def test_with_subdir(self):
        content = "console.log('test');"
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "test.html"
            policy = DirectoryPolicy(
                resource_type=ResourceType.PLOTLYJS,
                filename="plotly.min.js",
                content=content,
                subdir="static",
            )
            ref = policy.get_ref(output_path=output_path)

            assert ref.relative_path == os.path.join("static", "plotly.min.js")
            assert ref.copy_target == Path(output_dir) / "static" / "plotly.min.js"


class TestManifestPolicy:
    """Test ManifestPolicy"""

    def test_with_public_path(self):
        with tempfile.TemporaryDirectory() as output_dir:
            manifest_path = Path(output_dir) / "manifest.json"
            output_path = Path(output_dir) / "test.html"
            public_path = "/static/plotly.min.js"

            policy = ManifestPolicy(
                resource_type=ResourceType.PLOTLYJS,
                manifest_path=manifest_path,
                public_path=public_path,
            )
            ref = policy.get_ref(output_path=output_path)

            assert public_path in ref.html
            assert manifest_path.exists()

            # Check manifest content
            manifest = json.loads(manifest_path.read_text())
            assert "resources" in manifest
            assert len(manifest["resources"]) == 1
            assert manifest["resources"][0]["url"] == public_path
            assert manifest["resources"][0]["type"] == ResourceType.PLOTLYJS

    def test_with_source_path(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("console.log('test');")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                manifest_path = Path(output_dir) / "manifest.json"
                output_path = Path(output_dir) / "test.html"

                policy = ManifestPolicy(
                    resource_type=ResourceType.PLOTLYJS,
                    manifest_path=manifest_path,
                    source_path=temp_path,
                )
                ref = policy.get_ref(output_path=output_path)

                assert manifest_path.exists()
                manifest = json.loads(manifest_path.read_text())
                assert "hash" in manifest["resources"][0]
                assert manifest["resources"][0]["source"] == temp_path
        finally:
            os.unlink(temp_path)


class TestResourcePolicySet:
    """Test ResourcePolicySet"""

    def test_get_head_html(self):
        plotlyjs_content = "console.log('plotly');"
        css = ".test { color: red; }"

        policy_set = ResourcePolicySet()
        policy_set.plotlyjs = InlinePolicy(
            resource_type=ResourceType.PLOTLYJS, content=plotlyjs_content
        )
        policy_set.mathjax = UrlPolicy(
            resource_type=ResourceType.MATHJAX,
            url="https://cdn.example.com/MathJax.js",
        )
        policy_set.css = InlinePolicy(
            resource_type=ResourceType.CSS, content=css
        )
        policy_set.meta = InlinePolicy(
            resource_type=ResourceType.META,
            content='<meta charset="utf-8" />',
        )

        head_html = policy_set.get_head_html()

        assert "<meta charset" in head_html
        assert "PlotlyConfig" in head_html
        assert plotlyjs_content in head_html
        assert "MathJax.js" in head_html
        assert css in head_html
        assert "MathJax.Hub.Config" in head_html

    def test_get_copy_tasks(self):
        content = "console.log('test');"
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "test.html"

            policy_set = ResourcePolicySet()
            policy_set.plotlyjs = DirectoryPolicy(
                resource_type=ResourceType.PLOTLYJS,
                filename="plotly.min.js",
                content=content,
            )
            policy_set.mathjax = CdnPolicy(
                resource_type=ResourceType.MATHJAX,
                cdn_url="https://cdn.example.com/MathJax.js",
            )

            tasks = policy_set.get_copy_tasks(output_path=output_path)
            assert len(tasks) == 1
            assert tasks[0].copy_target == Path(output_dir) / "plotly.min.js"

    def test_execute_copies(self):
        content = "console.log('test');"
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "test.html"

            policy_set = ResourcePolicySet()
            policy_set.plotlyjs = DirectoryPolicy(
                resource_type=ResourceType.PLOTLYJS,
                filename="plotly.min.js",
                content=content,
            )

            copied = policy_set.execute_copies(output_path=output_path)
            assert len(copied) == 1
            assert copied[0] == Path(output_dir) / "plotly.min.js"
            assert copied[0].read_text() == content

            # Test no overwrite
            new_content = "console.log('new');"
            policy_set.plotlyjs = DirectoryPolicy(
                resource_type=ResourceType.PLOTLYJS,
                filename="plotly.min.js",
                content=new_content,
            )
            copied = policy_set.execute_copies(output_path=output_path)
            assert len(copied) == 0
            assert (Path(output_dir) / "plotly.min.js").read_text() == content

            # Test overwrite
            copied = policy_set.execute_copies(
                output_path=output_path, overwrite=True
            )
            assert len(copied) == 1
            assert (Path(output_dir) / "plotly.min.js").read_text() == new_content

    def test_get_set_policy(self):
        policy_set = ResourcePolicySet()

        policy = ExcludePolicy(resource_type=ResourceType.PLOTLYJS)
        policy_set.set_policy(ResourceType.PLOTLYJS, policy)
        assert policy_set.get_policy(ResourceType.PLOTLYJS) is policy

        extra_policy = UrlPolicy(
            resource_type="extra", url="https://example.com/extra.js"
        )
        policy_set.set_policy("extra", extra_policy)
        assert policy_set.get_policy("extra") is extra_policy


class TestToHtmlWithResourcePolicy:
    """Test to_html with resource_policy parameter"""

    def test_with_custom_policy(self, fig1):
        """Test to_html with a custom ResourcePolicySet"""
        css = ".plotly-graph-div { border: 2px solid blue; }"
        policy_set = create_policy_set(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
            css_content=css,
            meta_tags={"viewport": "width=device-width"},
        )

        html = pio.to_html(fig1, resource_policy=policy_set, full_html=True)

        assert "<head>" in html
        assert "viewport" in html
        assert css in html
        assert plotly_cdn_url() in html
        assert "MathJax" in html

    def test_legacy_params_still_work(self, fig1):
        """Ensure legacy include_plotlyjs parameter still works"""
        html_cdn = pio.to_html(fig1, include_plotlyjs="cdn", full_html=True)
        assert plotly_cdn_url() in html_cdn

        html_true = pio.to_html(fig1, include_plotlyjs=True, full_html=True)
        plotlyjs = get_plotlyjs()
        # Should have plotly.js content inline (first few chars)
        assert plotlyjs[:100] in html_true

        html_false = pio.to_html(fig1, include_plotlyjs=False, full_html=True)
        assert plotly_cdn_url() not in html_false
        assert "plotly.min.js" not in html_false

    def test_resource_policy_overrides_legacy(self, fig1):
        """Test that resource_policy parameter overrides legacy params"""
        policy_set = create_policy_set(include_plotlyjs=False)
        html = pio.to_html(
            fig1,
            include_plotlyjs="cdn",
            resource_policy=policy_set,
            full_html=True,
        )
        # Should NOT have CDN URL because policy_set excludes plotlyjs
        assert plotly_cdn_url() not in html


class TestWriteHtmlWithResourcePolicy:
    """Test write_html with resource_policy parameter"""

    def test_directory_policy_copies_file(self, fig1):
        """Test that directory policy copies plotly.js to output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.html"

            pio.write_html(
                fig1,
                output_file,
                include_plotlyjs="directory",
                full_html=True,
            )

            # Check HTML file exists and references plotly.min.js
            assert output_file.exists()
            html_content = output_file.read_text()
            assert 'src="plotly.min.js"' in html_content

            # Check plotly.min.js was copied
            plotlyjs_file = Path(tmpdir) / "plotly.min.js"
            assert plotlyjs_file.exists()
            assert len(plotlyjs_file.read_text()) > 0

    def test_with_custom_directory_policy(self, fig1):
        """Test write_html with a custom DirectoryPolicy"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.html"
            custom_css = ".custom { color: green; }"

            policy_set = create_policy_set(
                include_plotlyjs="directory",
                css_content=custom_css,
            )

            pio.write_html(
                fig1,
                output_file,
                resource_policy=policy_set,
                full_html=True,
            )

            assert output_file.exists()
            html_content = output_file.read_text()
            assert custom_css in html_content

            plotlyjs_file = Path(tmpdir) / "plotly.min.js"
            assert plotlyjs_file.exists()

    def test_manifest_policy(self, fig1):
        """Test write_html with ManifestPolicy"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.html"
            manifest_path = Path(tmpdir) / "assets.json"
            public_path = "/assets/plotly.min.js"

            policy_set = ResourcePolicySet()
            policy_set.plotlyjs = ManifestPolicy(
                resource_type=ResourceType.PLOTLYJS,
                manifest_path=manifest_path,
                public_path=public_path,
            )
            policy_set.meta = InlinePolicy(
                resource_type=ResourceType.META,
                content='<meta charset="utf-8" />',
            )

            pio.write_html(
                fig1,
                output_file,
                resource_policy=policy_set,
                full_html=True,
            )

            assert output_file.exists()
            assert manifest_path.exists()

            html_content = output_file.read_text()
            assert public_path in html_content

            manifest = json.loads(manifest_path.read_text())
            assert len(manifest["resources"]) >= 1


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    def test_include_plotlyjs_directory_still_works(self, fig1):
        """Test that include_plotlyjs='directory' still copies files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.html"

            # Old API
            pio.write_html(
                fig1,
                output_file,
                include_plotlyjs="directory",
                full_html=True,
                auto_open=False,
            )

            assert output_file.exists()
            assert (Path(tmpdir) / "plotly.min.js").exists()

    def test_iframe_renderer_with_resource_policy(self, fig1):
        """Test that IFrameRenderer supports resource_policy"""
        from plotly.io._base_renderers import IFrameRenderer

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            custom_css = ".iframe-figure { max-width: 800px; }"
            policy_set = create_policy_set(
                include_plotlyjs="cdn",
                include_mathjax="cdn",
                css_content=custom_css,
            )

            renderer = IFrameRenderer(
                include_plotlyjs="cdn",
                resource_policy=policy_set,
                html_directory="test_figures",
            )

            result = renderer.to_mimebundle(fig1.to_dict())
            assert "text/html" in result

            # Check the HTML file was created
            html_files = list(Path(tmpdir).glob("test_figures/*.html"))
            assert len(html_files) > 0

            html_content = html_files[0].read_text()
            assert custom_css in html_content
            assert plotly_cdn_url() in html_content

    def test_sphinx_gallery_renderer_with_resource_policy(self, fig1):
        """Test that SphinxGalleryHtmlRenderer supports resource_policy"""
        from plotly.io._base_renderers import SphinxGalleryHtmlRenderer

        custom_css = ".sg-figure { margin: 10px; }"
        policy_set = create_policy_set(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
            css_content=custom_css,
        )

        renderer = SphinxGalleryHtmlRenderer(
            connected=True, resource_policy=policy_set
        )

        result = renderer.to_mimebundle(fig1.to_dict())
        assert "text/html" in result
        assert custom_css in result["text/html"]


class TestResourcePolicyContext:
    def test_from_legacy_params_cdn(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
        )
        assert isinstance(ctx, ResourcePolicyContext)
        assert isinstance(ctx.policy_set, ResourcePolicySet)
        head_html = ctx.get_head_html()
        assert plotly_cdn_url() in head_html
        assert "mathjax" in head_html.lower()

    def test_from_legacy_params_directory(self, fig1):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.html"
            ctx = ResourcePolicyContext.from_legacy_params(
                include_plotlyjs="directory",
                output_path=output_path,
            )
            copy_tasks = ctx.get_copy_tasks()
            assert len(copy_tasks) > 0

    def test_from_policy_set(self, fig1):
        policy_set = create_policy_set(include_plotlyjs="cdn")
        ctx = ResourcePolicyContext.from_policy_set(policy_set)
        assert ctx.policy_set is policy_set
        assert plotly_cdn_url() in ctx.get_head_html()

    def test_get_all_refs(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
        )
        refs = ctx.get_all_refs()
        assert len(refs) > 0

    def test_get_missing_hints(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
        )
        hints = ctx.get_missing_hints()
        assert isinstance(hints, list)

    def test_warn_on_missing(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ctx.warn_on_missing()
            # No warnings expected for valid CDN config
            assert len(w) == 0

    def test_policy_property_accessors(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
        )
        assert ctx.plotlyjs is not None
        assert ctx.mathjax is not None
        assert ctx.meta is not None
        assert ctx.css is None

    def test_get_and_set_policy(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
        )
        policy = ctx.get_policy(ResourceType.PLOTLYJS)
        assert policy is not None

        new_policy = InlinePolicy(resource_type=ResourceType.CSS, content="body {}")
        ctx.set_policy(ResourceType.CSS, new_policy)
        assert ctx.css is not None

    def test_output_path_defaults_html_dir(self, fig1):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "sub/test.html"
            ctx = ResourcePolicyContext.from_legacy_params(
                include_plotlyjs="directory",
                output_path=output_path,
            )
            assert ctx.html_dir == output_path.parent


class TestToHtmlWithContext:
    def test_resource_context_override(self, fig1):
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
        )
        html = pio.to_html(
            fig1,
            include_plotlyjs=False,
            include_mathjax=False,
            resource_context=ctx,
            full_html=True,
        )
        assert plotly_cdn_url() in html

    def test_resource_policy_vs_context_conflict(self, fig1):
        policy_set = create_policy_set(include_plotlyjs=False)
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
        )
        with pytest.raises(ValueError, match="Both resource_context and resource_policy"):
            pio.to_html(
                fig1,
                resource_policy=policy_set,
                resource_context=ctx,
                full_html=True,
            )


class TestWriteHtmlWithContext:
    def test_with_resource_context(self, fig1):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.html"
            ctx = ResourcePolicyContext.from_legacy_params(
                include_plotlyjs="directory",
                output_path=output_file,
            )
            pio.write_html(
                fig1,
                output_file,
                include_plotlyjs=False,
                resource_context=ctx,
                full_html=True,
                auto_open=False,
            )
            assert output_file.exists()
            assert (Path(tmpdir) / "plotly.min.js").exists()


class TestOfflinePlotWithContext:
    def test_plot_with_resource_policy(self, fig1):
        from plotly.offline import plot

        policy_set = create_policy_set(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
        )
        div = plot(
            fig1,
            output_type="div",
            include_plotlyjs=False,
            resource_policy=policy_set,
            auto_open=False,
        )
        assert plotly_cdn_url() in div

    def test_plot_with_resource_context(self, fig1):
        from plotly.offline import plot

        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
        )
        div = plot(
            fig1,
            output_type="div",
            include_plotlyjs=False,
            resource_context=ctx,
            auto_open=False,
        )
        assert plotly_cdn_url() in div

    def test_plot_file_with_overwrite_resources(self, fig1):
        from plotly.offline import plot

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = str(Path(tmpdir) / "test_plot.html")
            result = plot(
                fig1,
                output_type="file",
                filename=filename,
                include_plotlyjs="directory",
                overwrite_resources=True,
                auto_open=False,
            )
            assert result == filename
            assert Path(filename).exists()
            assert (Path(tmpdir) / "plotly.min.js").exists()


class TestRendererWithContext:
    def test_iframe_renderer_with_resource_context(self, fig1):
        from plotly.io._base_renderers import IFrameRenderer

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            custom_css = ".ctx-figure { max-width: 800px; }"
            ctx = ResourcePolicyContext.from_legacy_params(
                include_plotlyjs="cdn",
                include_mathjax="cdn",
                css_content=custom_css,
            )

            renderer = IFrameRenderer(
                resource_context=ctx,
                html_directory="ctx_figures",
            )

            result = renderer.to_mimebundle(fig1.to_dict())
            assert "text/html" in result

            html_files = list(Path(tmpdir).glob("ctx_figures/*.html"))
            assert len(html_files) > 0

            html_content = html_files[0].read_text()
            assert custom_css in html_content
            assert plotly_cdn_url() in html_content

    def test_sphinx_gallery_renderer_with_resource_context(self, fig1):
        from plotly.io._base_renderers import SphinxGalleryHtmlRenderer

        custom_css = ".sg-ctx-figure { margin: 10px; }"
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            include_mathjax="cdn",
            css_content=custom_css,
        )

        renderer = SphinxGalleryHtmlRenderer(
            connected=True, resource_context=ctx
        )

        result = renderer.to_mimebundle(fig1.to_dict())
        assert "text/html" in result
        assert custom_css in result["text/html"]

    def test_browser_renderer_with_resource_context(self, fig1):
        from plotly.io._base_renderers import BrowserRenderer

        custom_css = ".browser-figure { border: 1px solid red; }"
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            css_content=custom_css,
        )

        renderer = BrowserRenderer(resource_context=ctx)
        assert renderer.resource_context is ctx

    def test_databricks_renderer_with_resource_context(self, fig1):
        from plotly.io._base_renderers import DatabricksRenderer

        custom_css = ".databricks-figure { padding: 10px; }"
        ctx = ResourcePolicyContext.from_legacy_params(
            include_plotlyjs="cdn",
            css_content=custom_css,
        )

        renderer = DatabricksRenderer(resource_context=ctx)
        assert renderer.resource_context is ctx


class TestResolveResourceContext:
    def test_legacy_params_default(self, fig1):
        from plotly.io._resource_policy import _resolve_resource_context

        ctx = _resolve_resource_context()
        assert ctx is not None
        html = ctx.get_head_html()
        assert "plotly" in html.lower()

    def test_resource_context_pass_through(self):
        from plotly.io._resource_policy import _resolve_resource_context

        ctx = ResourcePolicyContext.from_legacy_params(include_plotlyjs="cdn")
        result = _resolve_resource_context(resource_context=ctx)
        assert result is ctx

    def test_resource_policy_builds_context(self):
        from plotly.io._resource_policy import _resolve_resource_context

        policy_set = create_policy_set(include_plotlyjs="cdn")
        ctx = _resolve_resource_context(resource_policy=policy_set)
        assert isinstance(ctx, ResourcePolicyContext)
        assert ctx.policy_set is policy_set

    def test_context_plus_policy_raises(self):
        from plotly.io._resource_policy import _resolve_resource_context

        policy_set = create_policy_set(include_plotlyjs=False)
        ctx = ResourcePolicyContext.from_legacy_params(include_plotlyjs="cdn")
        with pytest.raises(ValueError, match="Both resource_context and resource_policy"):
            _resolve_resource_context(resource_context=ctx, resource_policy=policy_set)

    def test_context_with_legacy_warns(self):
        from plotly.io._resource_policy import _resolve_resource_context

        ctx = ResourcePolicyContext.from_legacy_params(include_plotlyjs="cdn")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _resolve_resource_context(
                resource_context=ctx,
                include_plotlyjs=False,
            )
            assert result is ctx
            assert any("resource_context" in str(warning.message) for warning in w)

    def test_policy_with_legacy_warns(self):
        from plotly.io._resource_policy import _resolve_resource_context

        policy_set = create_policy_set(include_plotlyjs="cdn")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _resolve_resource_context(
                resource_policy=policy_set,
                include_plotlyjs=False,
            )
            assert isinstance(result, ResourcePolicyContext)
            assert any("resource_policy" in str(warning.message) for warning in w)

    def test_output_path_and_overwrite_propagated(self):
        from plotly.io._resource_policy import _resolve_resource_context

        ctx = _resolve_resource_context(
            include_plotlyjs="directory",
            output_path="/tmp/test/test.html",
            overwrite=True,
        )
        assert ctx.output_path == Path("/tmp/test/test.html")
        assert ctx.overwrite is True


class TestFinalizeResourceContext:
    def test_finalize_executes_copies_and_warns(self):
        from plotly.io._resource_policy import (
            _resolve_resource_context,
            _finalize_resource_context,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.html"
            ctx = _resolve_resource_context(
                include_plotlyjs="directory",
                output_path=output_file,
            )
            _finalize_resource_context(ctx)
            copied_file = Path(tmpdir) / "plotly.min.js"
            assert copied_file.exists()

    def test_finalize_warns_on_missing(self):
        from plotly.io._resource_policy import (
            _resolve_resource_context,
            _finalize_resource_context,
            DirectoryPolicy,
            ResourceType,
            ResourcePolicySet,
        )

        policy_set = ResourcePolicySet()
        policy_set.plotlyjs = DirectoryPolicy(
            resource_type=ResourceType.PLOTLYJS,
            filename="missing.js",
        )
        ctx = _resolve_resource_context(
            resource_policy=policy_set,
            output_path="/tmp/test/test.html",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _finalize_resource_context(ctx)
            assert any("no usable source" in str(warning.message).lower() for warning in w)

