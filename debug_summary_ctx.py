import plotly.express as px
import pandas as pd
from plotly.express._core import SummaryContext, one_group

df = pd.DataFrame({
    "category": ["A", "A", "B", "B", "C", "C"],
    "value": [10, 20, 30, 40, 50, 60],
    "group": ["X", "Y", "X", "Y", "X", "Y"],
})

args = dict(
    data_frame=df,
    x="category",
    y="value",
    color="group",
    summary=dict(type="percent", show="all", format=".2f"),
    orientation="v",
    labels={},
    title=None,
    template=None,
    width=None,
    height=None,
    category_orders=None,
    color_discrete_sequence=None,
    color_discrete_map=None,
    color_continuous_scale=None,
    range_color=None,
    color_continuous_midpoint=None,
    pattern_shape_sequence=None,
    pattern_shape_map=None,
    opacity=None,
    barmode="relative",
    barnorm=None,
    histnorm=None,
    log_x=False,
    log_y=False,
    range_x=None,
    range_y=None,
    histfunc=None,
    cumulative=None,
    nbins=None,
    text_auto=False,
    marginal_x=None,
    marginal_y=None,
    animation_frame=None,
    animation_group=None,
    hover_name=None,
    hover_data=None,
    facet_row=None,
    facet_col=None,
    facet_col_wrap=0,
    facet_row_spacing=None,
    facet_col_spacing=None,
)

import plotly.graph_objs as go
from plotly.express._core import (
    apply_default_cascade, build_dataframe, infer_config, get_groups_and_orders,
)

apply_default_cascade(args, constructor=go.Bar)
args = build_dataframe(args, go.Bar)

trace_patch = {}
layout_patch = {}
trace_specs, grouped_mappings, sizeref, show_colorbar = infer_config(
    args, go.Bar, trace_patch, layout_patch
)
grouper = [x.grouper or one_group for x in grouped_mappings] or [one_group]
groups, orders = get_groups_and_orders(args, grouper)

print(f"Number of groups: {len(groups)}")
for g_name, g_df in groups.items():
    print(f"  {g_name}: {len(g_df)} rows")

print()
print("Creating SummaryContext...")
ctx = SummaryContext(args, go.Bar, grouped_mappings, grouper, orders)
print(f"is_active: {ctx.is_active()}")
print(f"specs: {ctx.specs}")
print()

for g_name in groups.keys():
    print(f"Group {g_name}:")
    stats = ctx.compute_stats(g_name, groups[g_name])
    print(f"  stats: {stats}")
    print(f"  text_html: {ctx.get_text_html(g_name)}")
    print(f"  text_plain: {ctx.get_text_plain(g_name)}")
    print(f"  should_show('annotation'): {ctx.should_show('annotation')}")
    print(f"  should_show('legend'): {ctx.should_show('legend')}")
    print(f"  should_show('hover'): {ctx.should_show('hover')}")

    base_name = ctx.get_group_trace_name(g_name)
    print(f"  base_name: {base_name}")
    print(f"  name_with_summary: {ctx.get_trace_name_with_summary(base_name, g_name)}")
    print()
