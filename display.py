from dash import dcc, html, dash_table
import plotly.graph_objs as go
from dash_iconify import DashIconify

def create_layout():
    """Create the main dashboard layout"""
    return html.Div([
        html.Div([
            html.Div([
                html.H1("FlowFIO"),
                html.P("Storage performance benchmarking")
            ], className='header'),
            
            html.Div([
                create_sidebar(),
                
                html.Div([
                    html.Div(id='status'),
                    html.Div(id='charts')
                ], className='main-content')
                
            ], className='layout')
            
        ], className='main-container'),
        
        dcc.Store(id='test-results-store'),
        dcc.Store(id='active-run-store'),
        dcc.Interval(id='log-interval', interval=1000, n_intervals=0)
    ])

def create_sidebar():
    """Create the sidebar with all controls"""
    return html.Div([
        html.Div([
            html.Button([
                DashIconify(icon="mdi:play", style={"marginRight": "8px"}),
                'Run Benchmark'
            ], id='run-button', n_clicks=0, className='run-button'),
        ], className='control-section'),
        
        html.Div([
            html.H3([
                DashIconify(icon="mdi:cog", style={"marginRight": "8px"}),
                "Configuration"
            ]),
            
            html.Label("Test Scenario"),
            dcc.Dropdown(
                id='scenario',
                options=[
                    {'label': 'Instant (5s)', 'value': 'instant'},
                    {'label': 'Quick (30s)', 'value': 'quick'},
                    {'label': 'Standard (60s)', 'value': 'standard'},
                    {'label': 'Long (300s)', 'value': 'long'}
                ],
                value='standard'
            ),
            
            html.Label("Workload Preset"),
            dcc.Dropdown(id='workload_preset', value='oltp'),
            
            html.Label("Storage Type"),
            dcc.Dropdown(id='storage_type', value='nvme_ssd'),
        ], className='control-section'),
        
        html.Div([
            html.H4([
                DashIconify(icon="mdi:tune", style={"marginRight": "6px"}),
                "Advanced"
            ]),
            
            html.Label("Direct I/O"),
            dcc.RadioItems(
                id='direct',
                options=[
                    {'label': 'Yes', 'value': '1'},
                    {'label': 'No', 'value': '0'}
                ],
                value='1'
            ),
            
            html.Label("Block Size"),
            dcc.Dropdown(id='bs', value='4k'),
            
            html.Label("Queue Depth"),
            dcc.Dropdown(id='iodepth', value='32'),
            
            html.Label("Jobs"),
            dcc.Dropdown(id='numjobs', value='4'),
            
            html.Label("File Size"),
            dcc.Input(
                id='size',
                type='text',
                value='1G',
                placeholder='e.g., 1G, 500M'
            ),
        ], className='control-section'),
               
    ], className='sidebar')

def create_status_summary(fio_data, workload_config, scenario_config):
    """Create the status summary display after benchmark completion"""
    job = fio_data['jobs'][0] if fio_data['jobs'] else {}
    
    read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024
    write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    
    return html.Div([
        html.Div([
            html.Div([
                html.H4(f"{read_iops + write_iops:.0f}"),
                html.P("IOPS")
            ], className='metric-card-minimal'),
            
            html.Div([
                html.H4(f"{read_bw + write_bw:.1f}"),
                html.P("MB/s")
            ], className='metric-card-minimal'),
            
            html.Div([
                html.H4(f"{job.get('read', {}).get('lat_ns', {}).get('mean', 0) / 1000:.1f}"),
                html.P("Latency (μs)")
            ], className='metric-card-minimal'),
            
            html.Div([
                html.H4(f"{scenario_config['runtime']}s"),
                html.P("Duration")
            ], className='metric-card-minimal'),
        ], className='metrics-grid'),
        
        html.Div([
            html.H4("Performance Breakdown"),
            create_performance_table(fio_data)
        ], className='detailed-table', style={'marginTop': '24px'})
    ])

def create_performance_table(fio_data):
    """Create the detailed performance breakdown table"""
    summary_data = []
    
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
                'if': {'row_index': 2},
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

