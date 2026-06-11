import warnings; warnings.filterwarnings("ignore")
import plotly.express as px

def extract_param_names(doc: str) -> list[str]:
    """Roughly extract 'param_name:' from docstring Parameters section."""
    if not doc:
        return []
    in_params = False
    params = []
    for line in doc.split("\n"):
        if "Parameters" in line and "----------" in doc:
            in_params = True
            continue
        if in_params and line.strip() == "Returns":
            break
        if in_params and ":" in line and not line.startswith("       "):
            # Match first word before colon
            stripped = line.strip()
            colon_idx = stripped.find(":")
            if colon_idx > 0:
                pname = stripped[:colon_idx].strip()
                if pname and " " not in pname:
                    params.append(pname)
    return params

scatter_params = extract_param_names(px.scatter.__doc__ or "")
line_params = extract_param_names(px.line.__doc__ or "")
bar_params = extract_param_names(px.bar.__doc__ or "")
hist_params = extract_param_names(px.histogram.__doc__ or "")

print("scatter doc params count:", len(scatter_params))
print("  has trendline_options:", "trendline_options" in scatter_params)
print("  has orientation:", "orientation" in scatter_params)
print("  has lines:", "lines" in scatter_params)

print("\nline doc params count:", len(line_params))
print("  has line_group:", "line_group" in line_params)
print("  has orientation:", "orientation" in line_params)
print("  has trendline_options:", "trendline_options" in line_params)
print("  all:", line_params)

print("\nbar doc params count:", len(bar_params))
print("  has barnorm:", "barnorm" in bar_params)
print("  has color_continuous_scale:", "color_continuous_scale" in bar_params)
print("  has orientation:", "orientation" in bar_params)
print("  all:", bar_params)

print("\nhist doc params count:", len(hist_params))
print("  has barnorm:", "barnorm" in hist_params)
print("  has nbins:", "nbins" in hist_params)
print("  has color_continuous_scale:", "color_continuous_scale" in hist_params)
print("  all:", hist_params[:30], "...")
