import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

df = pd.DataFrame({'x': [1, 2, 3], 'y': [10, 20, 30], 'cat': ['a', 'b', 'a']})

fig = px.scatter(df, x='x', y='y', size='y')
print('scatter OK:', type(fig).__name__, len(fig.data))

fig2 = px.line(df, x='x', y='y')
print('line OK:', type(fig2).__name__, len(fig2.data))

fig3 = px.bar(df, x='x', y='y')
print('bar OK:', type(fig3).__name__, len(fig3.data))

fig4 = px.histogram(df, x='x')
print('histogram OK:', type(fig4).__name__, len(fig4.data))

print('scatter._chart_name:', px.scatter._chart_name)
print('bar._chart_name:', px.bar._chart_name)

# Test with color + barmode
fig5 = px.bar(df, x='x', y='y', color='cat', barmode='group')
print('bar+group OK:', type(fig5).__name__, len(fig5.data))

# Test histogram with patches
fig6 = px.histogram(df, x='x', y='y', histfunc='sum', barnorm='percent')
print('histogram+patches OK:', type(fig6).__name__, len(fig6.data))

# Test scatter with trendline
fig7 = px.scatter(df, x='x', y='y', trendline='ols')
print('scatter+trendline OK:', type(fig7).__name__, len(fig7.data))

# Test that docstrings are preserved
print('scatter doc starts:', (px.scatter.__doc__ or '')[:50])
print('bar doc starts:', (px.bar.__doc__ or '')[:50])

# Test non-core4 still work
fig8 = px.pie(df, values='y', names='cat')
print('pie OK:', type(fig8).__name__, len(fig8.data))

print('\nAll basic tests passed!')
