import numpy as np
from argparse import ArgumentParser, BooleanOptionalAction
from collections import defaultdict
import json
import glob
from pathlib import Path
from custom_workflows import find_key
from random_vars import LoadLevel, ExponRV, RequestSize, RequestType
import copy
import datetime
from dateutil import parser
import numpy as np
import uuid
import os
from tqdm.auto import trange, tqdm
import glog
import shutil
import matplotlib.pyplot as plt

ALL_WORKFLOWS = ["apache", "kafka", "nginx", "system/auth", "postgresql/overview", "discover/search",
                 "discover/visualize", "system/syslog/dashboard", "system/syslog/lens", "mysql/dashboard", "mysql/lens",
                 "postgresql/duration"]

SLEEP_TEMPLATE = {
    "id": "",
    "name": "Sleep",
    "requests": [
        {
          "stream": [
            {
                "name": "sleep",
                "operation-type": "sleep",
                "duration": 0
            },
          ]
        }
    ]
}


def import_workflows(in_folder):
    workflows = defaultdict(lambda: [])
    for workflow in ALL_WORKFLOWS:
        globs = glob.glob(str(Path(in_folder, workflow, '*.json')))
        for file in globs:
            with open(file, 'r') as f:
                cur = json.load(f)
                cur = fix_histogram(cur)
                workflows[workflow].append(cur)
    return workflows


def round_time(x):
    x = x.replace(minute=0)
    x = x.replace(second=0)
    x = x.replace(microsecond=0)
    return x


def generate_uuid():
    # return as str instead of UUID object for json serialization
    return str(uuid.uuid4())


def copy_with_date_size(query, date_range, size):
    query = copy.deepcopy(query)
    query['id'] = generate_uuid()
    ranges = find_key(query, 'range')
    for ts in ranges:
        if '@timestamp' in ts:
            lte = parser.parse(ts['@timestamp']['lte'])
            gte = parser.parse(ts['@timestamp']['gte'])

            lte = round_time(lte)
            gte = round_time(gte)

            new_duration = datetime.timedelta(days=date_range)
            # add new duration to min time
            new_end = new_duration + gte
            new_end_fmt = new_end.isoformat(timespec="milliseconds")
            new_end_fmt = new_end_fmt.replace("+00:00", "Z")
            # set max time to min time + new duration

            new_start_fmt = gte.isoformat(timespec="milliseconds")
            new_start_fmt = new_start_fmt.replace("+00:00", "Z")

            ts['@timestamp']['gte'] = new_start_fmt
            ts['@timestamp']['lte'] = new_end_fmt

    bodies = find_key(query, 'body')
    for body in bodies:
        if 'size' in body:
            body['size'] = int(size)
    return query

def fix_histogram(query):
    histograms = find_key(query, 'date_histogram')
    min_hist_time = 86400

    for hist in histograms:
        if 'fixed_interval' in hist:
            if hist['fixed_interval'].endswith('s'):
                time = hist['fixed_interval'].strip('s')
                if float(time) < min_hist_time:
                    time = min_hist_time
                    hist['fixed_interval'] = f'{time}s'
            elif hist['fixed_interval'].endswith('m'):
                time = hist['fixed_interval'].strip('m')
                if float(time) < min_hist_time / 60:
                    time = min_hist_time / 60
                    hist['fixed_interval'] = f'{time}m'
    return query


def copy_sleep(duration):
    sleep_json = copy.deepcopy(SLEEP_TEMPLATE)
    sleep_json['id'] = generate_uuid()
    sleep_json['requests'][0]['stream'][0]['duration'] = duration
    return sleep_json


