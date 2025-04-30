from dash import dcc, html, Input, Output, State #, callback_context, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import dash

from settings import nj_doe_data_dir, gs_data_dir
from io import StringIO
import logging
import os

# Define constants for data sources
NJ_DOE_DATA = 'NJ DOE Data'
GS_MERGED_DATA = 'Great Schools Fuzzy Merged Data' # Match label used in dropdown

# Define columns (adjust if needed based on actual CSV contents)
GRADE_COLS = ['grade06', 'grade07', 'grade08', 'grade09', 'grade10', 'grade11', 'grade12']
DEMOGRAPHIC_COLS = ['american_indian_or_alaska_native', 'asian', 'black_or_african_american', 'hispanic', 'native_hawaiian_or_pacific_islander', 'two_or_more_races', 'white']
RATING_COLS = ['rating', 'rating_band'] # Columns specific to GS data

# --- Helper Functions ---
def get_unique_sorted(series):
    """Gets unique sorted values from a pandas Series, handling potential NaNs."""
    if series.empty or series.isnull().all(): # Check if series is empty or all NaN
        return []
    # Ensure string conversion for reliable sorting if mixed types
    return sorted([item for item in series.astype(str).unique() if pd.notna(item)])

def create_empty_figure(message="No data available"):
    """Creates a blank Plotly figure with a message."""
    fig = go.Figure()
    fig.update_layout(
        xaxis={'visible': False},
        yaxis={'visible': False},
        annotations=[{
            'text': message,
            'xref': 'paper', 'yref': 'paper',
            'showarrow': False, 'font': {'size': 14}
        }],
        margin=dict(l=20, r=20, t=40, b=20) # Consistent margins
    )
    return fig

# --- Initialize Dash App ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# --- App Layout ---
app.layout = html.Div(className='container-fluid p-4', children=[
    html.H1("NJ School Dashboard", className='mb-4 text-center'), # Generic title

    # --- Data Store Components ---
    dcc.Store(id='store-merged-data'),        # Holds merged enrollment + dim data (for year-specific plots)
    dcc.Store(id='store-merged-lang-data'),   # Holds merged enrollment + lang + dim data (for year-specific plots)
    dcc.Store(id='store-gs-dim-data'),        # Holds UNMERGED GS dimension data (for rating plots)
    dcc.Store(id='store-data-source-info'),   # Store info about the loaded source

    # --- Main Control Row (Applies to most plots) ---
    html.Div(className='row mb-4 p-3 bg-light rounded border align-items-end', children=[
        # Data Source Selector
        html.Div(className='col-md-4 mb-2', children=[ # Wider column
            html.Label("Select Data Source:", className='form-label fw-bold'),
            dcc.Dropdown(
                id='data-source-selector',
                options=[
                    {'label': 'NJ DOE Enrollment Data', 'value': NJ_DOE_DATA},
                    {'label': 'Great Schools Fuzzy Merged Data', 'value': GS_MERGED_DATA},
                ],
                value=NJ_DOE_DATA, # Default data source
                clearable=False,
                className='form-select-sm'
            )
        ]),
        # County Filter
        html.Div(className='col-md-2 mb-2', children=[
            html.Label("County:", className='form-label'),
            dcc.Dropdown(id='county-dropdown', clearable=False, className='form-select-sm')
        ]),
        # District Filter
        html.Div(className='col-md-3 mb-2', children=[
            html.Label("District:", className='form-label'),
            dcc.Dropdown(id='district-dropdown', clearable=False, className='form-select-sm')
        ]),
        # School Filter
        html.Div(className='col-md-3 mb-2', children=[ # Wider column
            html.Label("School:", className='form-label'),
            dcc.Dropdown(id='school-dropdown', clearable=False, className='form-select-sm')
        ]),
    ]),

    # --- Rating Plots Row (Conditionally Shown, uses current GS data) ---
    html.Div(id='rating-plots-row', className='row mb-4', style={'display': 'none'}, children=[ # Initially hidden
        html.Div(className='col-lg-6 mb-3', children=[
             dbc.Card(className='h-100', children=[
                 dbc.CardHeader('Current School Rating Distribution (GS)'), # Title updated
                 dbc.CardBody(dcc.Graph(id='rating-graph', className='h-100'))
             ])
        ]),
        html.Div(className='col-lg-6 mb-3', children=[
             dbc.Card(className='h-100', children=[
                 dbc.CardHeader('Current Schools by Rating Band (GS)'), # Title updated
                 dbc.CardBody(dcc.Graph(id='rating-band-graph', className='h-100'))
             ])
        ]),
    ]),

    # --- Separator and Academic Year Filter Row ---
    html.Hr(id='academic-separator', style={'display': 'block'}), # Always show separator
    html.H4("Academic Year Specific Data", id='academic-title', className='mb-3 text-center'),
    html.Div(className='row mb-4 p-3 bg-light rounded border align-items-end justify-content-center', children=[ # Centered row
        # Academic Year Filter (Moved Here)
        html.Div(className='col-md-4 mb-2', children=[ # Wider column for centering
            html.Label("Select Academic Year:", className='form-label'),
            dcc.Dropdown(id='year-dropdown', clearable=False, className='form-select-sm')
        ]),
    ]),

    # --- Academic Year Visualization Rows ---
    # Row 1: Enrollment Trend & Demographics
    html.Div(className='row mb-4', children=[
        html.Div(className='col-lg-6 mb-3', children=[
             dbc.Card(className='h-100', children=[
                 dbc.CardHeader('Total Enrollment Trend'),
                 dbc.CardBody(dcc.Graph(id='enrollment-trend-graph', className='h-100'))
             ])
        ]),
        html.Div(className='col-lg-6 mb-3', children=[
             dbc.Card(className='h-100', children=[
                 dbc.CardHeader('Demographic Distribution (Race/Ethnicity)'),
                 dbc.CardBody(dcc.Graph(id='demographic-dist-graph', className='h-100'))
             ])
        ]),
    ]),

    # Row 2: Grade Level & Home Language
    html.Div(className='row mb-4', children=[
        html.Div(className='col-lg-6 mb-3', children=[
             dbc.Card(className='h-100', children=[
                 dbc.CardHeader('Enrollment by Grade Level'),
                 dbc.CardBody(dcc.Graph(id='grade-dist-graph', className='h-100'))
             ])
        ]),
        html.Div(className='col-lg-6 mb-3', children=[
             dbc.Card(className='h-100', children=[
                 dbc.CardHeader('Top Home Languages'),
                 dbc.CardBody(dcc.Graph(id='language-dist-graph', className='h-100'))
             ])
        ]),
    ]),
])

