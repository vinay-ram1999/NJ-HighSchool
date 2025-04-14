import matplotlib.pyplot as plt
import seaborn as sns
import polars as pl

from settings import nj_doe_data_dir

df = pl.read_csv(f"{nj_doe_data_dir}/fct_enrollments.csv")

attributes = [col for col in df.columns if col != "academic_year"]

df_unpivot = df.unpivot(
    index="academic_year", 
    on=attributes, 
    variable_name="variable", 
    value_name="value"
)

df_grouped = df_unpivot.with_columns(pl.col("value").is_null().alias("is_null"))\
    .group_by(["academic_year", "variable"])\
    .agg([
        pl.count("value").alias("total"),
        pl.sum("is_null").alias("missing")
    ])\
    .with_columns((((pl.col("total") - pl.col("missing")) / pl.col("total")) * 100).alias("fullness"))

heatmap_df = df_grouped.pivot(
    values="fullness",
    index="variable",
    on="academic_year"
)

heatmap_pd = heatmap_df.to_pandas()
heatmap_pd = heatmap_pd.set_index("variable")
heatmap_pd = heatmap_pd.reindex(attributes)

year_order = sorted(heatmap_pd.columns)
heatmap_pd = heatmap_pd[year_order]

plt.figure(figsize=(10, 8))
ax = sns.heatmap(heatmap_pd, annot=True, cmap="YlGnBu", fmt=".1f")
plt.title("Percentage Fullness Heatmap for 'fct_enrollments'")
plt.xlabel("Academic Year")
plt.ylabel("Attribute")

plt.tight_layout()
plt.savefig(f"{nj_doe_data_dir}/profile_heatmap.png", dpi=300, bbox_inches='tight')
plt.show()