def main(args):
    out = {i: [] for i in range(args.clients)}

    if os.path.exists(args.out_folder):
        shutil.rmtree(args.out_folder)

    max_duration = 0

    workflows = import_workflows('elastic/logs/workflows')
    np.random.seed(args.seed)

    request_type_rv = RequestType(args.zipf, len(workflows))
    request_size_rv = RequestSize(args.pareto, loc=-1, clip=(0, args.size_max))
    load_level_rv = LoadLevel(args.load_period, args.clients, args.load_jitter, clip=(args.min_load, 1))
    between_workflow_sleep_rv = ExponRV(args.sleep_lambda)
    request_range_rv = ExponRV(args.request_range)

    # compute mean idle time by taking mean time spent by workflows
    # on average each request is 4 seconds apart then add 10 
    idle_time = np.sum(np.array([len(x) for x in workflows.values()]) * 4 * request_type_rv.pmf()) + 10

    # generate workloads
    for step in trange(args.num_steps, desc='Generating workload'):
        # draw the amount of load for this time slice
        num_clients = load_level_rv.draw()
        assert num_clients <= args.clients
        for client in range(num_clients):
            # draw the request types and sizes
            type_idx = request_type_rv.draw()
            request_size = request_size_rv.draw()
            request_size = np.clip(request_size * args.size_multiplier, args.size_min, args.size_max)
            request_range = request_range_rv.draw()
            # copy the entire workflow
            requests_list = [copy_with_date_size(q, request_range, request_size) for q in workflows[ALL_WORKFLOWS[type_idx]]]
            requests_list.append(copy_sleep(between_workflow_sleep_rv.draw()))

            out[client] += requests_list

        # the clients that are not adding load will sleep until the next time slice
        for sleeps in range(num_clients, args.clients):
            out[sleeps].append(copy_sleep(idle_time))

    # to determine how many zeros we need to pad the filenames
    num_digits_folders = int(np.ceil(np.log10(args.clients)))
    num_digits_workflows = int(np.ceil(np.log10(max([len(x) for x in out.values()]))))

    for k, v in tqdm(out.items(), desc='Writing workload'):
        current_duration = 0
        out_folder = Path(args.out_folder, f'{k:0{num_digits_folders}}')
        try:
            out_folder.mkdir(parents=True)
        except FileExistsError:
            for fname in glob.glob(str(out_folder.joinpath('*'))):
                os.remove(fname)
        for i, query in enumerate(v):
            with open(out_folder.joinpath(f'{i:0{num_digits_workflows}}.json'), 'w') as f:
                f.write(json.dumps(query, indent=2))

            if query.get('name', '') == 'Sleep':
                current_duration += query['requests'][0]['stream'][0]['duration']
            else:
                current_duration += 4

        max_duration = max(current_duration, max_duration)

    with open(Path(args.out_folder, 'args.json'), 'w') as f:
        f.write(json.dumps(vars(args), indent=2))

    glog.info(f'Max duration of workload: {max_duration:.2f}s ({max_duration / 60:.2f} min)')
    glog.info(f'Workload size: {sum(f.stat().st_size for f in Path(args.out_folder).glob("**/*") if f.is_file()) / 1024**2:.2f} MB')
    glog.info(f'Workload exported to {args.out_folder}')
    plt.plot(np.arange(len(load_level_rv.draws)), np.array(load_level_rv.draws))
    plt.ylim((0,None))
    plt.savefig(Path(args.out_folder, 'load.png'))


if __name__ == '__main__':

    cli = ArgumentParser()

    cli.add_argument('--zipf', type=float, default=1.0)
    cli.add_argument('--pareto', type=float, default=0.6)
    cli.add_argument('--size_min', type=int, default=0)
    cli.add_argument('--size_max', type=int, default=250)
    cli.add_argument('--sleep_lambda', type=float, default=10)
    cli.add_argument('--request_range', type=float, default=10)
    cli.add_argument('--num_steps', type=int, default=33)
    cli.add_argument('--clients', type=int, default=80)
    cli.add_argument('--out_folder', type=str, default='elastic/logs/workflows/custom/out')
    cli.add_argument('--seed', type=int, default=0)
    cli.add_argument('--load_period', type=int, default=10)
    cli.add_argument('--load_jitter', type=float, default=0.25)
    cli.add_argument('--min_load', type=float, default=0.75)
    cli.add_argument('--size_multiplier', type=float, default=1)

    args = cli.parse_args()
    main(args)
