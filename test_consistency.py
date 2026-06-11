import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "category": ["A", "A", "B", "B", "C", "C"],
    "value": [10, 20, 30, 40, 50, 60],
    "group": ["X", "Y", "X", "Y", "X", "Y"],
})

print("Verifying consistent summary text across legend, hover, and annotation...")
print()

fig = px.bar(
    df, x="category", y="value", color="group",
    summary=dict(type="percent", show="all", format=".2f")
)

print("Group X:")
print(f"  Legend name: {fig.data[0].name}")

# Extract hover text
hover = fig.data[0].hovertemplate
import re
extra_match = re.search(r'<extra>(.*?)</extra>', hover)
if extra_match:
    print(f"  Hover extra: {extra_match.group(1)}")

print(f"  Annotation text: {fig.layout.annotations[0].text}")
print()

print("Group Y:")
print(f"  Legend name: {fig.data[1].name}")

hover = fig.data[1].hovertemplate
extra_match = re.search(r'<extra>(.*?)</extra>', hover)
if extra_match:
    print(f"  Hover extra: {extra_match.group(1)}")

print(f"  Annotation text: {fig.layout.annotations[1].text}")
print()

# Check consistency
print("Consistency check:")
for i, trace in enumerate(fig.data):
    legend_text = trace.name
    # Extract summary part from legend (after " (" and before ")")
    import re
    m = re.search(r'\((.+)\)', legend_text)
    legend_summary = m.group(1) if m else ""

    hover = trace.hovertemplate
    m2 = re.search(r'<extra>(.*?)</extra>', hover)
    hover_summary = m2.group(1) if m2 else ""

    annot_text = fig.layout.annotations[i].text
    # Remove the bold group name part
    import re
    m3 = re.search(r'<br>(.+)', annot_text)
    annot_summary = m3.group(1) if m3 else ""

    # Normalize: replace <br> with ", "
    legend_norm = legend_summary.replace(", ", "<br>")
    hover_norm = hover_summary
    annot_norm = annot_summary

    print(f"  Group {i}:")
    print(f"    Legend summary:  {legend_summary}")
    print(f"    Hover summary:   {hover_summary}")
    print(f"    Annot summary:   {annot_summary}")
    print(f"    Consistent: {legend_norm == hover_norm == annot_norm}")
