import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import subprocess
import os
import yaml
from datetime import datetime
import numpy as np

# Load configuration
with open('fio_defaults.yaml', 'r') as f:
    config = yaml.safe_load(f)

app = dash.Dash(__name__)

# Add CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 0;
            }
            
            .main-container {
                background: rgba(255, 255, 255, 0.95);
                margin: 20px;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(90deg, #2C3E50 0%, #3498DB 100%);
                color: white;
                padding: 30px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                margin: 0;
                font-size: 32px;
                font-weight: 300;
                letter-spacing: 2px;
            }
            
            .header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 16px;
            }
            
            .control-panel {
                background: #f8f9fa;
                border-right: 3px solid #e9ecef;
                min-height: calc(100vh - 200px);
            }
            
            .control-section {
                padding: 25px;
                border-bottom: 1px solid #e9ecef;
            }
            
            .control-section h3 {
                color: #2C3E50;
                margin: 0 0 20px 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .control-section h4 {
                color: #34495E;
                margin: 20px 0 15px 0;
                font-size: 16px;
                font-weight: 500;
            }
            
            .control-section label {
                color: #5D6D7E;
                font-weight: 500;
                margin-bottom: 8px;
                display: block;
            }
            
            .run-button {
                background: linear-gradient(45deg, #FF6B6B, #FF8E53) !important;
                border: none !important;
                color: white !important;
                font-size: 18px !important;
                font-weight: 600 !important;
                padding: 15px 30px !important;
                border-radius: 25px !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4) !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
            }
            
            .run-button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 20px rgba(255, 107, 107, 0.6) !important;
            }
            
            .results-panel {
                padding: 30px;
                background: white;
            }
            
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px 25px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
                text-align: center;
                min-width: 160px;
                transition: transform 0.3s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-5px);
            }
            
            .metric-card h4 {
                font-size: 36px;
                font-weight: 700;
                margin: 0;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            
            .metric-card p {
                font-size: 14px;
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .metric-card.iops {
                background: linear-gradient(135deg, #FF6B6B, #FF8E53);
                box-shadow: 0 10px 30px rgba(255, 107, 107, 0.3);
            }
            
            .metric-card.bandwidth {
                background: linear-gradient(135deg, #4ECDC4, #44A08D);
                box-shadow: 0 10px 30px rgba(78, 205, 196, 0.3);
            }
            
            .metric-card.latency {
                background: linear-gradient(135deg, #45B7D1, #96C93D);
                box-shadow: 0 10px 30px rgba(69, 183, 209, 0.3);
            }
            
            .metric-card.duration {
                background: linear-gradient(135deg, #F093FB, #F5576C);
                box-shadow: 0 10px 30px rgba(240, 147, 251, 0.3);
            }
            
            .chart-container {
                background: white;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                margin: 20px 0;
                padding: 20px;
                border: 1px solid #f0f0f0;
            }
            
            .chart-title {
                color: #2C3E50;
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 15px;
                text-align: center;
            }
            
            .status-success {
                background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
                color: #1e3a8a;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-weight: 500;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .status-error {
                background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
                color: #7f1d1d;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-weight: 500;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .detailed-table {
                background: white;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                margin-top: 30px;
            }
            
            .detailed-table h4 {
                background: linear-gradient(90deg, #2C3E50 0%, #3498DB 100%);
                color: white;
                padding: 20px;
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
    html.Div([
        # Header
        html.Div([
            html.H1("FIO Storage Benchmark Dashboard"),
            html.P("Professional Storage Performance Analysis Tool")
        ], className='header'),
        
        html.Div([
            # Left Panel - Controls
            html.Div([
                html.Div([
                    html.H3("🎯 Test Configuration"),
                    
                    html.Label("Test Scenario:"),
                    dcc.Dropdown(
                        id='scenario',
                        options=[
                            {'label': '⚡ Instant (5s)', 'value': 'instant'},
                            {'label': '🚀 Quick (30s)', 'value': 'quick'},
                            {'label': '📊 Standard (60s)', 'value': 'standard'},
                            {'label': '🏢 Enterprise (300s)', 'value': 'enterprise'}
                        ],
                        value='standard',
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Label("Workload Preset:"),
                    dcc.Dropdown(
                        id='workload_preset',
                        options=[
                            {'label': f"💾 {v['name']}", 'value': k} 
                            for k, v in config['workloads'].items()
                        ],
                        value='oltp',
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Label("Storage Type:"),
                    dcc.Dropdown(
                        id='storage_type',
                        options=[
                            {'label': f"🔥 {v['name']}", 'value': k}
                            for k, v in config['storage_types'].items()
                        ],
                        value='nvme_ssd',
                        style={'marginBottom': '15px'}
                    ),
                ], className='control-section'),
                
                html.Div([
                    html.H4("⚙️ Advanced Settings"),
                    
                    html.Label("Direct I/O (bypass cache):"),
                    dcc.RadioItems(
                        id='direct',
                        options=[
                            {'label': '✅ Yes (recommended)', 'value': '1'},
                            {'label': '❌ No', 'value': '0'}
                        ],
                        value='1',
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Label("Block Size:"),
                    dcc.Dropdown(
                        id='bs',
                        options=[{'label': bs, 'value': bs} for bs in config['block_sizes']],
                        value='4k',
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Label("Queue Depth:"),
                    dcc.Dropdown(
                        id='iodepth',
                        options=[{'label': str(qd), 'value': str(qd)} for qd in config['queue_depths']],
                        value='32',
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Label("Number of Jobs:"),
                    dcc.Dropdown(
                        id='numjobs',
                        options=[{'label': str(nj), 'value': str(nj)} for nj in config['job_counts']],
                        value='4',
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Label("Test File Size:"),
                    dcc.Input(
                        id='size',
                        type='text',
                        value='1G',
                        placeholder='e.g., 1G, 500M, 2048M',
                        style={'width': '100%', 'padding': '8px', 'borderRadius': '5px', 'border': '1px solid #ddd'}
                    ),
                ], className='control-section'),
                
                html.Div([
                    html.Button('🚀 Run FIO Benchmark', id='run-button', n_clicks=0, 
                               className='run-button',
                               style={'width': '100%', 'marginTop': '10px'}),
                ], className='control-section'),
                       
            ], className='control-panel', style={'width': '350px'}),
            
            # Right Panel - Results
            html.Div([
                html.Div(id='status'),
                html.Div(id='charts')
            ], className='results-panel', style={'flex': 1})
            
        ], style={'display': 'flex'})
        
    ], className='main-container'),
    
    # Store for test results
    dcc.Store(id='test-results-store')
], style={'minHeight': '100vh'})

@app.callback(
    [Output('bs', 'value'),
     Output('iodepth', 'value'), 
     Output('numjobs', 'value')],
    [Input('workload_preset', 'value'),
     Input('storage_type', 'value')]
)
def update_settings_from_preset(workload_preset, storage_type):
    if workload_preset and workload_preset in config['workloads']:
        workload = config['workloads'][workload_preset]
        bs = workload.get('bs', '4k')
        iodepth = str(workload.get('iodepth', 32))
        numjobs = str(workload.get('numjobs', 4))
        
        # Override with storage type recommendations
        if storage_type and storage_type in config['storage_types']:
            storage = config['storage_types'][storage_type]
            iodepth = str(storage.get('recommended_iodepth', iodepth))
            numjobs = str(storage.get('recommended_numjobs', numjobs))
            
        return bs, iodepth, numjobs
    
    return '4k', '32', '4'

@app.callback(
    [Output('size', 'value')],
    [Input('scenario', 'value')]
)
def update_size_from_scenario(scenario):
    if scenario and scenario in config['scenarios']:
        return [config['scenarios'][scenario]['size']]
    return ['1G']

@app.callback(
    [Output('status', 'children'), Output('charts', 'children'), Output('test-results-store', 'data')],
    [Input('run-button', 'n_clicks')],
    [State('scenario', 'value'),
     State('workload_preset', 'value'),
     State('direct', 'value'),
     State('bs', 'value'),
     State('numjobs', 'value'),
     State('iodepth', 'value'),
     State('size', 'value')]
)
def run_fio_test(n_clicks, scenario, workload_preset, direct, bs, numjobs, iodepth, size):
    if n_clicks == 0:
        return "", "", {}
    
    # Create test data directory
    os.makedirs('/app/test-data', exist_ok=True)
    
    # Get scenario settings
    scenario_config = config['scenarios'].get(scenario, config['scenarios']['standard'])
    workload_config = config['workloads'].get(workload_preset, config['workloads']['oltp'])
    
    # Build FIO command
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'/app/test-data/results_{timestamp}.json'
    
    # Determine read/write pattern
    rw = workload_config.get('rw', 'randread')
    rwmixread = workload_config.get('rwmixread', 100)
    
    fio_cmd = [
        'fio',
        f'--filename=/app/test-data/testfile_{timestamp}',
        f'--direct={direct}',
        f'--rw={rw}',
        f'--bs={bs}',
        f'--numjobs={numjobs}',
        f'--iodepth={iodepth}',
        f'--size={size}',
        f'--runtime={scenario_config["runtime"]}',
        f'--ramp_time={scenario_config["ramp_time"]}',
        '--time_based',
        '--ioengine=libaio',
        '--group_reporting',
        '--output-format=json',
        f'--output={output_file}',
        f'--name=test_{timestamp}'
    ]
    
    # Add read/write mix if applicable
    if 'rw' in rw and rwmixread < 100:
        fio_cmd.append(f'--rwmixread={rwmixread}')
    
    # Log the FIO command
    print(f"Running FIO command: {' '.join(fio_cmd)}", flush=True)

    try:
        result = subprocess.run(fio_cmd, capture_output=True, text=True, timeout=scenario_config["runtime"] + 60)
        
        # Log FIO results
        print(f"FIO return code: {result.returncode}", flush=True)
        if result.stdout:
            print(f"FIO stdout: {result.stdout}", flush=True)
        if result.stderr:
            print(f"FIO stderr: {result.stderr}", flush=True)

        if result.returncode != 0:
            return f"Error running FIO: {result.stderr}", "", {}
        
        with open(output_file, 'r') as f:
            fio_data = json.load(f)
        
        # Create comprehensive visualizations
        charts = create_comprehensive_charts(fio_data, workload_config)
        
        # Create status summary
        status = create_status_summary(fio_data, workload_config, scenario_config)
        
        return status, charts, fio_data
        
    except subprocess.TimeoutExpired:
        return f"Test timed out after {scenario_config['runtime'] + 60} seconds", "", {}
    except Exception as e:
        return f"Error: {str(e)}", "", {}

def create_status_summary(fio_data, workload_config, scenario_config):
    """Create a status summary card"""
    job = fio_data['jobs'][0] if fio_data['jobs'] else {}
    
    read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024  # Convert to MB/s
    write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    
    return html.Div([
        html.H3("Test Results Summary"),
        html.Div([
            html.Div([
                html.H4(f"{read_iops + write_iops:.0f}", style={'color': '#1f77b4', 'margin': 0}),
                html.P("Total IOPS", style={'margin': 0})
            ], className='metric-card iops'),
            
            html.Div([
                html.H4(f"{read_bw + write_bw:.1f} MB/s", style={'color': '#ff7f0e', 'margin': 0}),
                html.P("Total Bandwidth", style={'margin': 0})
            ], className='metric-card bandwidth'),
            
            html.Div([
                html.H4(f"{job.get('read', {}).get('lat_ns', {}).get('mean', 0) / 1000:.1f} μs", style={'color': '#2ca02c', 'margin': 0}),
                html.P("Avg Read Latency", style={'margin': 0})
            ], className='metric-card latency'),
            
            html.Div([
                html.H4(f"{scenario_config['runtime']}s", style={'color': '#d62728', 'margin': 0}),
                html.P("Test Duration", style={'margin': 0})
            ], className='metric-card duration'),
        ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'})
    ])

def create_comprehensive_charts(fio_data, workload_config):
    """Create comprehensive visualization charts"""
    charts = []
    
    # Aggregate data across all jobs
    total_read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    total_write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    total_read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024  # MB/s
    total_write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    
    # 1. IOPS Comparison Chart
    iops_fig = go.Figure(data=[
        go.Bar(
            name='Read IOPS', 
            x=['Read', 'Write'], 
            y=[total_read_iops, total_write_iops],
            marker_color=['#FF6B6B', '#4ECDC4'],
            text=[f'{total_read_iops:.0f}', f'{total_write_iops:.0f}'],
            textposition='auto',
            textfont=dict(size=14, color='white', family='Segoe UI')
        )
    ])
    iops_fig.update_layout(
        title=dict(
            text='📊 IOPS Performance',
            font=dict(size=20, color='#2C3E50', family='Segoe UI'),
            x=0.5
        ),
        yaxis_title='IOPS',
        showlegend=False,
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI', color='#2C3E50'),
        margin=dict(t=60, b=40, l=40, r=40)
    )
    charts.append(html.Div([
        dcc.Graph(figure=iops_fig)
    ], className='chart-container'))
    
    # 2. Bandwidth Chart
    bw_fig = go.Figure(data=[
        go.Bar(
            name='Bandwidth', 
            x=['Read BW', 'Write BW'], 
            y=[total_read_bw, total_write_bw],
            marker_color=['#45B7D1', '#96C93D'],
            text=[f'{total_read_bw:.1f} MB/s', f'{total_write_bw:.1f} MB/s'],
            textposition='auto',
            textfont=dict(size=14, color='white', family='Segoe UI')
        )
    ])
    bw_fig.update_layout(
        title=dict(
            text='🚀 Bandwidth Performance',
            font=dict(size=20, color='#2C3E50', family='Segoe UI'),
            x=0.5
        ),
        yaxis_title='MB/s',
        showlegend=False,
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI', color='#2C3E50'),
        margin=dict(t=60, b=40, l=40, r=40)
    )
    charts.append(html.Div([
        dcc.Graph(figure=bw_fig)
    ], className='chart-container'))
    
    # 3. Latency Distribution (using first job as representative)
    if fio_data['jobs']:
        job = fio_data['jobs'][0]
        
        # Read latency percentiles
        read_percentiles = job['read'].get('clat_ns', {}).get('percentile', {})
        write_percentiles = job['write'].get('clat_ns', {}).get('percentile', {})
        
        if read_percentiles or write_percentiles:
            lat_fig = go.Figure()
            
            if read_percentiles:
                percentiles = [float(p) for p in read_percentiles.keys()]
                read_lats = [v / 1000 for v in read_percentiles.values()]  # Convert to μs
                lat_fig.add_trace(go.Scatter(
                    x=percentiles, y=read_lats, name='Read Latency',
                    mode='lines+markers', 
                    line=dict(color='#FF6B6B', width=3),
                    marker=dict(size=8, color='#FF6B6B'),
                    fill='tonexty' if not write_percentiles else None,
                    fillcolor='rgba(255, 107, 107, 0.1)'
                ))
            
            if write_percentiles:
                percentiles = [float(p) for p in write_percentiles.keys()]
                write_lats = [v / 1000 for v in write_percentiles.values()]  # Convert to μs
                lat_fig.add_trace(go.Scatter(
                    x=percentiles, y=write_lats, name='Write Latency',
                    mode='lines+markers', 
                    line=dict(color='#4ECDC4', width=3),
                    marker=dict(size=8, color='#4ECDC4'),
                    fill='tozeroy',
                    fillcolor='rgba(78, 205, 196, 0.1)'
                ))
            
            lat_fig.update_layout(
                title=dict(
                    text='⚡ Latency Percentiles',
                    font=dict(size=20, color='#2C3E50', family='Segoe UI'),
                    x=0.5
                ),
                xaxis_title='Percentile',
                yaxis_title='Latency (μs)',
                height=400,
                yaxis_type='log',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Segoe UI', color='#2C3E50'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(t=80, b=40, l=40, r=40)
            )
            charts.append(html.Div([
                dcc.Graph(figure=lat_fig)
            ], className='chart-container'))
    
    # 4. Performance Summary Table
    summary_data = []
    for i, job in enumerate(fio_data['jobs']):
        summary_data.append({
            'Job': f"Job {i+1}",
            'Read IOPS': f"{job['read']['iops']:.0f}",
            'Write IOPS': f"{job['write']['iops']:.0f}",
            'Read BW (MB/s)': f"{job['read']['bw'] / 1024:.1f}",
            'Write BW (MB/s)': f"{job['write']['bw'] / 1024:.1f}",
            'Read Lat (μs)': f"{job['read'].get('lat_ns', {}).get('mean', 0) / 1000:.1f}",
            'Write Lat (μs)': f"{job['write'].get('lat_ns', {}).get('mean', 0) / 1000:.1f}",
            'CPU %': f"{job.get('usr_cpu', 0) + job.get('sys_cpu', 0):.1f}"
        })
    
    if summary_data:
        table = dash_table.DataTable(
            data=summary_data,
            columns=[{"name": i, "id": i} for i in summary_data[0].keys()],
            style_cell={
                'textAlign': 'center',
                'fontFamily': 'Segoe UI',
                'fontSize': '14px',
                'padding': '12px'
            },
            style_header={
                'backgroundColor': 'transparent',
                'fontWeight': 'bold',
                'color': 'white',
                'fontSize': '16px'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgba(248, 248, 248, 0.5)'
                }
            ],
            style_data={
                'backgroundColor': 'rgba(255, 255, 255, 0.8)',
                'color': '#2C3E50'
            }
        )
        charts.append(html.Div([
            html.H4("📋 Detailed Job Results"),
            table
        ], className='detailed-table'))
    
    return charts

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
