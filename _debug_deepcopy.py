import copy
import plotly.graph_objects as go

fig = go.Figure()
fig.add_scatter(y=[1, 2, 3], name="test")

print(f"Original trace._customdata_columns: {fig.data[0]._customdata_columns}")

fig_copy = copy.deepcopy(fig)
print(f"Deepcopied trace._customdata_columns: {fig_copy.data[0]._customdata_columns}")

print(f"Are they equal? {fig_copy.data[0] == fig.data[0]}")

# Now add custom data
trace = go.Scatter(y=[4, 5, 6], name="test2")
trace._customdata_columns = {"a": 0}
fig2 = go.Figure()
fig2.add_trace(trace)
print(f"\nWith custom data:")
print(f"Original trace._customdata_columns: {fig2.data[0]._customdata_columns}")

fig2_copy = copy.deepcopy(fig2)
print(f"Deepcopied trace._customdata_columns: {fig2_copy.data[0]._customdata_columns}")

print(f"Are they equal? {fig2_copy.data[0] == fig2.data[0]}")
