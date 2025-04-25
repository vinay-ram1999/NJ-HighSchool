from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import dash

from settings import nj_doe_data_dir

dim_schools = pd.read_csv(f"{nj_doe_data_dir}/dim_schools.csv")
fct_enrollments = pd.read_csv(f"{nj_doe_data_dir}/fct_enrollments.csv")

df = pd.merge(dim_schools, fct_enrollments, on='county_district_school_code', how='inner').dropna()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.ZEPHYR])

app.layout = html.Div([
    html.H1("Dashboard"),
    html.Div([
        html.Label("Select X-axis:"),
        dcc.Dropdown(
            id='xaxis-dropdown',
            options=[{'label': col, 'value': col} for col in df.columns],
            value=df.columns[0]
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Select Y-axis:"),
        dcc.Dropdown(
            id='yaxis-dropdown',
            options=[{'label': col, 'value': col} for col in df.columns],
            value=df.columns[1] if len(df.columns) > 1 else df.columns[0]
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),

    dcc.Graph(id='scatter-plot'),

])

@app.callback(
    Output('scatter-plot', 'figure'),
    [Input('xaxis-dropdown', 'value'), Input('yaxis-dropdown', 'value')]
)
def register_callbacks(x_col, y_col):
    fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
    return fig

if __name__ == '__main__':
    app.run(debug=True)
