import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output
from callcenter_analytics.utils import fetchAgentCustomerValues
from configuration.config import SSL_CERTIFICATE_SERVER_PEM_FILE_PATH, SSL_CERTIFICATE_PRIVATE_KEY_PEM_FILE_PATH

# Function to create the Dash app and integrate it with Flask
def create_dash_app(flask_app):
    # Create Dash app instance
    app = Dash(server=flask_app, name="Dashboard", url_base_pathname='/dashboard/',
               external_stylesheets=[dbc.themes.BOOTSTRAP])
    
    def prepareChart(title, val):
        chart = go.Figure(go.Indicator(
            domain={'x': [0, 1], 'y': [0, 1]},
            value=val,
            number={'font_color': '#ffffff'},
            mode="gauge+number",
            title={'font': {'color': '#ffffff', 'size': 13}},
            gauge={'axis': {'range': [None, 10], 'tickcolor': '#ffffff'},
                   'steps': [
                       {'range': [0, 3], 'color': "red"},
                       {'range': [3, 7], 'color': "yellow"},
                       {'range': [7, 10], 'color': "lightgreen"}
                   ]},
        ))
        chart.layout.plot_bgcolor = '#323447'
        chart.layout.paper_bgcolor = '#323447'
        chart.layout.font.color = '#ffffff'
        chart.update_layout(title_text=title, title_x=0.5, title_y=0.975)
        return chart
    
    @app.callback(Output('live-update-charts', 'children'),
                  Input('update-interval', 'n_intervals'))
    def update_charts(n):
        result = fetchAgentCustomerValues()
        layout = html.Div(
            children=[
                html.Div(id='live-update-charts',
                         children=[
                             html.H1(style={'textAlign': 'center', 'fontFamily': 'Arial', 'fontSize': '40px',
                                            'color': '#84db69', 'background': '#323447'},
                                     children="Sentiment Insights Dashboard"),
                             html.Div(style={'display': 'flex'},
                                      children=[html.Div(children=[
                                          html.H1(style={'textAlign': 'center', 'fontFamily': 'Arial', 'fontSize': '18px',
                                                         'fontWeight': '100', 'background': '#323447', 'color': '#ffffff',
                                                         'width': '350px', 'height': '20px', 'margin-bottom': '-33px',
                                                         'margin-top': '10px', 'margin-left': '10px', 'padding-bottom': '1px',
                                                         'padding-top': '3px'}, children="Issue Status"),
                                          html.H2(style={'textAlign': 'center', 'fontFamily': 'Open Sans', 'fontSize': '40px',
                                                         'background': '#323447', 'color': '#ffffff', 'width': '350px',
                                                         'height': '146px', 'margin-left': '10px', 'margin-right': '10px',
                                                         'padding-top': '100px'}, children=result[5])
                                      ]),
                                          dcc.Graph(style={'height': '270px', 'width': '380px', 'margin': '10px'},
                                                    figure=prepareChart("Agent Confusion", result[0])),
                                          dcc.Graph(style={'height': '270px', 'width': '380px', 'margin': '10px'},
                                                    figure=prepareChart("Agent Knowledge", result[1]))]),
                             html.Div(style={'display': 'flex'},
                                      children=[dcc.Graph(style={'height': '270px', 'width': '380px', 'margin': '10px'},
                                                          figure=prepareChart("Customer Sentiment(Start of Call)", result[2])),
                                                dcc.Graph(style={'height': '270px', 'width': '380px', 'margin': '10px'},
                                                          figure=prepareChart("Customer Sentiment(End of Call)", result[3])),
                                                dcc.Graph(style={'height': '270px', 'width': '380px', 'margin': '10px'},
                                                          figure=prepareChart("Customer Satisfaction", result[4]))]),
                             dcc.Interval(
                                 id='update-interval',
                                 interval=30 * 1000,
                                 n_intervals=0
                             )
                         ])
            ]
        )
        return layout
    
    app.layout = update_charts(0)
    
    return app
