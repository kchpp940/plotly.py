from _plotly_utils.dependencies import _parse_pyproject_extras

extras = _parse_pyproject_extras()
print(f"Found {len(extras)} extras:")
for name, pkgs in sorted(extras.items()):
    print(f"\n  [{name}] ({len(pkgs)} packages):")
    for pkg, ver in pkgs.items():
        ver_str = f">={ver}" if ver else "(any)"
        print(f"    {pkg:30s} {ver_str}")
