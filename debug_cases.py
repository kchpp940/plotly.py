import pandas as pd
from plotly.graph_objects import Scatter
from plotly.express._core import build_dataframe

# Case 1: columns named after special strings
df = pd.DataFrame(dict(index=[1, 2], value=[3, 4], variable=[5, 6]), index=[7, 8])
args = dict(x=None, y=None, color=None, data_frame=df)
args_out = build_dataframe(args, Scatter)
df_out = args_out.pop('data_frame')
print('=== Case 1: special string columns ===')
print('args_out keys:', sorted(args_out.keys()))
print('x:', args_out.get('x'))
print('y:', args_out.get('y'))
print('color:', args_out.get('color'))
print('labels:', args_out.get('labels'))
print('_col_map:', args_out.get('_col_map'))
print('orientation:', args_out.get('orientation'))
print()

# Case 2: named index/columns (a, b)
df = pd.DataFrame(dict(a=[1, 2], b=[3, 4]), index=[7, 8])
df.index.name = 'a'
df.columns.name = 'b'
args = dict(x=None, y=None, color=None, data_frame=df)
args_out = build_dataframe(args, Scatter)
df_out = args_out.pop('data_frame')
print('=== Case 2: named index/columns (a, b) ===')
print('args_out keys:', sorted(args_out.keys()))
print('x:', args_out.get('x'))
print('y:', args_out.get('y'))
print('color:', args_out.get('color'))
print('labels:', args_out.get('labels'))
print('_col_map:', args_out.get('_col_map'))
print('orientation:', args_out.get('orientation'))
print()

# Case 3: everything called 'value'
df = pd.DataFrame(dict(b=[1, 2], value=[3, 4]), index=[7, 8])
df.index.name = 'value'
df.columns.name = 'value'
args = dict(x=None, y=None, color=None, data_frame=df)
args_out = build_dataframe(args, Scatter)
df_out = args_out.pop('data_frame')
print('=== Case 3: everything called value ===')
print('args_out keys:', sorted(args_out.keys()))
print('x:', args_out.get('x'))
print('y:', args_out.get('y'))
print('color:', args_out.get('color'))
print('labels:', args_out.get('labels'))
print('_col_map:', args_out.get('_col_map'))
print('orientation:', args_out.get('orientation'))