# --- Callbacks ---
# Callback 1: Load Data and Update Filters based on Data Source Selection
@app.callback(
    Output('store-merged-data', 'data'),
    Output('store-merged-lang-data', 'data'),
    Output('store-gs-dim-data', 'data'), # Output for GS dim data
    Output('store-data-source-info', 'data'),
    Output('year-dropdown', 'options'),   # Year options still needed
    Output('year-dropdown', 'value'),     # Year value still needed
    Output('county-dropdown', 'options'),
    Output('county-dropdown', 'value'),
    Output('district-dropdown', 'options'),
    Output('district-dropdown', 'value'),
    Output('school-dropdown', 'options'),
    Output('school-dropdown', 'value'),
    Input('data-source-selector', 'value')
)
def load_data_and_update_filters(selected_data_source):
    """Loads data based on selection, preprocesses, stores it, and updates filter options."""
    logging.info(f"Data source selected: {selected_data_source}. Loading data...")
    gs_dim_data_json = None # Initialize GS dim store to None
    dim_schools_for_merge = None # Initialize df used for merging academic data

    try:
        # --- Load Dimension Data ---
        if selected_data_source == NJ_DOE_DATA:
            dim_schools_path = os.path.join(nj_doe_data_dir, "dim_schools.csv")
            dim_schools = pd.read_csv(dim_schools_path, dtype={
                "county_district_school_code": str, "zipcode": str, "zipcode_extn": str
            })
            # Ensure required columns exist for merging later
            required_cols_nj = ['county_name', 'district_name', 'school_name', 'county_district_school_code']
            if not all(col in dim_schools.columns for col in required_cols_nj):
                 raise ValueError("NJ DOE dim_schools missing required county/district/school name/code columns.")
            dim_schools_for_merge = dim_schools[required_cols_nj].copy() # Use only needed cols for merge
            source_info = {'name': NJ_DOE_DATA, 'has_ratings': False}
            logging.info(f"Loaded {NJ_DOE_DATA} school dimensions.")

        elif selected_data_source == GS_MERGED_DATA:
            dim_schools_path = os.path.join(gs_data_dir, "fuzzy_merged_dim_schools.csv")
            dim_schools = pd.read_csv(dim_schools_path, dtype={
                "county_district_school_code": str, "rating": float, "rating_band": str # Load rating_band as string
            })
            relevant_gs_cols = [
                'county_name', 'district_name', 'school_name',
                'county_district_school_code', 'rating', 'rating_band'
            ]
            missing_cols = [col for col in relevant_gs_cols if col not in dim_schools.columns]
            if missing_cols:
                 raise ValueError(f"Missing columns in GS data: {missing_cols}")

            # Keep a copy of the relevant GS dimension data *before* merging for rating plots
            gs_dim_data_for_store = dim_schools[relevant_gs_cols].copy()
            # Convert to string (handles potential non-string types), strip whitespace, convert to Title Case
            gs_dim_data_for_store['rating_band'] = gs_dim_data_for_store['rating_band'].astype(str).str.strip().str.title()
            # Replace empty strings or specific null-like strings with 'Unknown' AFTER standardization
            gs_dim_data_for_store['rating_band'] = gs_dim_data_for_store['rating_band'].replace(['', 'Nan', 'None', 'Null'], 'Unknown')
            # Fill any remaining actual NaN values (if astype(str) didn't catch them)
            gs_dim_data_for_store['rating_band'] = gs_dim_data_for_store['rating_band'].fillna('Unknown')
            # Remove duplicates based on school code if necessary (assuming one current rating per school)
            gs_dim_data_for_store = gs_dim_data_for_store.drop_duplicates(subset=['county_district_school_code'], keep='first')
            gs_dim_data_json = gs_dim_data_for_store.to_json(date_format='iso', orient='split')

            # Prepare the dimension data needed for merging with academic facts
            dim_schools_for_merge = dim_schools[['county_district_school_code', 'county_name', 'district_name', 'school_name']].copy()
            source_info = {'name': GS_MERGED_DATA, 'has_ratings': True}
            logging.info(f"Loaded {GS_MERGED_DATA} school dimensions and prepared for rating plots.")
        else:
            raise ValueError(f"Unknown data source: {selected_data_source}")

        # --- Load Fact Data (Common to both sources) ---
        fct_enrollments_path = os.path.join(nj_doe_data_dir, "fct_enrollments.csv")
        fct_homelang_path = os.path.join(nj_doe_data_dir, "fct_homelang_enrollments.csv")

        fct_enrollments = pd.read_csv(fct_enrollments_path, dtype={
            "county_district_school_code": str, "academic_year": str
        })
        fct_homelang_enrollments = pd.read_csv(fct_homelang_path, dtype={
            "county_district_school_code": str, "academic_year": str
        })
        logging.info("Loaded fact tables (Enrollments, Home Language).")

        # --- Preprocess Fact Data ---
        fct_enrollments['total_enrollment'] = fct_enrollments[GRADE_COLS].sum(axis=1, skipna=True)

        # --- Merge Data for Academic Year Plots ---
        # Use the prepared dim_schools_for_merge DataFrame
        df_merged = pd.merge(
            fct_enrollments,
            dim_schools_for_merge, # Use the prepared df
            on='county_district_school_code',
            how='inner' # Keep only schools present in both datasets for academic plots
        )
        logging.info(f"Merged enrollments with {selected_data_source} dimensions for academic plots.")

        # Sort academic years
        df_merged['academic_year'] = df_merged['academic_year'].astype(str)
        unique_years = sorted(df_merged['academic_year'].unique())
        df_merged['academic_year'] = pd.Categorical(df_merged['academic_year'], ordered=True, categories=unique_years)

        # Preprocess and Merge Language Data
        fct_homelang_merged = pd.merge(
            fct_homelang_enrollments,
            fct_enrollments[['county_district_school_code', 'academic_year', 'total_enrollment']],
            on=['county_district_school_code', 'academic_year'],
            how='left'
        )
        fct_homelang_merged['student_count'] = (fct_homelang_merged['pct_of_students'] / 100 * fct_homelang_merged['total_enrollment']).round().fillna(0).astype(int)

        # Merge language counts into the main academic merged dataframe
        df_merged_lang = pd.merge(
            df_merged,
            fct_homelang_merged[['county_district_school_code', 'academic_year', 'home_language', 'pct_of_students', 'student_count']],
            on=['county_district_school_code', 'academic_year'],
            how='left'
        )
        df_merged_lang['home_language'] = df_merged_lang['home_language'].fillna('Unknown/Not Reported')
        df_merged_lang['pct_of_students'] = df_merged_lang['pct_of_students'].fillna(0)
        df_merged_lang['student_count'] = df_merged_lang['student_count'].fillna(0)
        logging.info("Merged home language data for academic plots.")

        # --- Prepare Filter Options ---
        # Year options based on the merged academic data
        year_options = [{'label': year, 'value': year} for year in unique_years]
        latest_year = unique_years[-1] if unique_years else None

        # County/District/School options based on the chosen dimension data (use dim_schools_for_merge as it's common)
        county_options = [{'label': 'All Counties', 'value': 'ALL'}] + [{'label': c, 'value': c} for c in get_unique_sorted(dim_schools_for_merge['county_name'])]
        district_options = [{'label': 'All Districts', 'value': 'ALL'}]
        school_options = [{'label': 'All Schools', 'value': 'ALL'}]

        # Reset filters to 'ALL' when data source changes
        county_value = 'ALL'
        district_value = 'ALL'
        school_value = 'ALL'

        logging.info("Data loaded and processed successfully. Updating filters and stores.")

        # Convert DataFrames to JSON for Storage
        merged_data_json = df_merged.to_json(date_format='iso', orient='split')
        merged_lang_data_json = df_merged_lang.to_json(date_format='iso', orient='split')
        # gs_dim_data_json was prepared earlier if needed
        return (
            merged_data_json, merged_lang_data_json, gs_dim_data_json, source_info,
            year_options, latest_year,
            county_options, county_value,
            district_options, district_value,
            school_options, school_value
        )
    
    except FileNotFoundError as e:
        logging.error(f"Error loading file: {e}. Check paths in settings.py.")
        return None, None, None, {'name': 'Error', 'has_ratings': False}, [], None, [], 'ALL', [], 'ALL', [], 'ALL'
    
    except Exception as e:
        logging.error(f"An error occurred during data loading/processing: {e}", exc_info=True)
        return None, None, None, {'name': 'Error', 'has_ratings': False}, [], None, [], 'ALL', [], 'ALL', [], 'ALL'

