"""
Resource Policy module for Plotly HTML export.

This module provides a unified, pluggable resource management system
for handling plotly.js, MathJax, CSS, and meta tags in HTML exports.
"""

import os
import json
import hashlib
import base64
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union, Dict, List, Any, Callable


def _generate_sri_hash(content: Union[str, bytes]) -> str:
    """Generate SHA256 hash for SRI (Subresource Integrity)."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    sha256_hash = hashlib.sha256(content).digest()
    return "sha256-" + base64.b64encode(sha256_hash).decode("utf-8")


class ResourceType:
    """Constants for resource types."""
    PLOTLYJS = "plotlyjs"
    MATHJAX = "mathjax"
    CSS = "css"
    META = "meta"


class PolicyType:
    """Constants for policy types."""
    INLINE = "inline"
    CDN = "cdn"
    DIRECTORY = "directory"
    URL = "url"
    MANIFEST = "manifest"
    EXCLUDE = "exclude"


@dataclass
class ResourceRef:
    """Represents a resource reference in HTML."""
    html: str
    copy_target: Optional[Path] = None
    copy_source: Optional[Path] = None
    relative_path: Optional[str] = None
    missing_hint: Optional[str] = None
    needs_copy: bool = False


@dataclass
class BaseResourcePolicy:
    """
    Abstract base class for resource policies.

    A resource policy determines how a specific resource (plotly.js,
    MathJax, CSS, meta tags) is included in HTML output.
    """

    resource_type: str
    content: Optional[str] = None
    url: Optional[str] = None
    cdn_url: Optional[str] = None
    filename: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        """
        Generate a resource reference.

        Parameters
        ----------
        output_path : Path, optional
            The path where the HTML file will be written.
        html_dir : Path, optional
            The directory relative to which paths should be calculated.

        Returns
        -------
        ResourceRef
            Contains HTML string, copy targets, and other metadata.
        """
        raise NotImplementedError()

    def needs_copy(self) -> bool:
        """Whether this policy requires copying files."""
        return False


class InlinePolicy(BaseResourcePolicy):
    """
    Policy for including resource content inline in HTML.

    For JavaScript and CSS, this embeds the content directly in
    <script> or <style> tags.
    """

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        if self.content is None:
            return ResourceRef(html="", missing_hint=self._get_missing_hint())

        if self.resource_type == ResourceType.META:
            html = self.content
        elif self.resource_type == ResourceType.CSS:
            html = f'<style {self._format_attributes()}>\n{self.content}\n</style>'
        else:
            html = f'<script {self._format_attributes()}>\n{self.content}\n</script>'

        return ResourceRef(html=html)

    def _format_attributes(self) -> str:
        return " ".join(f'{k}="{v}"' for k, v in self.attributes.items())

    def _get_missing_hint(self) -> str:
        return (
            f"Inline content for {self.resource_type} is None. "
            f"Provide content or use a different policy type."
        )


@dataclass
class CdnPolicy(BaseResourcePolicy):
    """
    Policy for loading resources from a CDN.

    Generates <script> or <link> tags with CDN URLs.
    Supports SRI (Subresource Integrity) hashes for security.
    """

    sri: bool = True

    def __init__(self, resource_type: str, cdn_url: str, sri: bool = True, **kwargs):
        kwargs["resource_type"] = resource_type
        kwargs["cdn_url"] = cdn_url
        super().__init__(**kwargs)
        self.sri = sri

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        if not self.cdn_url:
            return ResourceRef(html="", missing_hint=self._get_missing_hint())

        attributes = dict(self.attributes)
        if self.sri and self.content:
            integrity = _generate_sri_hash(self.content)
            attributes["integrity"] = integrity
            attributes["crossorigin"] = "anonymous"

        attr_str = " ".join(f'{k}="{v}"' for k, v in attributes.items())
        if attr_str:
            attr_str = " " + attr_str

        if self.resource_type == ResourceType.META:
            html = f'<meta{attr_str} />'
        elif self.resource_type == ResourceType.CSS:
            html = f'<link rel="stylesheet" href="{self.cdn_url}"{attr_str} />'
        else:
            html = f'<script src="{self.cdn_url}"{attr_str}></script>'

        return ResourceRef(html=html)

    def _get_missing_hint(self) -> str:
        return (
            f"CDN URL for {self.resource_type} is not configured. "
            f"Provide a valid CDN URL."
        )


@dataclass
class DirectoryPolicy(BaseResourcePolicy):
    """
    Policy for copying resources to the output directory.

    Copies the resource file to the same directory as the HTML file
    (or a specified subdirectory) and references it with a relative path.
    """

    def __init__(
        self,
        resource_type: str,
        filename: str,
        source_path: Optional[Union[str, Path]] = None,
        content: Optional[str] = None,
        subdir: Optional[str] = None,
        **kwargs,
    ):
        if subdir:
            filename = os.path.join(subdir, filename)

        if source_path is not None and content is None:
            source = Path(source_path)
            content = source.read_text(encoding="utf-8")

        kwargs["resource_type"] = resource_type
        kwargs["filename"] = filename
        kwargs["content"] = content
        super().__init__(**kwargs)
        self._source_path = Path(source_path) if source_path else None

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        if not self.filename:
            return ResourceRef(html="", missing_hint=self._get_missing_hint())

        base_dir = html_dir or (output_path.parent if output_path else Path("."))
        target_path = base_dir / self.filename
        relative_path = self.filename

        attr_str = self._format_attributes()

        if self.resource_type == ResourceType.CSS:
            html = f'<link rel="stylesheet" href="{relative_path}"{attr_str} />'
        else:
            html = f'<script src="{relative_path}"{attr_str}></script>'

        return ResourceRef(
            html=html,
            copy_source=self._source_path,
            copy_target=target_path,
            relative_path=relative_path,
            needs_copy=True,
        )

    def needs_copy(self) -> bool:
        return True

    def write_content(self, target_path: Path) -> None:
        """
        Write content directly to the target path.

        Used when no source_path is provided but content is available.
        """
        if self.content is None:
            raise ValueError(f"No content available for {self.resource_type}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(self.content, bytes):
            target_path.write_bytes(self.content)
        else:
            target_path.write_text(self.content, encoding="utf-8")

    def _format_attributes(self) -> str:
        attrs = " ".join(f'{k}="{v}"' for k, v in self.attributes.items())
        return " " + attrs if attrs else ""

    def _get_missing_hint(self) -> str:
        return (
            f"Filename for {self.resource_type} is not configured. "
            f"Provide a valid filename for the directory policy."
        )


class UrlPolicy(BaseResourcePolicy):
    """
    Policy for referencing resources via custom URLs.

    Similar to CDN policy but for arbitrary URLs (local or remote).
    """

    def __init__(self, resource_type: str, url: str, **kwargs):
        super().__init__(resource_type=resource_type, url=url, **kwargs)

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        if not self.url:
            return ResourceRef(html="", missing_hint=self._get_missing_hint())

        attr_str = self._format_attributes()

        if self.resource_type == ResourceType.META:
            html = f'<meta{attr_str} />'
        elif self.resource_type == ResourceType.CSS:
            html = f'<link rel="stylesheet" href="{self.url}"{attr_str} />'
        else:
            html = f'<script src="{self.url}"{attr_str}></script>'

        return ResourceRef(html=html)

    def _format_attributes(self) -> str:
        attrs = " ".join(f'{k}="{v}"' for k, v in self.attributes.items())
        return " " + attrs if attrs else ""

    def _get_missing_hint(self) -> str:
        return (
            f"URL for {self.resource_type} is not configured. "
            f"Provide a valid URL."
        )


class ManifestPolicy(BaseResourcePolicy):
    """
    Policy for managing resources via a manifest file.

    Records resource information in a JSON manifest file for
    integration with build tools and asset pipelines.
    """

    def __init__(
        self,
        resource_type: str,
        manifest_path: Union[str, Path],
        source_path: Optional[Union[str, Path]] = None,
        public_path: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(resource_type=resource_type, **kwargs)
        self._manifest_path = Path(manifest_path)
        self._source_path = Path(source_path) if source_path else None
        self._public_path = public_path

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        base_dir = html_dir or (output_path.parent if output_path else Path("."))
        manifest_path = self._manifest_path
        if not manifest_path.is_absolute():
            manifest_path = base_dir / manifest_path

        resource_entry = {
            "type": self.resource_type,
            "policy": PolicyType.MANIFEST,
        }

        if self._source_path:
            resource_entry["source"] = str(self._source_path)
            resource_entry["hash"] = self._compute_hash()

        if self._public_path:
            resource_entry["url"] = self._public_path

        self._update_manifest(manifest_path, resource_entry)

        if self._public_path:
            attr_str = self._format_attributes()
            if self.resource_type == ResourceType.CSS:
                html = f'<link rel="stylesheet" href="{self._public_path}"{attr_str} />'
            else:
                html = f'<script src="{self._public_path}"{attr_str}></script>'
        else:
            html = ""

        return ResourceRef(
            html=html,
            relative_path=self._public_path,
        )

    def _compute_hash(self) -> str:
        if not self._source_path or not self._source_path.exists():
            return ""
        content = self._source_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _update_manifest(self, manifest_path: Path, entry: Dict[str, Any]) -> None:
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except (json.JSONDecodeError, IOError):
                manifest = {}

        if "resources" not in manifest:
            manifest["resources"] = []

        manifest["resources"].append(entry)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))

    def _format_attributes(self) -> str:
        attrs = " ".join(f'{k}="{v}"' for k, v in self.attributes.items())
        return " " + attrs if attrs else ""


class ExcludePolicy(BaseResourcePolicy):
    """
    Policy for excluding a resource entirely.

    No reference is generated, no files are copied.
    """

    def __init__(self, resource_type: str, **kwargs):
        super().__init__(resource_type=resource_type, **kwargs)

    def get_ref(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> ResourceRef:
        return ResourceRef(html="")


@dataclass
class ResourcePolicySet:
    """
    A collection of resource policies for all resource types.

    This class manages policies for plotly.js, MathJax, CSS, and meta tags,
    and provides methods to generate all resource references and execute
    file copies.
    """

    plotlyjs: Optional[BaseResourcePolicy] = None
    mathjax: Optional[BaseResourcePolicy] = None
    css: Optional[BaseResourcePolicy] = None
    meta: Optional[BaseResourcePolicy] = None
    extra_resources: Dict[str, BaseResourcePolicy] = field(default_factory=dict)

    def get_policy(self, resource_type: str) -> Optional[BaseResourcePolicy]:
        """Get the policy for a specific resource type."""
        if resource_type == ResourceType.PLOTLYJS:
            return self.plotlyjs
        elif resource_type == ResourceType.MATHJAX:
            return self.mathjax
        elif resource_type == ResourceType.CSS:
            return self.css
        elif resource_type == ResourceType.META:
            return self.meta
        else:
            return self.extra_resources.get(resource_type)

    def set_policy(self, resource_type: str, policy: BaseResourcePolicy) -> None:
        """Set the policy for a specific resource type."""
        if resource_type == ResourceType.PLOTLYJS:
            self.plotlyjs = policy
        elif resource_type == ResourceType.MATHJAX:
            self.mathjax = policy
        elif resource_type == ResourceType.CSS:
            self.css = policy
        elif resource_type == ResourceType.META:
            self.meta = policy
        else:
            self.extra_resources[resource_type] = policy

    def get_all_refs(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> List[ResourceRef]:
        """
        Generate all resource references.

        Returns
        -------
        list of ResourceRef
            All resource references in order: meta, plotlyjs config,
            plotlyjs, mathjax, css, then extra resources.
        """
        refs = []

        if self.meta:
            refs.append(self.meta.get_ref(output_path, html_dir))

        if self.plotlyjs:
            from plotly.offline.offline import _window_plotly_config
            config_ref = ResourceRef(html=_window_plotly_config)
            refs.append(config_ref)
            refs.append(self.plotlyjs.get_ref(output_path, html_dir))

        if self.mathjax:
            from plotly.offline.offline import _mathjax_config
            refs.append(self.mathjax.get_ref(output_path, html_dir))
            config_ref = ResourceRef(html=_mathjax_config)
            refs.append(config_ref)

        if self.css:
            refs.append(self.css.get_ref(output_path, html_dir))

        for resource in self.extra_resources.values():
            refs.append(resource.get_ref(output_path, html_dir))

        return refs

    def get_head_html(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> str:
        """
        Generate HTML for the <head> section.

        Returns
        -------
        str
            All resource reference HTML strings joined with newlines.
        """
        refs = self.get_all_refs(output_path, html_dir)
        return "\n".join(ref.html for ref in refs if ref.html)

    def get_copy_tasks(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
    ) -> List[ResourceRef]:
        """
        Get all copy tasks.

        Returns
        -------
        list of ResourceRef
            Only resources that need to be copied.
        """
        refs = self.get_all_refs(output_path, html_dir)
        return [ref for ref in refs if ref.needs_copy and ref.copy_target]

    def execute_copies(
        self,
        output_path: Optional[Path] = None,
        html_dir: Optional[Path] = None,
        overwrite: bool = False,
    ) -> List[Path]:
        """
        Execute all file copy operations.

        Parameters
        ----------
        output_path : Path, optional
            Path to the HTML output file.
        html_dir : Path, optional
            Directory for relative path calculation.
        overwrite : bool, default False
            Whether to overwrite existing files.

        Returns
        -------
        list of Path
            Paths of files that were copied.
        """
        copied = []
        tasks = self.get_copy_tasks(output_path, html_dir)

        for task in tasks:
            if not task.copy_target:
                continue

            if task.copy_target.exists() and not overwrite:
                continue

            task.copy_target.parent.mkdir(parents=True, exist_ok=True)

            if task.copy_source:
                content = task.copy_source.read_bytes()
                task.copy_target.write_bytes(content)
            else:
                policy = self._find_policy_for_ref(task)
                if policy and isinstance(policy, DirectoryPolicy) and policy.content is not None:
                    policy.write_content(task.copy_target)

            copied.append(task.copy_target)

        return copied

    def _find_policy_for_ref(self, ref: ResourceRef) -> Optional[BaseResourcePolicy]:
        """Find the policy that generated a given ResourceRef."""
        for policy in [self.plotlyjs, self.mathjax, self.css, self.meta]:
            if policy is None:
                continue
            try:
                policy_ref = policy.get_ref()
                if policy_ref.html == ref.html:
                    return policy
            except Exception:
                pass

        for policy in self.extra_resources.values():
            try:
                policy_ref = policy.get_ref()
                if policy_ref.html == ref.html:
                    return policy
            except Exception:
                pass

        return None

    def get_missing_hints(self) -> List[str]:
        """
        Get all missing resource hints.

        Returns
        -------
        list of str
            Warning messages for missing or misconfigured resources.
        """
        hints = []
        refs = self.get_all_refs()
        for ref in refs:
            if ref.missing_hint:
                hints.append(ref.missing_hint)
        return hints


def policy_from_include_plotlyjs(
    include_plotlyjs: Union[bool, str],
    plotlyjs_source: Optional[Union[str, Path]] = None,
    plotlyjs_cdn_url: Optional[str] = None,
    plotlyjs_content: Optional[str] = None,
) -> Optional[BaseResourcePolicy]:
    """
    Create a plotly.js policy from the legacy include_plotlyjs parameter.

    Parameters
    ----------
    include_plotlyjs : bool or str
        Legacy include_plotlyjs parameter value.
        Supported values: True, False, 'cdn', 'directory', or a path ending in '.js'.
    plotlyjs_source : str or Path, optional
        Path to the plotly.js source file for directory policy.
    plotlyjs_cdn_url : str, optional
        CDN URL for plotly.js.
    plotlyjs_content : str, optional
        plotly.js content for inline and SRI hash generation.

    Returns
    -------
    BaseResourcePolicy or None
    """
    if include_plotlyjs is False:
        return ExcludePolicy(resource_type=ResourceType.PLOTLYJS)

    if isinstance(include_plotlyjs, str):
        include_lower = include_plotlyjs.lower()

        if include_lower == "cdn":
            return CdnPolicy(
                resource_type=ResourceType.PLOTLYJS,
                cdn_url=plotlyjs_cdn_url or "",
                content=plotlyjs_content,
                attributes={"charset": "utf-8"},
            )

        if include_lower == "directory":
            return DirectoryPolicy(
                resource_type=ResourceType.PLOTLYJS,
                filename="plotly.min.js",
                source_path=plotlyjs_source,
                content=plotlyjs_content,
                attributes={"charset": "utf-8"},
            )

        if include_plotlyjs.endswith(".js"):
            return UrlPolicy(
                resource_type=ResourceType.PLOTLYJS,
                url=include_plotlyjs,
                attributes={"charset": "utf-8"},
            )

    if include_plotlyjs is True:
        return InlinePolicy(
            resource_type=ResourceType.PLOTLYJS,
            content=plotlyjs_content,
        )

    return None


def policy_from_include_mathjax(
    include_mathjax: Union[bool, str],
    mathjax_cdn_url: str = "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js",
) -> Optional[BaseResourcePolicy]:
    """
    Create a MathJax policy from the legacy include_mathjax parameter.

    Parameters
    ----------
    include_mathjax : bool or str
        Legacy include_mathjax parameter value.
        Supported values: False, 'cdn', or a path ending in '.js'.
    mathjax_cdn_url : str, optional
        CDN URL for MathJax.

    Returns
    -------
    BaseResourcePolicy or None
    """
    if include_mathjax is False:
        return None

    if isinstance(include_mathjax, str):
        include_lower = include_mathjax.lower()

        if include_lower == "cdn":
            return UrlPolicy(
                resource_type=ResourceType.MATHJAX,
                url=mathjax_cdn_url + "?config=TeX-AMS-MML_SVG",
            )

        if include_mathjax.endswith(".js"):
            return UrlPolicy(
                resource_type=ResourceType.MATHJAX,
                url=include_mathjax + "?config=TeX-AMS-MML_SVG",
            )

    return None


def create_policy_set(
    include_plotlyjs: Union[bool, str] = True,
    include_mathjax: Union[bool, str] = False,
    plotlyjs_source: Optional[Union[str, Path]] = None,
    plotlyjs_cdn_url: Optional[str] = None,
    plotlyjs_content: Optional[str] = None,
    mathjax_cdn_url: Optional[str] = None,
    css_content: Optional[str] = None,
    css_url: Optional[str] = None,
    meta_tags: Optional[Dict[str, str]] = None,
    include_meta_charset: bool = True,
) -> ResourcePolicySet:
    """
    Create a ResourcePolicySet from legacy parameters.

    This is the main compatibility layer that converts the old-style
    include_plotlyjs/include_mathjax parameters into a full ResourcePolicySet.

    Parameters
    ----------
    include_plotlyjs : bool or str, default True
        Legacy include_plotlyjs parameter.
    include_mathjax : bool or str, default False
        Legacy include_mathjax parameter.
    plotlyjs_source : str or Path, optional
        Path to plotly.js source file.
    plotlyjs_cdn_url : str, optional
        CDN URL for plotly.js.
    plotlyjs_content : str, optional
        plotly.js content for inline embedding.
    mathjax_cdn_url : str, optional
        CDN URL for MathJax.
    css_content : str, optional
        Custom CSS content to inline.
    css_url : str, optional
        URL to custom CSS stylesheet.
    meta_tags : dict, optional
        Additional meta tags as name/content pairs.
    include_meta_charset : bool, default True
        Whether to include <meta charset="utf-8">.

    Returns
    -------
    ResourcePolicySet
    """
    from plotly.io._utils import plotly_cdn_url as _plotly_cdn_url
    from plotly.offline.offline import get_plotlyjs

    policy_set = ResourcePolicySet()

    # Set defaults for plotly.js if not provided
    if plotlyjs_cdn_url is None:
        plotlyjs_cdn_url = _plotly_cdn_url()
    if plotlyjs_content is None and include_plotlyjs is not False:
        try:
            plotlyjs_content = get_plotlyjs()
        except Exception:
            pass

    plotlyjs_policy = policy_from_include_plotlyjs(
        include_plotlyjs,
        plotlyjs_source=plotlyjs_source,
        plotlyjs_cdn_url=plotlyjs_cdn_url,
        plotlyjs_content=plotlyjs_content,
    )
    if plotlyjs_policy:
        policy_set.plotlyjs = plotlyjs_policy

    mathjax_policy = policy_from_include_mathjax(
        include_mathjax,
        mathjax_cdn_url=mathjax_cdn_url or "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js",
    )
    if mathjax_policy:
        policy_set.mathjax = mathjax_policy

    if css_content:
        policy_set.css = InlinePolicy(
            resource_type=ResourceType.CSS,
            content=css_content,
        )
    elif css_url:
        policy_set.css = UrlPolicy(
            resource_type=ResourceType.CSS,
            url=css_url,
        )

    meta_parts = []
    if include_meta_charset:
        meta_parts.append('<meta charset="utf-8" />')
    if meta_tags:
        for name, content in meta_tags.items():
            meta_parts.append(f'<meta name="{name}" content="{content}" />')

    if meta_parts:
        policy_set.meta = InlinePolicy(
            resource_type=ResourceType.META,
            content="\n".join(meta_parts),
        )

    return policy_set
