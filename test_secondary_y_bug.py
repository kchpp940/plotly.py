import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

def test_secondary_y_hline():
    """测试带 secondary_y 的子图中 add_hline 的 shape 和 annotation 轴引用是否一致"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 3, 2], name="primary"), secondary_y=False)
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[40, 30, 20], name="secondary"), secondary_y=True)

    print("=== 测试1: add_hline 带 secondary_y=True ===")
    fig.add_hline(y=30, row=1, col=1, secondary_y=True, 
                  annotation_text="test", annotation_position="top right")
    
    shape = fig.layout.shapes[-1]
    annotation = fig.layout.annotations[-1]
    
    print(f"Shape yref: {shape.yref}")
    print(f"Annotation yref: {annotation.yref}")
    print(f"Shape yref == Annotation yref: {shape.yref == annotation.yref}")
    
    if shape.yref != annotation.yref:
        print("BUG 复现: shape 和 annotation 的 yref 不一致!")
    else:
        print("OK: shape 和 annotation 的 yref 一致")
    
    return shape.yref == annotation.yref

def test_facet_secondary_y():
    """测试 facet 图中带 secondary_y 的情况"""
    df = px.data.tips()
    fig = px.scatter(df, x="total_bill", y="tip", facet_col="sex", 
                     facet_row="smoker")
    
    print("\n=== 测试2: facet 图 add_vline ===")
    fig.add_vline(x=30, row=2, col=2, annotation_text="test")
    
    shape = fig.layout.shapes[-1]
    annotation = fig.layout.annotations[-1]
    
    print(f"Shape xref: {shape.xref}, yref: {shape.yref}")
    print(f"Annotation xref: {annotation.xref}, yref: {annotation.yref}")
    print(f"Axis refs match: {shape.xref == annotation.xref and shape.yref == annotation.yref}")
    
    return shape.xref == annotation.xref and shape.yref == annotation.yref

def test_complex_subplots():
    """测试复杂子图布局"""
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"secondary_y": True}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": True}]],
    )
    
    for r in range(1, 3):
        for c in range(1, 3):
            fig.add_trace(go.Scatter(x=[1, 2, 3], y=[r*10 + c, r*10 + c + 1, r*10 + c + 2]), 
                         row=r, col=c, secondary_y=False)
            if (r, c) in [(1, 1), (2, 2)]:
                fig.add_trace(go.Scatter(x=[1, 2, 3], y=[r*100 + c, r*100 + c + 10, r*100 + c + 20]), 
                             row=r, col=c, secondary_y=True)
    
    print("\n=== 测试3: 复杂子图 add_hline 到 secondary_y ===")
    all_match = True
    
    # 测试 (1,1) secondary_y=True
    fig.add_hline(y=120, row=1, col=1, secondary_y=True, annotation_text="(1,1) sec")
    shape = fig.layout.shapes[-1]
    annotation = fig.layout.annotations[-1]
    match = shape.yref == annotation.yref
    all_match &= match
    print(f"(1,1) sec: Shape yref={shape.yref}, Annotation yref={annotation.yref}, match={match}")
    
    # 测试 (2,2) secondary_y=True  
    fig.add_hline(y=220, row=2, col=2, secondary_y=True, annotation_text="(2,2) sec")
    shape = fig.layout.shapes[-1]
    annotation = fig.layout.annotations[-1]
    match = shape.yref == annotation.yref
    all_match &= match
    print(f"(2,2) sec: Shape yref={shape.yref}, Annotation yref={annotation.yref}, match={match}")
    
    # 测试 (1,2) secondary_y=False
    fig.add_hline(y=15, row=1, col=2, secondary_y=False, annotation_text="(1,2) prim")
    shape = fig.layout.shapes[-1]
    annotation = fig.layout.annotations[-1]
    match = shape.yref == annotation.yref
    all_match &= match
    print(f"(1,2) prim: Shape yref={shape.yref}, Annotation yref={annotation.yref}, match={match}")
    
    return all_match

if __name__ == "__main__":
    result1 = test_secondary_y_hline()
    result2 = test_facet_secondary_y()
    result3 = test_complex_subplots()
    
    print("\n" + "="*50)
    print(f"测试结果: {'全部通过' if (result1 and result2 and result3) else '存在BUG'}")
    print(f"  测试1 (secondary_y hline): {'通过' if result1 else '失败'}")
    print(f"  测试2 (facet vline): {'通过' if result2 else '失败'}")
    print(f"  测试3 (复杂子图): {'通过' if result3 else '失败'}")
