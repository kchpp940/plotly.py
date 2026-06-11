import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "category": ["A", "A", "B", "B", "C", "C"],
    "value": [10, 20, 30, 40, 50, 60],
    "group": ["X", "Y", "X", "Y", "X", "Y"],
})

# Let's trace through px.bar to see where summary gets lost
print("Testing px.bar with dict summary...")
print()

import plotly.graph_objs as go
from plotly.express._core import (
    apply_default_cascade, build_dataframe, infer_config, get_groups_and_orders,
    SummaryContext, one_group, make_figure,
)

# Simulate what px.bar does
args = dict(
    data_frame=df,
    x="category",
    y="value",
    color="group",
    summary=dict(type="percent", show="all", format=".2f"),
)

print(f"Before apply_default_cascade: summary = {args.get('summary')}")

trace_patch = dict(
    histnorm=None,
    histfunc=None,
    cumulative=dict(enabled=None),
)
layout_patch = dict(barmode="relative", barnorm=None)

apply_default_cascade(args, constructor=go.Bar)
print(f"After apply_default_cascade: summary = {args.get('summary')}")

args = build_dataframe(args, go.Bar)
print(f"After build_dataframe: summary = {args.get('summary')}")

trace_specs, grouped_mappings, sizeref, show_colorbar = infer_config(
    args, go.Bar, trace_patch, layout_patch
)
grouper = [x.grouper or one_group for x in grouped_mappings] or [one_group]
groups, orders = get_groups_and_orders(args, grouper)

print(f"Number of groups: {len(groups)}")

summary_ctx = SummaryContext(args, go.Bar, grouped_mappings, grouper, orders)
print(f"summary_ctx.is_active(): {summary_ctx.is_active()}")
print(f"summary_ctx.specs: {summary_ctx.specs}")

for g_name in groups.keys():
    stats = summary_ctx.compute_stats(g_name, groups[g_name])
    print(f"  Group {g_name}: stats = {stats}")