# Callback 2: Update Dependent Filters (District & School) based on County/District Selection
@app.callback(
    Output('district-dropdown', 'options', allow_duplicate=True),
    Output('district-dropdown', 'value', allow_duplicate=True),
    Input('county-dropdown', 'value'),
    # Use GS dim data if available (more complete list), else use merged data
    State('store-gs-dim-data', 'data'),
    State('store-merged-data', 'data'),
    State('store-data-source-info', 'data'),
    State('district-dropdown', 'value'),
    prevent_initial_call=True
)
def update_district_dropdown(selected_county, gs_dim_json, merged_data_json, source_info, current_district_value):
    """Updates district dropdown options based on selected county."""
    options = [{'label': 'All Districts', 'value': 'ALL'}]
    new_value = 'ALL'
    df_for_filters = None

    # Determine which dataframe to use for filter options
    # Prefer GS dim data if selected, as it represents the current school list without year duplication
    if source_info and source_info.get('name') == GS_MERGED_DATA and gs_dim_json:
        try:
            df_for_filters = pd.read_json(StringIO(gs_dim_json), orient='split')
        except ValueError:
            logging.warning("Could not decode GS dim data for district filter.")
    elif merged_data_json: # Fallback to merged data (NJ DOE or if GS failed)
         try:
            df_for_filters = pd.read_json(StringIO(merged_data_json), orient='split')
            # Need to drop duplicates if using merged data as it has multiple years
            df_for_filters = df_for_filters.drop_duplicates(subset=['county_name', 'district_name'])
         except ValueError:
            logging.warning("Could not decode merged data for district filter.")

    if df_for_filters is None or selected_county is None:
        return options, new_value # Return default if no data

    if selected_county == 'ALL':
        districts = get_unique_sorted(df_for_filters['district_name'])
        options = [{'label': 'All Districts', 'value': 'ALL'}] + [{'label': d, 'value': d} for d in districts]
    else:
        filtered_df = df_for_filters[df_for_filters['county_name'] == selected_county]
        districts = get_unique_sorted(filtered_df['district_name'])
        options = [{'label': 'All Districts', 'value': 'ALL'}] + [{'label': d, 'value': d} for d in districts]
    return options, new_value # Always reset district when county changes

