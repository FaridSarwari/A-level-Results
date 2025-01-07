from dash import dcc, html, dash_table, Dash
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np

# Read the data
df_table = pd.read_csv("https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/45add44a-3cfd-4616-b108-e1f94792ef16/csv")

# Convert the time_period column to the desired format
df_table['time_period'] = df_table['time_period'].astype(str)
df_table['formatted_time_period'] = df_table['time_period'].apply(lambda x: f"{x[:4]}/{x[4:]}")
df_table['start_year'] = df_table['time_period'].str[:4].astype(int)

# Calculate absolute columns
percentage_columns = [
    'perc_astar_grade_achieved',
    'perc_astar_a_grade_achieved',
    'perc_astar_b_grade_achieved',
    'perc_astar_c_grade_achieved',
    'perc_astar_d_grade_achieved',
    'perc_astar_e_grade_achieved'
]
for col in percentage_columns:
    df_table[col] = pd.to_numeric(df_table[col], errors='coerce')
    abs_col_name = f"abs_{col.split('_')[1]}_{col.split('_')[2]}_grade_achieved"
    df_table[abs_col_name] = (df_table[col] / 100) * df_table['entry_count']

# Create Dash app
app = Dash(__name__, title="A-level Results Dashboard")

server = app.server

# Layout
app.layout = html.Div([
    html.H1("A-level Results Dashboard"),

    # Filters
    html.Div([
        html.Label("Select Start Date:"),
        dcc.Dropdown(
            id='start-date-dropdown',
            options=[{'label': year, 'value': year} for year in sorted(df_table['start_year'].unique())],
            value=min(df_table['start_year']),
            clearable=False
        ),

        html.Label("Select End Date:"),
        dcc.Dropdown(
            id='end-date-dropdown',
            options=[{'label': year, 'value': year} for year in sorted(df_table['start_year'].unique())],
            value=max(df_table['start_year']),
            clearable=False
        ),

        html.Label("Select Indicator Type:"),
        dcc.RadioItems(
            id='indicator-type',
            options=[
                {'label': 'Percentage', 'value': 'percentage'},
                {'label': 'Absolute', 'value': 'absolute'}
            ],
            value='percentage',
            inline=True
        ),

        html.Label("Select Gender/Characteristic:"),
        dcc.Dropdown(
            id='characteristic-filter',
            options=[{'label': c, 'value': c} for c in df_table['characteristic_value'].unique()],
            value='All Students',  # Default to "All Students"
            clearable=False
        ),

        html.Label("Select Subjects:"),
        dcc.Dropdown(
            id='subject-filter',
            options=[{'label': s, 'value': s} for s in df_table['subject_name'].unique()],
            value=[df_table['subject_name'].unique()[0]],  # Default to the first subject
            multi=True,  # Enable multi-selection
            clearable=False
        ),

    ], style={'padding': '20px', 'width': '50%', 'display': 'inline-block'}),

    # Table
    html.Div([
        dash_table.DataTable(
            id='filtered-table',
            columns=[],
            style_table={'overflowX': 'auto'}
        )
    ]),

    # Line Chart
    html.Div([
        dcc.Graph(
            id='entries-line-chart',
            style={'height': '400px'}
        )
    ])
])

# Callbacks
@app.callback(
    [Output('filtered-table', 'data'),
     Output('filtered-table', 'columns')],
    [
        Input('start-date-dropdown', 'value'),
        Input('end-date-dropdown', 'value'),
        Input('indicator-type', 'value'),
        Input('characteristic-filter', 'value'),
        Input('subject-filter', 'value')
    ]
)
def update_table(start_date, end_date, indicator_type, selected_characteristic, selected_subject):
    # Filter the data based on selected date range, characteristic, and subject
    filtered_df = df_table[
        (df_table['start_year'] >= int(start_date)) &
        (df_table['start_year'] <= int(end_date)) &
        (df_table['characteristic_value'] == selected_characteristic) &
        (df_table['subject_name'].isin(selected_subject))
    ]

    # Include Entry Count indicator
    base_columns = ['entry_count']
    if indicator_type == 'percentage':
        selected_columns = percentage_columns
    else:
        selected_columns = [f"abs_{col.split('_')[1]}_{col.split('_')[2]}_grade_achieved" for col in percentage_columns]

    # Combine entry count with other selected indicators
    all_columns = base_columns + selected_columns

    # Pivot table for display format
    table_data = filtered_df[['start_year'] + all_columns].groupby('start_year').mean().T.reset_index()
    table_data.rename(columns={'index': 'Indicator'}, inplace=True)

    # Ensure all column names are strings
    table_data.columns = table_data.columns.map(str)

    # Format columns for Dash
    table_columns = [{'name': col, 'id': col} for col in table_data.columns]

    return table_data.to_dict('records'), table_columns


@app.callback(
    Output('entries-line-chart', 'figure'),
    [
        Input('start-date-dropdown', 'value'),
        Input('end-date-dropdown', 'value'),
        Input('subject-filter', 'value'),
        Input('characteristic-filter', 'value')
    ]
)
def update_line_chart(start_date, end_date, selected_subjects, selected_characteristic):
    # Ensure selected_subjects is a list to handle single or multiple selections
    if not isinstance(selected_subjects, list):
        selected_subjects = [selected_subjects]

    # Filter data for the selected date range, subjects, and characteristic
    filtered_df = df_table[
        (df_table['start_year'] >= int(start_date)) &
        (df_table['start_year'] <= int(end_date)) &
        (df_table['subject_name'].isin(selected_subjects)) &
        (df_table['characteristic_value'] == selected_characteristic)
    ]

    # Create the line chart
    data_traces = []
    for subject in selected_subjects:
        subject_df = filtered_df[filtered_df['subject_name'] == subject]
        aggregated_df = subject_df.groupby('start_year', as_index=False)['entry_count'].sum()

        trace = {
            'x': aggregated_df['start_year'],
            'y': aggregated_df['entry_count'],
            'type': 'line',
            'name': f'{subject} ({selected_characteristic})'
        }
        data_traces.append(trace)

    line_chart_figure = {
        'data': data_traces,
        'layout': {
            'title': f'Entries Count Over Time for Selected Subjects ({selected_characteristic})',
            'xaxis': {'title': 'Year'},
            'yaxis': {'title': 'Entry Count'},
            'template': 'plotly_white'
        }
    }
    return line_chart_figure

#Run app---------------------------------------------

if __name__ == '__main__':
    app.run_server(
        port=8000,       # You can change this port number
        debug=True       # Set to False for production
    )
