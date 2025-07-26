import dash
from dash import Input, Output, State, no_update
import json
import subprocess
import os
import yaml
from datetime import datetime
import threading, time, signal, psutil

from display import (
    create_layout, 
    create_status_summary, 
    create_comprehensive_charts,
    create_running_status,
    create_error_status
)

running_processes = {}

with open('fio_defaults.yaml', 'r') as f:
    config = yaml.safe_load(f)

app = dash.Dash(__name__)

with open('app.html', 'r') as f:
    app.index_string = f.read()

app.layout = create_layout()

@app.callback(
    [Output('bs', 'value'), Output('iodepth', 'value'), Output('numjobs', 'value')],
    [Input('workload_preset', 'value'), Input('storage_type', 'value')]
)
def update_settings_from_preset(workload_preset, storage_type):
    if workload_preset and workload_preset in config['workloads']:
        workload = config['workloads'][workload_preset]
        bs = workload.get('bs', '4k')
        iodepth = str(workload.get('iodepth', 32))
        numjobs = str(workload.get('numjobs', 4))
        
        if storage_type and storage_type in config['storage_types']:
            storage = config['storage_types'][storage_type]
            iodepth = str(storage.get('recommended_iodepth', iodepth))
            numjobs = str(storage.get('recommended_numjobs', numjobs))
            
        return bs, iodepth, numjobs
    
    return '4k', '32', '4'

@app.callback([Output('size', 'value')], [Input('scenario', 'value')])
def update_size_from_scenario(scenario):
    if scenario and scenario in config['scenarios']:
        return [config['scenarios'][scenario]['size']]
    return ['1G']

@app.callback(Output('workload_preset', 'options'), Input('workload_preset', 'id'))
def populate_workload_options(_):
    return [{'label': v['name'], 'value': k} for k, v in config['workloads'].items()]

@app.callback(Output('storage_type', 'options'), Input('storage_type', 'id'))
def populate_storage_options(_):
    return [{'label': v['name'], 'value': k} for k, v in config['storage_types'].items()]

@app.callback(Output('bs', 'options'), Input('bs', 'id'))
def populate_bs_options(_):
    return [{'label': bs, 'value': bs} for bs in config['block_sizes']]

@app.callback(Output('iodepth', 'options'), Input('iodepth', 'id'))
def populate_iodepth_options(_):
    return [{'label': str(qd), 'value': str(qd)} for qd in config['queue_depths']]

@app.callback(Output('numjobs', 'options'), Input('numjobs', 'id'))
def populate_numjobs_options(_):
    return [{'label': str(nj), 'value': str(nj)} for nj in config['job_counts']]

@app.callback(
    Output('active-run-store', 'data'),
    [Input('run-button', 'n_clicks')],
    [State('scenario', 'value'), State('workload_preset', 'value'), State('direct', 'value'),
     State('bs', 'value'), State('numjobs', 'value'), State('iodepth', 'value'), State('size', 'value')]
)
def run_fio_test(n_clicks, scenario, workload_preset, direct, bs, numjobs, iodepth, size):
    if n_clicks == 0:
        return no_update
    
    os.makedirs('/app/test-data', exist_ok=True)
    
    scenario_config = config['scenarios'].get(scenario, config['scenarios']['standard'])
    workload_config = config['workloads'].get(workload_preset, config['workloads']['oltp'])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'/app/test-data/results_{timestamp}.json'
    log_file = f'/app/test-data/log_{timestamp}.txt'
    
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
    
    if 'rw' in rw and rwmixread < 100:
        fio_cmd.append(f'--rwmixread={rwmixread}')
    
    cmd_str = ' '.join(fio_cmd)
    print(f"Running FIO command: {cmd_str}", flush=True)

    with open(log_file, "w") as lf:
        lf.write(f"Command: {cmd_str}\n\n")
        lf.flush()
        process = subprocess.Popen(fio_cmd, stdout=lf, stderr=lf, text=True)

    running_processes[timestamp] = {
        "process": process,
        "output_file": output_file,
        "log_file": log_file,
        "scenario_config": scenario_config,
        "workload_config": workload_config,
        "start_time": datetime.now(),
        "runtime": scenario_config["runtime"]
    }

    return {"run_id": timestamp, "log_file": log_file}

@app.callback(
    [Output('status', 'children'), Output('charts', 'children'), 
     Output('test-results-store', 'data'), Output('active-run-store', 'clear_data')],
    [Input('log-interval', 'n_intervals')],
    [State('active-run-store', 'data')]
)
def monitor_test_progress(n, active_run):
    if not active_run:
        return no_update, no_update, no_update, no_update

    run_id = active_run.get('run_id')
    log_file = active_run.get('log_file')

    proc_info = running_processes.get(run_id)
    if not proc_info:
        return no_update, no_update, no_update, no_update

    process = proc_info['process']

    try:
        with open(log_file, 'r') as lf:
            lines = lf.readlines()[-15:]
        log_content = ''.join(lines)
    except Exception:
        log_content = "Collecting logs..."

    if process.poll() is None:
        start_time = proc_info['start_time']
        runtime = proc_info['runtime']
        elapsed = (datetime.now() - start_time).total_seconds()
        progress_percent = min((elapsed / runtime) * 100, 100)
        
        return create_running_status(log_content, progress_percent, runtime), no_update, no_update, no_update
    else:
        output_file = proc_info['output_file']
        scenario_config = proc_info['scenario_config']
        workload_config = proc_info['workload_config']

        try:
            with open(output_file, 'r') as f:
                fio_data = json.load(f)
            
            charts = create_comprehensive_charts(fio_data, workload_config)
            summary = create_status_summary(fio_data, workload_config, scenario_config)
            
            running_processes.pop(run_id, None)
            return summary, charts, fio_data, True
            
        except Exception as e:
            running_processes.pop(run_id, None)
            return create_error_status(str(e)), "", {}, True

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)