@app.callback(
    Output('school-dropdown', 'options', allow_duplicate=True),
    Output('school-dropdown', 'value', allow_duplicate=True),
    Input('county-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    # Use GS dim data if available (more complete list), else use merged data
    State('store-gs-dim-data', 'data'),
    State('store-merged-data', 'data'),
    State('store-data-source-info', 'data'),
    State('school-dropdown', 'value'),
    prevent_initial_call=True
)
def update_school_dropdown(selected_county, selected_district, gs_dim_json, merged_data_json, source_info, current_school_value):
    """Updates school dropdown options based on selected county and district."""
    options = [{'label': 'All Schools', 'value': 'ALL'}]
    new_value = 'ALL'
    df_for_filters = None

    # Determine which dataframe to use for filter options
    # Prefer GS dim data if selected
    if source_info and source_info.get('name') == GS_MERGED_DATA and gs_dim_json:
        try:
            df_for_filters = pd.read_json(StringIO(gs_dim_json), orient='split')
        except ValueError:
            logging.warning("Could not decode GS dim data for school filter.")
    elif merged_data_json: # Fallback to merged data
         try:
            df_for_filters = pd.read_json(StringIO(merged_data_json), orient='split')
            # Need to drop duplicates if using merged data
            df_for_filters = df_for_filters.drop_duplicates(subset=['county_name', 'district_name', 'school_name'])
         except ValueError:
            logging.warning("Could not decode merged data for school filter.")

    if df_for_filters is None or selected_county is None or selected_district is None:
        return options, new_value # Return default if no data

    # Filter by county first
    filtered_df = df_for_filters.copy()
    if selected_county != 'ALL':
        filtered_df = filtered_df[filtered_df['county_name'] == selected_county]

    # Filter by district if applicable and valid
    if selected_district != 'ALL':
        if selected_district in filtered_df['district_name'].unique():
            filtered_df = filtered_df[filtered_df['district_name'] == selected_district]
        else:
            selected_district = 'ALL' # Treat as All if invalid

    schools = get_unique_sorted(filtered_df['school_name'])
    options = [{'label': 'All Schools', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in schools]
    return options, new_value # Always reset school when county/district changes

# Callback 3: Update visibility of Rating Plots Row
@app.callback(
    Output('rating-plots-row', 'style'),
    Input('store-data-source-info', 'data') # Triggered when data source info changes
)
def update_rating_plots_visibility(source_info):
    """Shows or hides the rating plots row based on the selected data source."""
    if source_info and source_info.get('has_ratings', False):
        # Show rating plots row
        return {'display': 'flex'} # Use 'flex' for row behavior with bootstrap cols
    else:
        # Hide rating plots row
        return {'display': 'none'}

# Callback 4: Update All Graphs based on Filters and Stored Data
@app.callback(
    Output('enrollment-trend-graph', 'figure'),
    Output('demographic-dist-graph', 'figure'),
    Output('grade-dist-graph', 'figure'),
    Output('language-dist-graph', 'figure'),
    Output('rating-graph', 'figure'),
    Output('rating-band-graph', 'figure'),
    Input('store-merged-data', 'data'),         # Academic merged data
    Input('store-merged-lang-data', 'data'),   # Academic language merged data
    Input('store-gs-dim-data', 'data'),        # GS dimension data (for ratings)
    Input('store-data-source-info', 'data'),   # Info about current source
    Input('year-dropdown', 'value'),           # Year filter (for academic plots)
    Input('county-dropdown', 'value'),         # Filters for all plots
    Input('district-dropdown', 'value'),
    Input('school-dropdown', 'value'),
    prevent_initial_call=True # Wait for data to be loaded initially
)
def update_graphs(merged_data_json, merged_lang_data_json, gs_dim_json, source_info, selected_year, selected_county, selected_district, selected_school):
    """Updates all graph figures based on stored data and filter selections."""
    # Initialize all figures to empty state
    fig_trend = create_empty_figure('Select filters to view trend')
    fig_demographic = create_empty_figure('Select filters to view demographics')
    fig_grade = create_empty_figure('Select filters to view grade distribution')
    fig_language = create_empty_figure('Select filters to view languages')
    fig_rating = create_empty_figure('Rating data not applicable or available')
    fig_rating_band = create_empty_figure('Rating band data not applicable or available')

    # --- Generate Rating Plots (if GS data is selected) ---
    if source_info and source_info.get('has_ratings', False) and gs_dim_json:
        try:
            df_gs_dim = pd.read_json(StringIO(gs_dim_json), orient='split')
            logging.debug(f"GS Dim data for rating plots head:\n{df_gs_dim.head()}") # Add debug log

            # Filter GS dim data by County, District, School ONLY
            gs_filtered_df = df_gs_dim.copy()
            rating_filter_context = "Statewide"
            if selected_county != 'ALL':
                gs_filtered_df = gs_filtered_df[gs_filtered_df['county_name'] == selected_county]
                rating_filter_context = f"{selected_county} County"
            if selected_district != 'ALL':
                if selected_district in gs_filtered_df['district_name'].unique():
                    gs_filtered_df = gs_filtered_df[gs_filtered_df['district_name'] == selected_district]
                    rating_filter_context = f"{selected_district} District"
            if selected_school != 'ALL':
                 if selected_school in gs_filtered_df['school_name'].unique():
                    gs_filtered_df = gs_filtered_df[gs_filtered_df['school_name'] == selected_school]
                    rating_filter_context = selected_school

            # 5. Rating Distribution (Histogram)
            if not gs_filtered_df.empty and 'rating' in gs_filtered_df.columns:
                ratings_data = gs_filtered_df[['rating']].dropna(subset=['rating']) # Only need rating column
                if not ratings_data.empty:
                     fig_rating = px.histogram(
                         ratings_data, x='rating', nbins=10,
                         title=f'Current School Rating Distribution ({rating_filter_context})', # Title updated
                         labels={'rating': 'Great Schools Rating (1-10)'}
                     )
                     fig_rating.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20), bargap=0.1)
                else:
                     fig_rating = create_empty_figure(f'No rating data for {rating_filter_context}')

            # 6. Rating Band Distribution (Donut Chart)
            if not gs_filtered_df.empty and 'rating_band' in gs_filtered_df.columns:
                # Use the already standardized 'rating_band' column
                logging.debug(f"Rating band counts input:\n{gs_filtered_df['rating_band'].value_counts()}") # Add debug log
                rating_band_counts = gs_filtered_df['rating_band'].value_counts().reset_index()
                rating_band_counts.columns = ['Rating Band', 'Count']
                # Exclude 'Unknown' category explicitly IF it exists after value_counts
                rating_band_counts = rating_band_counts[rating_band_counts['Rating Band'] != 'Unknown']

                band_order = ['Below Average', 'Average', 'Above Average'] # Order is Title Case
                # Apply categorical ordering based on the standardized Title Case bands
                if 'Rating Band' in rating_band_counts.columns:
                    # Get unique bands present *after* filtering 'Unknown'
                    present_bands = [band for band in band_order if band in rating_band_counts['Rating Band'].unique()]
                    if present_bands:
                         rating_band_counts['Rating Band'] = pd.Categorical(rating_band_counts['Rating Band'], categories=present_bands, ordered=True)
                         rating_band_counts = rating_band_counts.sort_values('Rating Band')

                logging.debug(f"Rating band counts for plot:\n{rating_band_counts}") # Add debug log

                if not rating_band_counts.empty:
                    fig_rating_band = px.pie(
                        rating_band_counts, names='Rating Band', values='Count',
                        title=f'Current Schools by Rating Band ({rating_filter_context})', # Title updated
                        hole=0.4
                    )
                    fig_rating_band.update_traces(textposition='inside', textinfo='percent+label',
                                                  pull=[0.05 if band == 'Above Average' else 0 for band in rating_band_counts['Rating Band']])
                    fig_rating_band.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
                else:
                     # This message should appear if only 'Unknown' bands were present or df was empty
                     fig_rating_band = create_empty_figure(f'No valid rating band data for {rating_filter_context}')

        except ValueError:
            logging.error("Could not decode GS dim data for rating graphs.", exc_info=True)
            fig_rating = create_empty_figure("Error loading rating data.")
            fig_rating_band = create_empty_figure("Error loading rating band data.")
        except Exception as e:
             logging.error(f"Error generating rating plots: {e}", exc_info=True)
             fig_rating = create_empty_figure("Error generating rating plot.")
             fig_rating_band = create_empty_figure("Error generating rating band plot.")

    # --- Generate Academic Year Plots (if data and year are selected) ---
    # Check for essential academic data and selected year
    if not merged_data_json or not merged_lang_data_json or not selected_year:
        logging.warning("Academic graph update skipped: Merged data or year not available.")
        # Keep the empty figures initialized earlier, but return rating plots if generated
        return fig_trend, fig_demographic, fig_grade, fig_language, fig_rating, fig_rating_band

    # Proceed with academic plots generation inside a try-except block
    try:
        # Load academic data from JSON stores
        df_merged = pd.read_json(StringIO(merged_data_json), orient='split')
        df_merged_lang = pd.read_json(StringIO(merged_lang_data_json), orient='split')

        # Ensure academic_year is categorical after loading from JSON
        if 'academic_year' in df_merged.columns:
             unique_years = sorted(df_merged['academic_year'].astype(str).unique())
             df_merged['academic_year'] = pd.Categorical(df_merged['academic_year'].astype(str), ordered=True, categories=unique_years)
        if 'academic_year' in df_merged_lang.columns:
             unique_years_lang = sorted(df_merged_lang['academic_year'].astype(str).unique())
             df_merged_lang['academic_year'] = pd.Categorical(df_merged_lang['academic_year'].astype(str), ordered=True, categories=unique_years_lang)

        # --- Filter Academic Data ---
        trend_filtered_df = df_merged.copy() # For trend across all years
        year_filtered_df = df_merged[df_merged['academic_year'] == selected_year]
        lang_year_filtered_df = df_merged_lang[df_merged_lang['academic_year'] == selected_year]

        # Apply filters progressively (County, District, School)
        academic_filter_context = "Statewide"
        if selected_county != 'ALL':
            trend_filtered_df = trend_filtered_df[trend_filtered_df['county_name'] == selected_county]
            year_filtered_df = year_filtered_df[year_filtered_df['county_name'] == selected_county]
            lang_year_filtered_df = lang_year_filtered_df[lang_year_filtered_df['county_name'] == selected_county]
            academic_filter_context = f"{selected_county} County"
        if selected_district != 'ALL':
            if selected_district in trend_filtered_df['district_name'].unique():
                trend_filtered_df = trend_filtered_df[trend_filtered_df['district_name'] == selected_district]
                year_filtered_df = year_filtered_df[year_filtered_df['district_name'] == selected_district]
                lang_year_filtered_df = lang_year_filtered_df[lang_year_filtered_df['district_name'] == selected_district]
                academic_filter_context = f"{selected_district} District"
        if selected_school != 'ALL':
             if selected_school in trend_filtered_df['school_name'].unique():
                trend_filtered_df = trend_filtered_df[trend_filtered_df['school_name'] == selected_school]
                year_filtered_df = year_filtered_df[year_filtered_df['school_name'] == selected_school]
                lang_year_filtered_df = lang_year_filtered_df[lang_year_filtered_df['school_name'] == selected_school]
                academic_filter_context = selected_school

        # --- Generate Academic Figures ---
        # 1. Enrollment Trend
        if not trend_filtered_df.empty:
            trend_grouped = trend_filtered_df.groupby('academic_year', observed=True)['total_enrollment'].sum().reset_index()
            if not trend_grouped.empty:
                fig_trend = px.line(
                    trend_grouped, x='academic_year', y='total_enrollment',
                    title=f'Total Enrollment Trend ({academic_filter_context})', markers=True,
                    labels={'total_enrollment': 'Total Students', 'academic_year': 'Academic Year'}
                )
                fig_trend.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))
            else:
                # Handle case where groupby results in empty df (e.g., only one year selected)
                fig_trend = create_empty_figure(f'No trend data for {academic_filter_context}')
        else:
            # Handle case where initial filtering makes df empty
             fig_trend = create_empty_figure(f'No trend data for {academic_filter_context}')

        # Plots based on single selected year
        if not year_filtered_df.empty:
            year_agg = year_filtered_df.sum(numeric_only=True)

            # 2. Demographic Distribution
            valid_demo_cols = [col for col in DEMOGRAPHIC_COLS if col in year_agg]
            if valid_demo_cols:
                demographic_data = year_agg[valid_demo_cols].reset_index()
                demographic_data.columns = ['Demographic', 'Count']
                demographic_data = demographic_data[demographic_data['Count'] > 0]
                if not demographic_data.empty:
                    fig_demographic = px.pie(
                        demographic_data, names='Demographic', values='Count',
                        title=f'Demographics in {selected_year} ({academic_filter_context})', hole=0.3
                    )
                    fig_demographic.update_traces(textposition='inside', textinfo='percent+label')
                    fig_demographic.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
                else:
                    fig_demographic = create_empty_figure(f'No demographic data for {academic_filter_context} in {selected_year}')

            # 3. Grade Level Distribution
            valid_grade_cols = [col for col in GRADE_COLS if col in year_agg]
            if valid_grade_cols:
                grade_data = year_agg[valid_grade_cols].reset_index()
                grade_data.columns = ['Grade', 'Count']
                grade_data = grade_data[grade_data['Count'] > 0]
                if not grade_data.empty:
                    grade_data['Grade'] = grade_data['Grade'].str.replace('grade', 'Grade ').str.upper()
                    fig_grade = px.bar(
                        grade_data, x='Grade', y='Count',
                        title=f'Enrollment by Grade in {selected_year} ({academic_filter_context})',
                        labels={'Count': 'Number of Students'}
                    )
                    fig_grade.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20), xaxis_title=None)
                else:
                     fig_grade = create_empty_figure(f'No grade data for {academic_filter_context} in {selected_year}')
        else: # year_filtered_df is empty
             fig_demographic = create_empty_figure(f'No data for {academic_filter_context} in {selected_year}')
             fig_grade = create_empty_figure(f'No data for {academic_filter_context} in {selected_year}')

        # 4. Home Language Distribution (using lang_year_filtered_df)
        if not lang_year_filtered_df.empty:
            lang_grouped = lang_year_filtered_df.groupby('home_language', observed=True)['student_count'].sum().reset_index()
            lang_grouped = lang_grouped[lang_grouped['student_count'] > 0]
            if not lang_grouped.empty:
                lang_grouped = lang_grouped.sort_values(by='student_count', ascending=False).head(15)
                fig_language = px.bar(
                    lang_grouped, x='student_count', y='home_language', orientation='h',
                    title=f'Top Home Languages in {selected_year} ({academic_filter_context})',
                    labels={'student_count': 'Estimated Number of Students', 'home_language': 'Home Language'}
                )
                fig_language.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20), yaxis={'categoryorder':'total ascending'})
            else:
                 fig_language = create_empty_figure(f'No language data for {academic_filter_context} in {selected_year}')
        else: # lang_year_filtered_df is empty
             fig_language = create_empty_figure(f'No language data for {academic_filter_context} in {selected_year}')

    except ValueError as e: # Catch specific ValueError from pd.read_json
        logging.error(f"Could not decode academic data from store: {e}", exc_info=True)
        fig_trend = create_empty_figure("Error loading trend data.")
        fig_demographic = create_empty_figure("Error loading demographic data.")
        fig_grade = create_empty_figure("Error loading grade data.")
        fig_language = create_empty_figure("Error loading language data.")

    except Exception as e: # Catch other potential errors during academic plot generation
        logging.error(f"Error generating academic plots: {e}", exc_info=True)
        fig_trend = create_empty_figure("Error generating trend plot.")
        fig_demographic = create_empty_figure("Error generating demographic plot.")
        fig_grade = create_empty_figure("Error generating grade plot.")
        fig_language = create_empty_figure("Error generating language plot.")
    return fig_trend, fig_demographic, fig_grade, fig_language, fig_rating, fig_rating_band

# --- Run the App ---
if __name__ == '__main__':
    logging.info("Dash app starting...")
    logging.info(f"Access it at: http://127.0.0.1:8050")
    app.run(debug=True)
