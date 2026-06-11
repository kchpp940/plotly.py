import warnings; warnings.filterwarnings("ignore")
import plotly.express as px

scatter_doc = px.scatter.__doc__ or ""
line_doc = px.line.__doc__ or ""
bar_doc = px.bar.__doc__ or ""
hist_doc = px.histogram.__doc__ or ""

print("scatter has trendline*:", "trendline_options" in scatter_doc)
print("scatter has lines (should be False - not in sig):", "    lines:" in scatter_doc)
print("line has trendline (should be False):", "trendline_options" in line_doc)
print("line has line_group:", "    line_group:" in line_doc)
print("bar has barnorm (should be False):", "    barnorm:" in bar_doc)
print("histogram has barnorm:", "    barnorm:" in hist_doc)
print("histogram has color_continuous_scale (should be False):", "color_continuous_scale" in hist_doc)
print("bar has color_continuous_scale:", "color_continuous_scale" in bar_doc)
print()
print("SUCCESS")
