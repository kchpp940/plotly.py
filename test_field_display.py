import plotly.express as px
import pandas as pd
import numpy as np


def test_basic_column_names():
    """测试：按列名配置显示名"""
    print("=" * 60)
    print("测试1：按列名配置显示名")
    print("=" * 60)
    
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
    
    print(f"X轴标题: {x_title}")
    print(f"Y轴标题: {y_title}")
    
    assert x_title == '地区', f"X轴标题应为'地区'，实际为'{x_title}'"
    assert y_title == '销售额', f"Y轴标题应为'销售额'，实际为'{y_title}'"
    
    print("✓ 测试1通过")
    return True


def test_semantic_roles():
    """测试：按语义角色配置显示名"""
    print("\n" + "=" * 60)
    print("测试2：按语义角色配置显示名")
    print("=" * 60)
    
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
    
    print(f"X轴标题: {x_title}")
    print(f"Y轴标题: {y_title}")
    print(f"图例标题: {legend_title}")
    
    assert x_title == '横轴', f"X轴标题应为'横轴'，实际为'{x_title}'"
    assert y_title == '纵轴', f"Y轴标题应为'纵轴'，实际为'{y_title}'"
    assert legend_title == '类别', f"图例标题应为'类别'，实际为'{legend_title}'"
    
    print("✓ 测试2通过")
    return True


def test_wide_form():
    """测试：wide-form 数据场景"""
    print("\n" + "=" * 60)
    print("测试3：wide-form 数据场景")
    print("=" * 60)
    
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
    
    x_title = fig.layout.xaxis.title.text
    y_title = fig.layout.yaxis.title.text
    legend_title = fig.layout.legend.title.text
    
    print(f"X轴标题: {x_title}")
    print(f"Y轴标题: {y_title}")
    print(f"图例标题: {legend_title}")
    
    assert y_title == '销售额', f"Y轴标题应为'销售额'，实际为'{y_title}'"
    assert legend_title == '月份', f"图例标题应为'月份'，实际为'{legend_title}'"
    
    print("✓ 测试3通过")
    return True


def test_facet():
    """测试：facet 场景"""
    print("\n" + "=" * 60)
    print("测试4：facet 场景")
    print("=" * 60)
    
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
    
    print(f"X轴标题: {x_title}")
    print(f"Y轴标题: {y_title}")
    
    assert x_title == '总账单', f"X轴标题应为'总账单'，实际为'{x_title}'"
    assert y_title == '小费', f"Y轴标题应为'小费'，实际为'{y_title}'"
    
    print("✓ 测试4通过")
    return True


def test_hide_field_in_hover():
    """测试：隐藏 hover 中的字段"""
    print("\n" + "=" * 60)
    print("测试5：隐藏 hover 中的字段")
    print("=" * 60)
    
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
    print(f"Hover 模板: {hovertemplate}")
    
    assert 'hidden_col' not in hovertemplate, f"hover 中不应包含 hidden_col"
    
    print("✓ 测试5通过")
    return True


def test_labels_compatibility():
    """测试：与 labels 参数的兼容性"""
    print("\n" + "=" * 60)
    print("测试6：与 labels 参数的兼容性")
    print("=" * 60)
    
    df = pd.DataFrame({
        'x': [1, 2, 3],
        'y': [4, 5, 6]
    })
    
    # 只有 labels
    fig1 = px.scatter(df, x='x', y='y', labels={'x': 'X-label', 'y': 'Y-label'})
    
    # 只有 field_display
    fig2 = px.scatter(df, x='x', y='y', field_display={'x': 'X-fd', 'y': 'Y-fd'})
    
    # 两者都有，field_display 优先级更高
    fig3 = px.scatter(df, x='x', y='y', labels={'x': 'X-label', 'y': 'Y-label'},
                      field_display={'x': 'X-fd-override'})
    
    print(f"labels only - X: {fig1.layout.xaxis.title.text}")
    print(f"field_display only - X: {fig2.layout.xaxis.title.text}")
    print(f"both - X: {fig3.layout.xaxis.title.text}")
    print(f"both - Y (from labels): {fig3.layout.yaxis.title.text}")
    
    assert fig1.layout.xaxis.title.text == 'X-label', "labels 应该生效"
    assert fig2.layout.xaxis.title.text == 'X-fd', "field_display 应该生效"
    assert fig3.layout.xaxis.title.text == 'X-fd-override', "field_display 应该覆盖 labels"
    assert fig3.layout.yaxis.title.text == 'Y-label', "Y 轴应该从 labels 继承"
    
    print("✓ 测试6通过")
    return True


def test_line_chart():
    """测试：px.line 的行为一致性"""
    print("\n" + "=" * 60)
    print("测试7：px.line 的行为一致性")
    print("=" * 60)
    
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
    
    x_title = fig.layout.xaxis.title.text
    y_title = fig.layout.yaxis.title.text
    legend_title = fig.layout.legend.title.text
    
    print(f"X轴标题: {x_title}")
    print(f"Y轴标题: {y_title}")
    print(f"图例标题: {legend_title}")
    
    assert x_title == '时间', f"X轴标题应为'时间'，实际为'{x_title}'"
    assert y_title == '数值', f"Y轴标题应为'数值'，实际为'{y_title}'"
    assert legend_title == '分组', f"图例标题应为'分组'，实际为'{legend_title}'"
    
    print("✓ 测试7通过")
    return True


def test_area_chart():
    """测试：px.area 的行为一致性"""
    print("\n" + "=" * 60)
    print("测试8：px.area 的行为一致性")
    print("=" * 60)
    
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
    
    x_title = fig.layout.xaxis.title.text
    y_title = fig.layout.yaxis.title.text
    legend_title = fig.layout.legend.title.text
    
    print(f"X轴标题: {x_title}")
    print(f"Y轴标题: {y_title}")
    print(f"图例标题: {legend_title}")
    
    assert x_title == '时间', f"X轴标题应为'时间'，实际为'{x_title}'"
    assert y_title == '数值', f"Y轴标题应为'数值'，实际为'{y_title}'"
    assert legend_title == '系列', f"图例标题应为'系列'，实际为'{legend_title}'"
    
    print("✓ 测试8通过")
    return True


def test_defaults():
    """测试：px.defaults.field_display"""
    print("\n" + "=" * 60)
    print("测试9：px.defaults.field_display")
    print("=" * 60)
    
    df = pd.DataFrame({
        'x': [1, 2, 3],
        'y': [4, 5, 6]
    })
    
    # 保存原始默认值
    original_defaults = px.defaults.field_display
    
    try:
        px.defaults.field_display = {'x': '默认X', 'y': '默认Y'}
        
        fig = px.scatter(df, x='x', y='y')
        
        x_title = fig.layout.xaxis.title.text
        y_title = fig.layout.yaxis.title.text
        
        print(f"X轴标题: {x_title}")
        print(f"Y轴标题: {y_title}")
        
        assert x_title == '默认X', f"X轴标题应为'默认X'，实际为'{x_title}'"
        assert y_title == '默认Y', f"Y轴标题应为'默认Y'，实际为'{y_title}'"
        
        print("✓ 测试9通过")
        return True
    finally:
        px.defaults.field_display = original_defaults


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始运行 field_display 功能测试")
    print("=" * 60)
    
    tests = [
        test_basic_column_names,
        test_semantic_roles,
        test_wide_form,
        test_facet,
        test_hide_field_in_hover,
        test_labels_compatibility,
        test_line_chart,
        test_area_chart,
        test_defaults,
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
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
