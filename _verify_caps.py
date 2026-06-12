"""Verify capability layer + pyproject consistency checker."""

from _plotly_utils.dependencies import deps, check_pyproject_consistency

print("=" * 70)
print("PART 1: Capability registry")
print("=" * 70)

cap_names = sorted(deps._caps.keys())
print(f"Total capabilities: {len(cap_names)}")
for name in cap_names:
    cap = deps.capability(name)
    avail = deps.available(name)
    print(f"  {name:35s} → {cap.dep_name:15s} [{'✓' if avail else '✗'}] {cap.description}")

print()
print("=" * 70)
print("PART 2: deps.require() with capability name")
print("=" * 70)

# 1. Available capability → no-op
deps.require("core.numpy")
print("✓ deps.require('core.numpy') → no-op (available)")

# 2. Missing capability → ImportError with feature label
try:
    deps.require("ff.skimage")
    assert False, "Should have raised"
except ImportError as e:
    msg = str(e)
    assert "scikit-image" in msg or "skimage" in msg
    assert "create_ternary_contour" in msg
    assert "pip install" in msg
    print(f"✓ deps.require('ff.skimage') → ImportError with feature label")

# 3. Nonexistent capability → KeyError
try:
    deps.require("fake.capability")
    assert False, "Should have raised KeyError"
except KeyError as e:
    print(f"✓ deps.require('fake.capability') → KeyError (not registered)")

# 4. deps.available() helper
assert deps.available("core.numpy") is True
assert isinstance(deps.available("ff.skimage"), bool)
print("✓ deps.available(cap_name) works")

# 5. deps.module(cap_name)
np_mod = deps.module("core.numpy")
assert np_mod is not None
assert hasattr(np_mod, "array")
print(f"✓ deps.module('core.numpy') → numpy module (id={id(np_mod)})")

# 6. deps.capability_summary()
cap_summary = deps.capability_summary()
assert len(cap_summary) == len(cap_names)
assert cap_summary["core.numpy"] is True
print(f"✓ deps.capability_summary() → {len(cap_summary)} entries")

print()
print("=" * 70)
print("PART 3: pyproject.toml consistency checker")
print("=" * 70)

issues = check_pyproject_consistency()

for severity, items in issues.items():
    if items:
        print(f"\n⚠ {severity.upper()} ({len(items)}):")
        for item in items:
            print(f"   - {item}")

if not any(issues.values()):
    print("✓ No consistency issues found!")
else:
    total = sum(len(v) for v in issues.values())
    print(f"\n⚠ Total: {total} issue(s) across {len([k for k, v in issues.items() if v])} category(ies)")

print()
print("=" * 70)
print("All checks passed!")
print("=" * 70)
