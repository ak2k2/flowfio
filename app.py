import dash
from dash import dcc, html, Input, Output, State, dash_table, no_update
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import subprocess
import os
import yaml
from datetime import datetime
import numpy as np
import threading, time, signal, psutil

# Global store for running FIO processes {run_id: Popen}
running_processes = {}

# Load configuration
with open('fio_defaults.yaml', 'r') as f:
    config = yaml.safe_load(f)

app = dash.Dash(__name__)

with open('app.html', 'r') as f:
    app.index_string = f.read()

app.layout = html.Div([
    html.Div([
        # Header
        html.Div([
            html.H1("FlowFIO"),
            html.P("Storage performance benchmarking")
        ], className='header'),
        
        # Main Layout
        html.Div([
            # Sidebar
            html.Div([
                html.Div([
                    html.H3("Test Configuration"),
                    
                    html.Label("Test Scenario"),
                    dcc.Dropdown(
                        id='scenario',
                        options=[
                            {'label': 'Instant (5s)', 'value': 'instant'},
                            {'label': 'Quick (30s)', 'value': 'quick'},
                            {'label': 'Standard (60s)', 'value': 'standard'},
                            {'label': 'Enterprise (300s)', 'value': 'enterprise'}
                        ],
                        value='standard'
                    ),
                    
                    html.Label("Workload Preset"),
                    dcc.Dropdown(
                        id='workload_preset',
                        options=[
                            {'label': v['name'], 'value': k} 
                            for k, v in config['workloads'].items()
                        ],
                        value='oltp'
                    ),
                    
                    html.Label("Storage Type"),
                    dcc.Dropdown(
                        id='storage_type',
                        options=[
                            {'label': v['name'], 'value': k}
                            for k, v in config['storage_types'].items()
                        ],
                        value='nvme_ssd'
                    ),
                ], className='control-section'),
                
                html.Div([
                    html.H4("Advanced Settings"),
                    
                    html.Label("Direct I/O"),
                    dcc.RadioItems(
                        id='direct',
                        options=[
                            {'label': 'Yes (recommended)', 'value': '1'},
                            {'label': 'No', 'value': '0'}
                        ],
                        value='1'
                    ),
                    
                    html.Label("Block Size"),
                    dcc.Dropdown(
                        id='bs',
                        options=[{'label': bs, 'value': bs} for bs in config['block_sizes']],
                        value='4k'
                    ),
                    
                    html.Label("Queue Depth"),
                    dcc.Dropdown(
                        id='iodepth',
                        options=[{'label': str(qd), 'value': str(qd)} for qd in config['queue_depths']],
                        value='32'
                    ),
                    
                    html.Label("Number of Jobs"),
                    dcc.Dropdown(
                        id='numjobs',
                        options=[{'label': str(nj), 'value': str(nj)} for nj in config['job_counts']],
                        value='4'
                    ),
                    
                    html.Label("Test File Size"),
                    dcc.Input(
                        id='size',
                        type='text',
                        value='1G',
                        placeholder='e.g., 1G, 500M, 2048M'
                    ),
                ], className='control-section'),
                
                html.Div([
                    html.Button('Run Benchmark', id='run-button', n_clicks=0, className='run-button'),
                ], className='control-section'),
                       
            ], className='sidebar'),
            
            # Main Content
            html.Div([
                html.Div(id='status'),
                html.Div(id='charts')
            ], className='main-content')
            
        ], className='layout')
        
    ], className='main-container'),
    
    # Store for test results
    dcc.Store(id='test-results-store'),
    dcc.Store(id='active-run-store'),  # holds current run_id and log path
    dcc.Interval(id='log-interval', interval=1000, n_intervals=0)
])

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

# -------------------- RUN BUTTON CALLBACK --------------------
# When button clicked, start FIO in a separate thread / process and immediately return run_id & log path

