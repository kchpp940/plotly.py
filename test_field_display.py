import plotly.express as px
import pandas as pd
import numpy as np


def test_basic_column_names():
    df = pd.DataFrame({
        'sales': [100, 200, 150],
        'region': ['A', 'B', 'C']
    })
    fig = px.bar(
        df,
        x='region',
        y='sales',
        field_display={
            'sales': '销售额',
            'region': '地区'
        }
    )
    x_title = fig.layout.xaxis.title.text
    y_title = fig.layout.yaxis.title.text
    assert x_title == '地区', f"X轴标题应为'地区'，实际为'{x_title}'"
    assert y_title == '销售额', f"Y轴标题应为'销售额'，实际为'{y_title}'"
    print("✓ test_basic_column_names")
    return True


def test_semantic_roles():
    df = pd.DataFrame({
        'x_col': [1, 2, 3],
        'y_col': [4, 5, 6],
        'cat_col': ['a', 'b', 'c']
    })
    fig = px.scatter(
        df,
        x='x_col',
        y='y_col',
        color='cat_col',
        field_display={
            'x': '横轴',
            'y': '纵轴',
            'color': '类别'
        }
    )
    x_title = fig.layout.xaxis.title.text
    y_title = fig.layout.yaxis.title.text
    legend_title = fig.layout.legend.title.text
    assert x_title == '横轴', f"X轴标题应为'横轴'，实际为'{x_title}'"
    assert y_title == '纵轴', f"Y轴标题应为'纵轴'，实际为'{y_title}'"
    assert legend_title == '类别', f"图例标题应为'类别'，实际为'{legend_title}'"
    print("✓ test_semantic_roles")
    return True


def test_wide_form_flat():
    df = pd.DataFrame({
        'Jan': [100, 200],
        'Feb': [150, 250],
        'Mar': [120, 220]
    }, index=['Product A', 'Product B'])
    fig = px.bar(
        df,
        x=df.index,
        y=['Jan', 'Feb', 'Mar'],
        field_display={
            'value': '销售额',
            'variable': '月份',
            'x': '产品'
        },
        barmode='group'
    )
    y_title = fig.layout.yaxis.title.text
    legend_title = fig.layout.legend.title.text
    assert y_title == '销售额', f"Y轴标题应为'销售额'，实际为'{y_title}'"
    assert legend_title == '月份', f"图例标题应为'月份'，实际为'{legend_title}'"
    print("✓ test_wide_form_flat")
    return True


def test_wide_form_explicit_schema():
    df = pd.DataFrame({
        'Jan': [100, 200],
        'Feb': [150, 250],
    }, index=['Product A', 'Product B'])
    fig = px.bar(
        df,
        x=df.index,
        y=['Jan', 'Feb'],
        field_display=dict(
            by_role={'x': '产品'},
            by_internal={'value': '销售额', 'variable': '月份'},
        ),
        barmode='group'
    )
    y_title = fig.layout.yaxis.title.text
    legend_title = fig.layout.legend.title.text
    assert y_title == '销售额', f"Y轴标题应为'销售额'，实际为'{y_title}'"
    assert legend_title == '月份', f"图例标题应为'月份'，实际为'{legend_title}'"
    print("✓ test_wide_form_explicit_schema")
    return True


def test_explicit_schema_no_collision():
    df = pd.DataFrame({
        'col_x': [1, 2, 3],
        'col_y': [4, 5, 6],
        'cat': ['a', 'b', 'c']
    })
    fig = px.scatter(
        df,
        x='col_x',
        y='col_y',
        color='cat',
        field_display=dict(
            by_role={'x': 'X角色', 'color': '颜色角色'},
            by_column={'col_x': '宽度列', 'col_y': '高度列'},
        )
    )
    x_title = fig.layout.xaxis.title.text
    legend_title = fig.layout.legend.title.text
    assert x_title == 'X角色', f"X轴标题应为'X角色'，实际为'{x_title}'"
    assert legend_title == '颜色角色', f"图例标题应为'颜色角色'，实际为'{legend_title}'"
    print("✓ test_explicit_schema_no_collision")
    return True


def test_facet():
    df = px.data.tips()
    fig = px.scatter(
        df,
        x='total_bill',
        y='tip',
        facet_col='sex',
        facet_row='smoker',
        field_display={
            'facet_col': '性别',
            'facet_row': '是否吸烟',
            'x': '总账单',
            'y': '小费'
        }
    )
    x_title = fig.layout.xaxis.title.text
    y_title = fig.layout.yaxis.title.text
    assert x_title == '总账单', f"X轴标题应为'总账单'，实际为'{x_title}'"
    assert y_title == '小费', f"Y轴标题应为'小费'，实际为'{y_title}'"
    print("✓ test_facet")
    return True


def test_hide_field_in_hover():
    df = pd.DataFrame({
        'x': [1, 2, 3],
        'y': [4, 5, 6],
        'visible_col': ['a', 'b', 'c'],
        'hidden_col': [10, 20, 30]
    })
    fig = px.scatter(
        df,
        x='x',
        y='y',
        hover_data=['visible_col', 'hidden_col'],
        field_display={
            'hidden_col': False
        }
    )
    hovertemplate = fig.data[0].hovertemplate
    assert 'hidden_col' not in hovertemplate, f"hover 中不应包含 hidden_col"
    print("✓ test_hide_field_in_hover")
    return True


