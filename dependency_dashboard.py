import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objects as go
import networkx as nx
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.express as px

# Initialize the Dash app
app = dash.Dash(__name__, title="Dream.OS Architecture Explorer")

# Load the latest dependency data
def load_latest_data():
    output_dir = Path("outputs")
    graph_file = output_dir / "dependency_graph.json"
    with open(graph_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Create layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Dream.OS Architecture Explorer", className="dashboard-title"),
        html.P(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", id="last-updated"),
    ], className="header"),
    
    # Main content
    html.Div([
        # Left sidebar - Filters
        html.Div([
            html.H3("Filters"),
            
            # Module group filter
            html.Label("Module Groups"),
            dcc.Dropdown(
                id='group-filter',
                multi=True,
                placeholder="Select module groups..."
            ),
            
            # Hotspot score range
            html.Label("Hotspot Score Range"),
            dcc.RangeSlider(
                id='hotspot-range',
                min=0,
                max=1,
                step=0.1,
                marks={i/10: str(i/10) for i in range(11)},
                value=[0, 1]
            ),
            
            # Size filter
            html.Label("Module Size (KB)"),
            dcc.RangeSlider(
                id='size-range',
                min=0,
                max=100,
                step=5,
                marks={i: str(i) for i in range(0, 101, 20)},
                value=[0, 100]
            ),
            
            # Search box
            html.Label("Search Modules"),
            dcc.Input(
                id='search-box',
                type='text',
                placeholder='Enter module name...'
            ),
            
            # Update button
            html.Button('Update View', id='update-button', n_clicks=0),
            
        ], className="sidebar"),
        
        # Main content area
        html.Div([
            # Tabs for different views
            dcc.Tabs([
                # Network View
                dcc.Tab(label='Network View', children=[
                    dcc.Graph(id='network-graph')
                ]),
                
                # Hotspots View
                dcc.Tab(label='Hotspots', children=[
                    dcc.Graph(id='hotspots-chart')
                ]),
                
                # Metrics View
                dcc.Tab(label='Metrics', children=[
                    dcc.Graph(id='metrics-chart')
                ]),
                
                # Cycles View
                dcc.Tab(label='Dependency Cycles', children=[
                    html.Div(id='cycles-list')
                ])
            ]),
            
            # Module details panel (hidden by default)
            html.Div(id='module-details', className='module-details-panel')
        ], className="main-content")
    ], className="content-wrapper"),
])

# Callback to update network graph
@app.callback(
    Output('network-graph', 'figure'),
    [Input('update-button', 'n_clicks')],
    [State('group-filter', 'value'),
     State('hotspot-range', 'value'),
     State('size-range', 'value'),
     State('search-box', 'value')]
)
def update_network_graph(n_clicks, groups, hotspot_range, size_range, search_term):
    data = load_latest_data()
    
    # Filter nodes based on criteria
    nodes = pd.DataFrame(data['nodes'])
    filtered_nodes = nodes[
        (nodes['hotspot_score'].between(hotspot_range[0], hotspot_range[1])) &
        (nodes['size_kb'].between(size_range[0], size_range[1]))
    ]
    
    if groups:
        filtered_nodes = filtered_nodes[filtered_nodes['group'].isin(groups)]
    
    if search_term:
        filtered_nodes = filtered_nodes[
            filtered_nodes['id'].str.contains(search_term, case=False)
        ]
    
    # Create network layout
    G = nx.Graph()
    for _, node in filtered_nodes.iterrows():
        G.add_node(node['id'])
    
    # Add edges between filtered nodes
    edges = pd.DataFrame(data['edges'])
    filtered_edges = edges[
        edges['from'].isin(filtered_nodes['id']) &
        edges['to'].isin(filtered_nodes['id'])
    ]
    
    for _, edge in filtered_edges.iterrows():
        G.add_edge(edge['from'], edge['to'])
    
    # Calculate layout
    pos = nx.spring_layout(G)
    
    # Create Plotly figure
    edge_trace = go.Scatter(
        x=[], y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)
    
    node_trace = go.Scatter(
        x=[], y=[],
        text=[],
        mode='markers+text',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlOrRd',
            size=[],
            color=[],
            line_width=2
        )
    )
    
    for node in G.nodes():
        x, y = pos[node]
        node_data = filtered_nodes[filtered_nodes['id'] == node].iloc[0]
        node_trace['x'] += (x,)
        node_trace['y'] += (y,)
        node_trace['text'] += (node,)
        node_trace['marker']['size'] += (20 + node_data['hotspot_score'] * 30,)
        node_trace['marker']['color'] += (node_data['hotspot_score'],)
    
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                   ))
    
    return fig

# Callback to update hotspots chart
@app.callback(
    Output('hotspots-chart', 'figure'),
    [Input('update-button', 'n_clicks')]
)
def update_hotspots_chart(n_clicks):
    data = load_latest_data()
    hotspots = pd.DataFrame(data['hotspots'])
    
    fig = px.bar(hotspots,
                 x='module',
                 y='score',
                 title='Top Hotspots',
                 hover_data=['reasons'])
    
    return fig

# Callback to update module details
@app.callback(
    Output('module-details', 'children'),
    [Input('network-graph', 'clickData')]
)
def display_module_details(clickData):
    if not clickData:
        return html.Div()
    
    data = load_latest_data()
    module_id = clickData['points'][0]['text']
    module_data = next(n for n in data['nodes'] if n['id'] == module_id)
    
    return html.Div([
        html.H3(module_id),
        html.Table([
            html.Tr([html.Td("Size"), html.Td(f"{module_data['size_kb']} KB")]),
            html.Tr([html.Td("Classes"), html.Td(module_data['class_count'])]),
            html.Tr([html.Td("Functions"), html.Td(module_data['function_count'])]),
            html.Tr([html.Td("Hotspot Score"), html.Td(f"{module_data['hotspot_score']:.2f}")]),
            html.Tr([html.Td("Last Modified"), html.Td(module_data['last_modified'])]),
            html.Tr([html.Td("Author"), html.Td(module_data['last_author'])]),
        ])
    ])

if __name__ == '__main__':
    app.run_server(debug=True) 