import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import subprocess
import os
from datetime import datetime

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("FIO Storage Benchmark Dashboard"),
    
    html.Div([
        html.Label("Direct I/O (bypass cache):"),
        dcc.Dropdown(
            id='direct',
            options=[
                {'label': 'Yes (1)', 'value': '1'},
                {'label': 'No (0)', 'value': '0'}
            ],
            value='1'
        ),
        
        html.Label("I/O Pattern:"),
        dcc.Dropdown(
            id='rw',
            options=[
                {'label': 'Random Read', 'value': 'randread'},
                {'label': 'Random Write', 'value': 'randwrite'},
                {'label': 'Random Mixed', 'value': 'randrw'},
                {'label': 'Sequential Read', 'value': 'read'},
                {'label': 'Sequential Write', 'value': 'write'}
            ],
            value='randread'
        ),
        
        html.Label("Block Size:"),
        dcc.Dropdown(
            id='bs',
            options=[
                {'label': '4k', 'value': '4k'},
                {'label': '8k', 'value': '8k'},
                {'label': '16k', 'value': '16k'},
                {'label': '64k', 'value': '64k'}
            ],
            value='4k'
        ),
        
        html.Label("Number of Jobs:"),
        dcc.Dropdown(
            id='numjobs',
            options=[
                {'label': '1', 'value': '1'},
                {'label': '4', 'value': '4'},
                {'label': '8', 'value': '8'},
                {'label': '16', 'value': '16'}
            ],
            value='1'
        ),
        
        html.Label("I/O Depth:"),
        dcc.Dropdown(
            id='iodepth',
            options=[
                {'label': '1', 'value': '1'},
                {'label': '8', 'value': '8'},
                {'label': '16', 'value': '16'},
                {'label': '32', 'value': '32'}
            ],
            value='1'
        ),
        
        html.Button('Run FIO Benchmark', id='run-button', n_clicks=0),
    ], style={'width': '300px', 'margin': '20px'}),
    
    html.Div(id='status'),
    html.Div(id='charts')
])

@app.callback(
    [Output('status', 'children'), Output('charts', 'children')],
    [Input('run-button', 'n_clicks')],
    [State('direct', 'value'),
     State('rw', 'value'),
     State('bs', 'value'),
     State('numjobs', 'value'),
     State('iodepth', 'value')]
)
def run_fio_test(n_clicks, direct, rw, bs, numjobs, iodepth):
    if n_clicks == 0:
        return "", ""
    
    # Create test data directory
    os.makedirs('/app/test-data', exist_ok=True)
    
    # Build FIO command
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'/app/test-data/results_{timestamp}.json'
    
    fio_cmd = [
        'fio',
        f'--filename=/app/test-data/testfile_{timestamp}',
        f'--direct={direct}',
        f'--rw={rw}',
        f'--bs={bs}',
        f'--numjobs={numjobs}',
        f'--iodepth={iodepth}',
        '--size=100M',
        '--runtime=10',
        '--status-interval=1',  # Emit progress logs every second
        '--output-format=json',
        f'--output={output_file}',
        f'--name=test_{timestamp}'
    ]
    # Log the FIO command
    print(f"Running FIO command: {' '.join(fio_cmd)}", flush=True)

    try:
        result = subprocess.run(fio_cmd, capture_output=True, text=True, timeout=60)
        # Log FIO results
        print(f"FIO return code: {result.returncode}", flush=True)
        print(f"FIO stdout: {result.stdout}", flush=True)
        print(f"FIO stderr: {result.stderr}", flush=True)
        
        if result.returncode != 0:
            return f"Error running FIO: {result.stderr}", ""
        
        with open(output_file, 'r') as f:
            fio_data = json.load(f)
        
        job = fio_data['jobs'][0]
        
        charts = []
        
        # IOPS Chart
        iops_data = {
            'Read IOPS': job['read']['iops'],
            'Write IOPS': job['write']['iops']
        }
        
        iops_fig = go.Figure(data=[
            go.Bar(name='IOPS', x=list(iops_data.keys()), y=list(iops_data.values()))
        ])
        iops_fig.update_layout(title='IOPS Performance')
        
        # Bandwidth Chart
        bw_data = {
            'Read BW (MB/s)': job['read']['bw'] / 1024,  # Convert to MB/s
            'Write BW (MB/s)': job['write']['bw'] / 1024
        }
        
        bw_fig = go.Figure(data=[
            go.Bar(name='Bandwidth', x=list(bw_data.keys()), y=list(bw_data.values()))
        ])
        bw_fig.update_layout(title='Bandwidth Performance')
        
        # Latency Chart
        lat_data = {
            'Read Latency (ms)': job['read']['lat_ns']['mean'] / 1000000,  # Convert to ms
            'Write Latency (ms)': job['write']['lat_ns']['mean'] / 1000000
        }
        
        lat_fig = go.Figure(data=[
            go.Bar(name='Latency', x=list(lat_data.keys()), y=list(lat_data.values()))
        ])
        lat_fig.update_layout(title='Average Latency')
        
        charts = [
            dcc.Graph(figure=iops_fig),
            dcc.Graph(figure=bw_fig),
            dcc.Graph(figure=lat_fig)
        ]
        
        return f"Test completed successfully! Results saved to {output_file}", charts
        
    except subprocess.TimeoutExpired:
        return "Test timed out after 60 seconds", ""
    except Exception as e:
        return f"Error: {str(e)}", ""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