@app.callback(
    Output('active-run-store', 'data'),
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
        return no_update
    
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

    # Create log file for live tailing
    log_file = f"/app/test-data/log_{timestamp}.txt"

    # Start FIO asynchronously
    with open(log_file, "w") as lf:
        process = subprocess.Popen(fio_cmd, stdout=lf, stderr=lf, text=True)

    running_processes[timestamp] = {
        "process": process,
        "output_file": output_file,
        "log_file": log_file,
        "scenario_config": scenario_config,
        "workload_config": workload_config
    }

    # Return immediate status, charts empty, store active run info
    active_run = {"run_id": timestamp, "log_file": log_file}
    return active_run


# -------------------- LOG STREAMING CALLBACK --------------------
# This callback fires every second to update the status div with latest log lines.

@app.callback(
    [Output('status', 'children'), Output('charts', 'children'), Output('test-results-store', 'data'), Output('active-run-store', 'clear_data')],
    [Input('log-interval', 'n_intervals')],
    [State('active-run-store', 'data')]
)
def stream_logs(n, active_run):
    if not active_run:
        # No active run
        return no_update, no_update, no_update, no_update

    run_id = active_run.get('run_id')
    log_file = active_run.get('log_file')

    proc_info = running_processes.get(run_id)
    if not proc_info:
        return no_update, no_update, no_update, no_update

    process = proc_info['process']

    # Read last 15 lines of log file
    try:
        with open(log_file, 'r') as lf:
            lines = lf.readlines()[-15:]
        log_pre = html.Pre(''.join(lines), style={"fontSize": "12px", "whiteSpace": "pre-wrap"})
    except Exception:
        log_pre = "Collecting logs..."

    if process.poll() is None:
        # Still running
        status_div = html.Div([
            html.Div("Running FIO benchmark...", className="status-success"),
            log_pre
        ])
        return status_div, no_update, no_update, no_update
    else:
        # Completed
        output_file = proc_info['output_file']
        scenario_config = proc_info['scenario_config']
        workload_config = proc_info['workload_config']

        try:
            with open(output_file, 'r') as f:
                fio_data = json.load(f)
            charts = create_comprehensive_charts(fio_data, workload_config)
            summary = create_status_summary(fio_data, workload_config, scenario_config)
            # cleanup
            running_processes.pop(run_id, None)
            status_done = html.Div([html.Div("FIO Test Completed", className="status-success"), summary])
            return status_done, charts, fio_data, True
        except Exception as e:
            err_div = html.Div(f"Error reading FIO results: {str(e)}", className="status-error")
            running_processes.pop(run_id, None)
            return err_div, "", {}, True

def create_status_summary(fio_data, workload_config, scenario_config):
    """Create a status summary card"""
    job = fio_data['jobs'][0] if fio_data['jobs'] else {}
    
    read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024  # Convert to MB/s
    write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    
    return html.Div([
        # Key Metrics Row
        html.Div([
            html.Div([
                html.H4(f"{read_iops + write_iops:.0f}"),
                html.P("Total IOPS")
            ], className='metric-card iops'),
            
            html.Div([
                html.H4(f"{read_bw + write_bw:.1f}"),
                html.P("Total Bandwidth (MB/s)")
            ], className='metric-card bandwidth'),
            
            html.Div([
                html.H4(f"{job.get('read', {}).get('lat_ns', {}).get('mean', 0) / 1000:.1f}"),
                html.P("Avg Read Latency (μs)")
            ], className='metric-card latency'),
            
            html.Div([
                html.H4(f"{scenario_config['runtime']}"),
                html.P("Test Duration (s)")
            ], className='metric-card duration'),
        ], className='metrics-grid'),
        
        # Detailed Performance Table
        html.Div([
            html.H4("📊 Performance Breakdown"),
            create_performance_table(fio_data)
        ], className='detailed-table', style={'marginTop': '24px'})
    ])

def create_performance_table(fio_data):
    """Create a compact performance breakdown table"""
    summary_data = []
    
    # Aggregate totals
    total_read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    total_write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    total_read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024
    total_write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    avg_read_lat = sum(j['read'].get('lat_ns', {}).get('mean', 0) for j in fio_data['jobs']) / len(fio_data['jobs']) / 1000
    avg_write_lat = sum(j['write'].get('lat_ns', {}).get('mean', 0) for j in fio_data['jobs']) / len(fio_data['jobs']) / 1000
    
    summary_data.append({
        'Metric': 'Read',
        'IOPS': f"{total_read_iops:.0f}",
        'Bandwidth (MB/s)': f"{total_read_bw:.1f}",
        'Avg Latency (μs)': f"{avg_read_lat:.1f}",
        'P95 Latency (μs)': f"{fio_data['jobs'][0]['read'].get('clat_ns', {}).get('percentile', {}).get('95.000000', 0) / 1000:.1f}" if fio_data['jobs'] else "0",
        'P99 Latency (μs)': f"{fio_data['jobs'][0]['read'].get('clat_ns', {}).get('percentile', {}).get('99.000000', 0) / 1000:.1f}" if fio_data['jobs'] else "0"
    })
    
    summary_data.append({
        'Metric': 'Write',
        'IOPS': f"{total_write_iops:.0f}",
        'Bandwidth (MB/s)': f"{total_write_bw:.1f}",
        'Avg Latency (μs)': f"{avg_write_lat:.1f}",
        'P95 Latency (μs)': f"{fio_data['jobs'][0]['write'].get('clat_ns', {}).get('percentile', {}).get('95.000000', 0) / 1000:.1f}" if fio_data['jobs'] else "0",
        'P99 Latency (μs)': f"{fio_data['jobs'][0]['write'].get('clat_ns', {}).get('percentile', {}).get('99.000000', 0) / 1000:.1f}" if fio_data['jobs'] else "0"
    })
    
    summary_data.append({
        'Metric': 'Total',
        'IOPS': f"{total_read_iops + total_write_iops:.0f}",
        'Bandwidth (MB/s)': f"{total_read_bw + total_write_bw:.1f}",
        'Avg Latency (μs)': f"{(avg_read_lat + avg_write_lat) / 2:.1f}",
        'P95 Latency (μs)': "-",
        'P99 Latency (μs)': "-"
    })
    
    return dash_table.DataTable(
        data=summary_data,
        columns=[{"name": i, "id": i} for i in summary_data[0].keys()],
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'Segoe UI',
            'fontSize': '13px',
            'padding': '8px'
        },
        style_header={
            'backgroundColor': 'transparent',
            'fontWeight': 'bold',
            'color': 'white',
            'fontSize': '14px'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 2},  # Total row
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgba(248, 248, 248, 0.03)'
            }
        ],
        style_data={
            'backgroundColor': 'rgba(255, 255, 255, 0.05)',
            'color': '#fafafa'
        }
    )