def create_running_status(log_content, progress_percent, runtime):
    """Create the running status display with progress bar and formatted logs"""
    lines = log_content.split('\n')
    
    # Extract command from first line
    command = ""
    output_lines = []
    
    for line in lines:
        if line.startswith("Command: "):
            command = line[9:]  # Remove "Command: " prefix
        else:
            output_lines.append(line)
    
    # Format command with line breaks
    if command:
        cmd_parts = command.split(' ')
        formatted_cmd = []
        current_line = ""
        
        for part in cmd_parts:
            if len(current_line + part) > 80:
                formatted_cmd.append(current_line.strip())
                current_line = part + " "
            else:
                current_line += part + " "
        
        if current_line.strip():
            formatted_cmd.append(current_line.strip())
        
        command_display = html.Div([
            html.H4("Running Command:", style={"color": "#10b981", "marginBottom": "8px"}),
            html.Pre('\n'.join(formatted_cmd), style={
                "fontFamily": "monospace",
                "fontSize": "11px",
                "color": "#fafafa",
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
                "padding": "12px",
                "borderRadius": "4px",
                "marginBottom": "16px",
                "whiteSpace": "pre-wrap"
            })
        ])
    else:
        command_display = html.Div()
    
    # Calculate remaining time
    remaining_seconds = max(0, runtime - (progress_percent / 100) * runtime)
    remaining_minutes = int(remaining_seconds // 60)
    remaining_secs = int(remaining_seconds % 60)
    
    if remaining_minutes > 0:
        time_remaining = f"{remaining_minutes}m {remaining_secs}s"
    else:
        time_remaining = f"{remaining_secs}s"
    
    # Progress bar
    progress_bar = html.Div([
        html.Div([
            html.Div([
                html.Div([
                    DashIconify(icon="mdi:loading", className="spin", style={"marginRight": "8px"}),
                    f"Running benchmark... ({progress_percent:.1f}% complete, {time_remaining} remaining)"
                ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px", "color": "#10b981"}),
                html.Div([
                    html.Div(style={
                        "width": f"{progress_percent}%",
                        "height": "4px",
                        "backgroundColor": "#10b981",
                        "borderRadius": "2px",
                        "transition": "width 0.3s ease"
                    })
                ], style={
                    "width": "100%",
                    "height": "4px",
                    "backgroundColor": "rgba(113, 113, 122, 0.3)",
                    "borderRadius": "2px",
                    "overflow": "hidden"
                })
            ])
        ], style={"marginBottom": "16px"})
    ])
    
    # Format output logs
    output_content = '\n'.join(output_lines[-10:])  # Last 10 lines
    if output_content.strip():
        log_display = html.Div([
            html.H4("Live Output:", style={"color": "#fafafa", "marginBottom": "8px"}),
            html.Pre(output_content, style={
                "fontFamily": "monospace",
                "fontSize": "11px",
                "color": "#a1a1aa",
                "backgroundColor": "rgba(0, 0, 0, 0.3)",
                "padding": "12px",
                "borderRadius": "4px",
                "whiteSpace": "pre-wrap",
                "maxHeight": "200px",
                "overflowY": "auto"
            })
        ])
    else:
        log_display = html.Div()
    
    return html.Div([
        command_display,
        progress_bar,
        log_display
    ])

def create_error_status(error_message):
    """Create error status display"""
    return html.Div([
        html.Div([
            DashIconify(icon="mdi:alert-circle", style={"marginRight": "8px", "color": "#ef4444"}),
            "Error reading FIO results"
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px", "color": "#ef4444"}),
        html.Pre(error_message, style={
            "fontFamily": "monospace",
            "fontSize": "11px",
            "color": "#fca5a5",
            "backgroundColor": "rgba(239, 68, 68, 0.1)",
            "padding": "12px",
            "borderRadius": "4px",
            "whiteSpace": "pre-wrap"
        })
    ], className="status-error")

def create_comprehensive_charts(fio_data, workload_config):
    """Create all performance charts"""
    charts = []
    
    total_read_iops = sum(j['read']['iops'] for j in fio_data['jobs'])
    total_write_iops = sum(j['write']['iops'] for j in fio_data['jobs'])
    total_read_bw = sum(j['read']['bw'] for j in fio_data['jobs']) / 1024
    total_write_bw = sum(j['write']['bw'] for j in fio_data['jobs']) / 1024
    
    charts_row1 = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_iops_chart(total_read_iops, total_write_iops),
                style={'height': '300px'}
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(
                figure=create_bandwidth_chart(total_read_bw, total_write_bw),
                style={'height': '300px'}
            )
        ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
    ], className='chart-container')
    
    charts.append(charts_row1)
    
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
    """Create IOPS bar chart"""
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
    """Create bandwidth bar chart"""
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
        read_lats = [v / 1000 for v in read_percentiles.values()]
        fig.add_trace(go.Scatter(
            x=percentiles, y=read_lats, name='Read',
            mode='lines+markers', 
            line=dict(color='#fafafa', width=2),
            marker=dict(size=4, color='#fafafa')
        ))
    
    if write_percentiles:
        percentiles = [float(p) for p in write_percentiles.keys()]
        write_lats = [v / 1000 for v in write_percentiles.values()]
        fig.add_trace(go.Scatter(
            x=percentiles, y=write_lats, name='Write',
            mode='lines+markers', 
            line=dict(color='#71717a', width=2),
            marker=dict(size=4, color='#71717a')
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
        margin=dict(t=60, b=40, l=50, r=40),
        xaxis=dict(
            gridcolor='rgba(113, 113, 122, 0.1)',
            gridwidth=1
        ),
        yaxis=dict(
            gridcolor='rgba(113, 113, 122, 0.1)',
            gridwidth=1
        )
    )
    return fig