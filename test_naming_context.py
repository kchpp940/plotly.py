import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
import numpy as np

np.random.seed(42)

df = pd.DataFrame({
    'x': np.random.randn(100),
    'y': np.random.randn(100),
    'color': np.random.choice(['A', 'B', 'C'], 100),
    'symbol': np.random.choice(['X', 'Y'], 100),
    'line_dash': np.random.choice(['solid', 'dash'], 100),
    'facet_col': np.random.choice(['F1', 'F2'], 100),
    'facet_row': np.random.choice(['R1', 'R2'], 100),
    'animation_frame': np.random.choice([2020, 2021, 2022], 100),
    'size': np.random.randint(10, 100, 100),
})


def test_basic_scatter():
    fig = px.scatter(df, x='x', y='y')
    traces = fig.data
    assert len(traces) == 1, f"Expected 1 trace, got {len(traces)}"
    assert traces[0].name == "", f"Expected empty name, got '{traces[0].name}'"
    assert traces[0].showlegend == False, f"Expected showlegend=False, got {traces[0].showlegend}"
    print("✓ test_basic_scatter passed")


def test_color_grouped():
    fig = px.scatter(df, x='x', y='y', color='color')
    traces = fig.data
    names = [t.name for t in traces]
    legendgroups = [t.legendgroup for t in traces]
    showlegends = [t.showlegend for t in traces]
    
    assert len(traces) == 3, f"Expected 3 traces, got {len(traces)}"
    assert set(names) == {'A', 'B', 'C'}, f"Expected names A,B,C, got {names}"
    assert names == legendgroups, "legendgroup should match name"
    assert all(showlegends), "All traces should have showlegend=True"
    assert fig.layout.legend.title.text == 'color', f"Expected legend title 'color', got '{fig.layout.legend.title.text}'"
    print("✓ test_color_grouped passed")


def test_color_symbol_grouped():
    fig = px.scatter(df, x='x', y='y', color='color', symbol='symbol')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 6, f"Expected 6 traces, got {len(traces)}"
    for name in names:
        assert ', ' in name, f"Name should contain comma separator: '{name}'"
    assert fig.layout.legend.title.text == 'color, symbol', f"Expected 'color, symbol', got '{fig.layout.legend.title.text}'"
    print("✓ test_color_symbol_grouped passed")


def test_color_symbol_linedash_line():
    df_line = df.copy()
    df_line = df_line.sort_values('x')
    fig = px.line(df_line, x='x', y='y', color='color', symbol='symbol', line_dash='line_dash')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 12, f"Expected 12 traces, got {len(traces)}"
    assert fig.layout.legend.title.text == 'color, line_dash, symbol', f"Expected 'color, line_dash, symbol', got '{fig.layout.legend.title.text}'"
    print("✓ test_color_symbol_linedash_line passed")


def test_facet():
    fig = px.scatter(df, x='x', y='y', color='color', facet_col='facet_col')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 6, f"Expected 6 traces (3 colors * 2 cols), got {len(traces)}"
    unique_names = list(dict.fromkeys(names))
    assert set(unique_names) == {'A', 'B', 'C'}, f"Facet should not affect trace names: {unique_names}"
    
    showlegends = [t.showlegend for t in traces]
    true_count = sum(1 for s in showlegends if s)
    false_count = sum(1 for s in showlegends if not s)
    assert true_count == 3 and false_count == 3, f"Should have 3 True and 3 False showlegend values: {showlegends}"
    print("✓ test_facet passed")


def test_animation_frame():
    fig = px.scatter(df, x='x', y='y', color='color', animation_frame='animation_frame')
    
    assert len(fig.frames) == 3, f"Expected 3 frames, got {len(fig.frames)}"
    
    for frame in fig.frames:
        traces = frame.data
        names = [t.name for t in traces]
        showlegends = [t.showlegend for t in traces]
        assert set(names) == {'A', 'B', 'C'}, f"Frame names should be A,B,C: {names}"
        assert all(showlegends), f"Each frame's traces should show legend: {showlegends}"
    
    print("✓ test_animation_frame passed")


