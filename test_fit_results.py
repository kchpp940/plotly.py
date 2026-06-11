import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    "x": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
    "y": [2, 4, 5, 4, 5, 1, 2, 3, 4, 5],
    "group": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"],
})

print("Testing OLS fit_results structure...")
print()

fig = px.scatter(
    df, x="x", y="y", color="group",
    trendline="ols",
)

# Get trendline results
trendline_results = px.get_trendline_results(fig)
print(f"Trendline results shape: {trendline_results.shape}")
print(f"Columns: {trendline_results.columns.tolist()}")
print()

for idx, row in trendline_results.iterrows():
    group = row["group"] if "group" in trendline_results.columns else f"group_{idx}"
    fit = row["px_fit_results"]
    print(f"Group {group}:")
    if fit is not None:
        print(f"  Type: {type(fit)}")
        print(f"  params: {fit.params}")
        print(f"  params[0] (intercept): {fit.params[0] if len(fit.params) > 0 else 'N/A'}")
        print(f"  params[1] (slope): {fit.params[1] if len(fit.params) > 1 else 'N/A'}")
        print(f"  rsquared: {fit.rsquared}")
        print(f"  pvalues: {fit.pvalues}")
        print(f"  tvalues: {fit.tvalues}")
        print(f"  bse: {fit.bse}")  # standard errors
    else:
        print("  fit_results is None")
    print()

print("Testing with LOWESS...")
fig2 = px.scatter(df, x="x", y="y", color="group", trendline="lowess")
trendline_results2 = px.get_trendline_results(fig2)
for idx, row in trendline_results2.iterrows():
    group = row["group"] if "group" in trendline_results2.columns else f"group_{idx}"
    fit = row["px_fit_results"]
    print(f"Group {group}: fit_results = {fit}")