def create_comprehensive_charts(fio_data, workload_config):
    """Create comprehensive visualization charts"""
    charts = []
    
    # Aggregate data across all jobs
    total_read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    total_write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    total_read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024  # MB/s
    total_write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    
    # Create a 2x2 grid of compact charts
    charts_row1 = html.Div([
        # IOPS Chart (left)
        html.Div([
            dcc.Graph(
                figure=create_iops_chart(total_read_iops, total_write_iops),
                style={'height': '300px'}
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        # Bandwidth Chart (right)
        html.Div([
            dcc.Graph(
                figure=create_bandwidth_chart(total_read_bw, total_write_bw),
                style={'height': '300px'}
            )
        ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
    ], className='chart-container')
    
    charts.append(charts_row1)
    
    # Latency chart full width
    if fio_data['jobs']:
        lat_chart = html.Div([
            dcc.Graph(
                figure=create_latency_chart(fio_data['jobs'][0]),
                style={'height': '350px'}
            )
        ], className='chart-container')
        charts.append(lat_chart)
    
    return charts

def create_iops_chart(read_iops, write_iops):
    """Create compact IOPS chart"""
    fig = go.Figure(data=[
        go.Bar(
            x=['Read', 'Write'], 
            y=[read_iops, write_iops],
            marker_color=['#10b981', '#3b82f6'],
            text=[f'{read_iops:.0f}', f'{write_iops:.0f}'],
            textposition='auto',
            textfont=dict(size=12, color='white')
        )
    ])
    fig.update_layout(
        title=dict(text='IOPS', font=dict(size=16, color='#fafafa'), x=0.5),
        yaxis_title='IOPS',
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI', color='#fafafa', size=11),
        margin=dict(t=40, b=30, l=40, r=20)
    )
    return fig

def create_bandwidth_chart(read_bw, write_bw):
    """Create compact bandwidth chart"""
    fig = go.Figure(data=[
        go.Bar(
            x=['Read', 'Write'], 
            y=[read_bw, write_bw],
            marker_color=['#3b82f6', '#8b5cf6'],
            text=[f'{read_bw:.1f}', f'{write_bw:.1f}'],
            textposition='auto',
            textfont=dict(size=12, color='white')
        )
    ])
    fig.update_layout(
        title=dict(text='Bandwidth (MB/s)', font=dict(size=16, color='#fafafa'), x=0.5),
        yaxis_title='MB/s',
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI', color='#fafafa', size=11),
        margin=dict(t=40, b=30, l=40, r=20)
    )
    return fig

def create_latency_chart(job):
    """Create latency percentile chart"""
    read_percentiles = job['read'].get('clat_ns', {}).get('percentile', {})
    write_percentiles = job['write'].get('clat_ns', {}).get('percentile', {})
    
    fig = go.Figure()
    
    if read_percentiles:
        percentiles = [float(p) for p in read_percentiles.keys()]
        read_lats = [v / 1000 for v in read_percentiles.values()]  # Convert to μs
        fig.add_trace(go.Scatter(
            x=percentiles, y=read_lats, name='Read',
            mode='lines+markers', 
            line=dict(color='#10b981', width=2),
            marker=dict(size=4, color='#10b981')
        ))
    
    if write_percentiles:
        percentiles = [float(p) for p in write_percentiles.keys()]
        write_lats = [v / 1000 for v in write_percentiles.values()]  # Convert to μs
        fig.add_trace(go.Scatter(
            x=percentiles, y=write_lats, name='Write',
            mode='lines+markers', 
            line=dict(color='#3b82f6', width=2),
            marker=dict(size=4, color='#3b82f6')
        ))
    
    fig.update_layout(
        title=dict(text='Latency Percentiles', font=dict(size=16, color='#fafafa'), x=0.5),
        xaxis_title='Percentile',
        yaxis_title='Latency (μs)',
        yaxis_type='log',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI', color='#fafafa', size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40, l=50, r=40)
    )
    return fig

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