def test_trendline_trace_scope():
    fig = px.scatter(df, x='x', y='y', color='color', trendline='ols', trendline_scope='trace')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 6, f"Expected 6 traces (3 data + 3 trendline), got {len(traces)}"
    
    data_names = names[::2]
    trend_names = names[1::2]
    assert set(data_names) == {'A', 'B', 'C'}, f"Data names: {data_names}"
    expected_trend = {f"{n} Trendline" for n in ['A', 'B', 'C']}
    assert set(trend_names) == expected_trend, f"Trend names: {trend_names}"
    
    legendgroups = [t.legendgroup for t in traces]
    for i in range(0, len(traces), 2):
        assert legendgroups[i] == legendgroups[i+1], f"Data and trendline should have same legendgroup: {legendgroups[i:i+2]}"
        assert legendgroups[i] == data_names[i//2], f"legendgroup should match data name: {legendgroups[i]}"
    
    print("✓ test_trendline_trace_scope passed")


def test_trendline_overall_scope():
    fig = px.scatter(df, x='x', y='y', color='color', trendline='ols', trendline_scope='overall')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 4, f"Expected 4 traces (3 data + 1 overall trendline), got {len(traces)}"
    assert names[-1] == 'Overall Trendline', f"Last trace should be 'Overall Trendline': {names}"
    
    trend_trace = traces[-1]
    assert trend_trace.legendgroup == 'Overall Trendline', f"Overall trendline legendgroup: {trend_trace.legendgroup}"
    assert trend_trace.showlegend == True, f"Overall trendline showlegend should be True: {trend_trace.showlegend}"
    
    print("✓ test_trendline_overall_scope passed")


def test_basic_trendline_no_color():
    fig = px.scatter(df, x='x', y='y', trendline='ols', trendline_scope='trace')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 2, f"Expected 2 traces, got {len(traces)}"
    assert names[0] == '', f"First trace name should be empty: '{names[0]}'"
    assert names[1] == 'Trendline', f"Second trace should be 'Trendline': '{names[1]}'"
    
    print("✓ test_basic_trendline_no_color passed")


def test_bar_legend():
    fig = px.bar(df, x='color', y='x', color='symbol', barmode='group')
    traces = fig.data
    names = [t.name for t in traces]
    
    assert len(traces) == 2, f"Expected 2 traces, got {len(traces)}"
    assert set(names) == {'X', 'Y'}, f"Expected X,Y, got {names}"
    for t in traces:
        assert t.offsetgroup == t.name, f"offsetgroup should match name: {t.offsetgroup}"
        assert bool(t.alignmentgroup) == True, f"alignmentgroup should be True: {t.alignmentgroup}"
    
    print("✓ test_bar_legend passed")


def test_no_legend_types():
    df_heatmap = pd.DataFrame({
        'x': [1, 2, 3, 1, 2, 3],
        'y': [1, 1, 1, 2, 2, 2],
        'z': [10, 20, 30, 40, 50, 60],
    })
    fig = px.density_heatmap(df_heatmap, x='x', y='y', z='z')
    traces = fig.data
    
    assert len(traces) == 1, f"Expected 1 trace, got {len(traces)}"
    assert getattr(traces[0], 'legendgroup', None) is None, f"Heatmap should not have legendgroup: {getattr(traces[0], 'legendgroup', None)}"
    assert getattr(traces[0], 'showlegend', None) is None, f"Heatmap should not have showlegend set: {getattr(traces[0], 'showlegend', None)}"
    
    print("✓ test_no_legend_types passed")


def test_parallel_coordinates():
    df_iris = px.data.iris()
    fig = px.parallel_coordinates(df_iris, color='species_id')
    traces = fig.data
    
    assert len(traces) == 1, f"Expected 1 trace, got {len(traces)}"
    assert getattr(traces[0], 'legendgroup', None) is None, f"Parcoords should not have legendgroup: {getattr(traces[0], 'legendgroup', None)}"
    
    print("✓ test_parallel_coordinates passed")


def test_pie_chart():
    df_pie = pd.DataFrame({
        'names': ['A', 'B', 'C', 'D'],
        'values': [10, 20, 30, 40],
    })
    fig = px.pie(df_pie, names='names', values='values')
    traces = fig.data
    
    assert len(traces) == 1, f"Expected 1 trace, got {len(traces)}"
    assert traces[0].legendgroup is None, f"Pie should not have legendgroup: {traces[0].legendgroup}"
    
    print("✓ test_pie_chart passed")


if __name__ == '__main__':
    test_basic_scatter()
    test_color_grouped()
    test_color_symbol_grouped()
    test_color_symbol_linedash_line()
    test_facet()
    test_animation_frame()
    test_trendline_trace_scope()
    test_trendline_overall_scope()
    test_basic_trendline_no_color()
    test_bar_legend()
    test_no_legend_types()
    test_parallel_coordinates()
    test_pie_chart()
    print("\n✅ All tests passed!")