def test_labels_compatibility():
    df = pd.DataFrame({
        'x': [1, 2, 3],
        'y': [4, 5, 6]
    })
    fig1 = px.scatter(df, x='x', y='y', labels={'x': 'X-label', 'y': 'Y-label'})
    fig2 = px.scatter(df, x='x', y='y', field_display={'x': 'X-fd', 'y': 'Y-fd'})
    fig3 = px.scatter(df, x='x', y='y', labels={'x': 'X-label', 'y': 'Y-label'},
                      field_display={'x': 'X-fd-override'})
    assert fig1.layout.xaxis.title.text == 'X-label', "labels 应该生效"
    assert fig2.layout.xaxis.title.text == 'X-fd', "field_display 应该生效"
    assert fig3.layout.xaxis.title.text == 'X-fd-override', "field_display 应该覆盖 labels"
    assert fig3.layout.yaxis.title.text == 'Y-label', "Y 轴应该从 labels 继承"
    print("✓ test_labels_compatibility")
    return True


def test_line_chart():
    df = pd.DataFrame({
        'time': [1, 2, 3],
        'value': [10, 20, 15],
        'group': ['A', 'A', 'B']
    })
    fig = px.line(
        df,
        x='time',
        y='value',
        color='group',
        field_display={
            'x': '时间',
            'y': '数值',
            'color': '分组'
        }
    )
    assert fig.layout.xaxis.title.text == '时间'
    assert fig.layout.yaxis.title.text == '数值'
    assert fig.layout.legend.title.text == '分组'
    print("✓ test_line_chart")
    return True


def test_area_chart():
    df = pd.DataFrame({
        'x': [1, 2, 3],
        'y1': [10, 20, 15],
        'y2': [5, 15, 10]
    })
    fig = px.area(
        df,
        x='x',
        y=['y1', 'y2'],
        field_display={
            'x': '时间',
            'value': '数值',
            'variable': '系列'
        }
    )
    assert fig.layout.xaxis.title.text == '时间'
    assert fig.layout.yaxis.title.text == '数值'
    assert fig.layout.legend.title.text == '系列'
    print("✓ test_area_chart")
    return True


def test_bar_chart():
    df = pd.DataFrame({
        'cat': ['A', 'B', 'C'],
        'val': [10, 20, 30],
        'grp': ['X', 'X', 'Y']
    })
    fig = px.bar(
        df,
        x='cat',
        y='val',
        color='grp',
        field_display={
            'x': '类别',
            'y': '值',
            'color': '组别'
        }
    )
    assert fig.layout.xaxis.title.text == '类别'
    assert fig.layout.yaxis.title.text == '值'
    assert fig.layout.legend.title.text == '组别'
    print("✓ test_bar_chart")
    return True


def test_defaults():
    df = pd.DataFrame({
        'x': [1, 2, 3],
        'y': [4, 5, 6]
    })
    original = px.defaults.field_display
    try:
        px.defaults.field_display = {'x': '默认X', 'y': '默认Y'}
        fig = px.scatter(df, x='x', y='y')
        assert fig.layout.xaxis.title.text == '默认X'
        assert fig.layout.yaxis.title.text == '默认Y'
        print("✓ test_defaults")
        return True
    finally:
        px.defaults.field_display = original


def test_trace_name_from_context():
    df = pd.DataFrame({
        'x': [1, 2, 3, 1, 2, 3],
        'y': [4, 5, 6, 7, 8, 9],
        'cat': ['A', 'A', 'A', 'B', 'B', 'B']
    })
    fig = px.scatter(
        df,
        x='x',
        y='y',
        color='cat',
        field_display=dict(
            by_role={'color': '类别'},
        )
    )
    trace_names = [t.name for t in fig.data]
    assert len(trace_names) > 0, "应该有 trace"
    print("✓ test_trace_name_from_context")
    return True


def test_explicit_schema_by_column():
    df = pd.DataFrame({
        'revenue': [100, 200],
        'department': ['Sales', 'Eng']
    })
    fig = px.bar(
        df,
        x='department',
        y='revenue',
        field_display=dict(
            by_column={'revenue': '收入', 'department': '部门'}
        )
    )
    assert fig.layout.xaxis.title.text == '部门'
    assert fig.layout.yaxis.title.text == '收入'
    print("✓ test_explicit_schema_by_column")
    return True


def run_all_tests():
    tests = [
        test_basic_column_names,
        test_semantic_roles,
        test_wide_form_flat,
        test_wide_form_explicit_schema,
        test_explicit_schema_no_collision,
        test_facet,
        test_hide_field_in_hover,
        test_labels_compatibility,
        test_line_chart,
        test_area_chart,
        test_bar_chart,
        test_defaults,
        test_trace_name_from_context,
        test_explicit_schema_by_column,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n测试结果: {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
