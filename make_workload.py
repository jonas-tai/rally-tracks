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
from dataclasses import dataclass, field


@dataclass
class ClientRequestList:
    requests: list[dict] = field(default_factory=list)
    workflow_index: int | None = None
    request_index: int = 0
    request_size: float | None = None
    request_range: float | None = None

    def get_next(self, workflows: dict, request_type_rv: RequestType, request_size_rv: RequestSize | None, request_range_rv: ExponRV | None, size_max: int, draw_size_zero: bool):
        if self.request_size is None and request_size_rv is not None:
            self.request_size = request_size_rv.draw()
        if self.request_range is None and request_range_rv is not None:
            self.request_range = request_range_rv.draw()
        if self.workflow_index is None:
            self.workflow_index = request_type_rv.draw()

        requests_lists_for_workflow = workflows[ALL_WORKFLOWS[self.workflow_index]]

        if self.request_index >= len(requests_lists_for_workflow):
            self.request_index = 0
            self.workflow_index = request_type_rv.draw()
            if request_range_rv is not None:
                self.request_range = request_range_rv.draw()
            if request_size_rv is not None:
                self.request_size = request_size_rv.draw()

            requests_lists_for_workflow = workflows[ALL_WORKFLOWS[self.workflow_index]]

        new_request = requests_lists_for_workflow[self.request_index]
        self.request_index += 1
        self.requests.append(copy_with_date_size(new_request, self.request_range,
                             self.request_size, size_max, draw_size_zero))

    def append_sleep(self, t: float):
        self.requests.append(copy_sleep(t))


BETWEEN_REQUEST_TIME = 4

ALL_WORKFLOWS = ["apache", "kafka", "system/auth", "postgresql/overview", "discover/search",
                 "discover/visualize", "system/syslog/dashboard", "system/syslog/lens", "mysql/dashboard", "mysql/lens",
                 "postgresql/duration", "nginx"]

SLEEP_INNER = {
    "name": "sleep",
    "operation-type": "sleep",
    "duration": 0
}

SLEEP_TEMPLATE = {
    "id": "",
    "name": "Sleep",
    "requests": [
        {
          "stream": [
              SLEEP_INNER
          ]
        }
    ]
}


def import_workflows(in_folder, num_workflows):
    if num_workflows == 0:
        workflow_list = ALL_WORKFLOWS
    else:
        workflow_list = ALL_WORKFLOWS[:num_workflows]
    workflows = defaultdict(lambda: [])
    for workflow in workflow_list:
        globs = glob.glob(str(Path(in_folder, workflow, '*.json')))
        for file in globs:
            with open(file, 'r') as f:
                cur = json.load(f)
                cur = fix_histogram(cur)
                # cur = clean_request(cur)
                # cur = fix_timeouts(cur)
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


def generate_id(iter_num, orig_id, wf_id):
    return f'{iter_num}.{wf_id} {orig_id}'


def copy_with_date_size(query, date_range, size, size_max, draw_size_zero):
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
            if size is None:
                body['size'] = int(min(body['size'], size_max))
            elif draw_size_zero and body['size'] == 0:
                body['size'] = int(min(size, size_max))
            else:
                body['size'] = int(min(size, body['size'], size_max))
    return query


def fix_histogram(query):
    histograms = find_key(query, 'date_histogram')
    min_hist_time = 60 * 60 * 24

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

# def clean_request(query):
#     query['requests'] = query['requests'][:1]
#     return query

# def fix_timeouts(query):
#     return query


def copy_sleep(duration):
    sleep_json = copy.deepcopy(SLEEP_TEMPLATE)
    sleep_json['id'] = generate_uuid()
    sleep_json['requests'][0]['stream'][0]['duration'] = duration
    return sleep_json


def append_sleep_to_json(query, duration):
    sleep_json = copy.deepcopy(SLEEP_INNER)
    sleep_json['duration'] = duration
    requests_list = query['requests']

    if 'stream' in requests_list[-1]:
        requests_list[-1]['stream'].append(sleep_json)
    else:
        req = requests_list[-1]
        requests_list[-1] = {'stream': [req, sleep_json]}
    return query


def main(args):
    if args.target_clients is None:
        args.target_clients = args.clients

    out = {i: ClientRequestList() for i in range(args.target_clients)}

    if os.path.exists(args.out_folder) and 'n' in args.mode:
        shutil.rmtree(args.out_folder)

    max_duration = 0

    workflows = import_workflows('elastic/logs/workflows', args.num_workflow_types)
    np.random.seed(args.seed)

    request_type_rv = RequestType(args.zipf, len(workflows))
    if args.draw_size:
        request_size_rv = RequestSize(args.pareto, loc=-1, clip=(0, args.size_max))
    else:
        request_size_rv = None
    load_level_rv = LoadLevel(args.load_period, args.clients, args.load_jitter, args.mean_load, clip=(args.min_load, 1))
    request_range_rv = ExponRV(args.request_range)

    # generate workloads
    for step in trange(0, args.max_workload_time, BETWEEN_REQUEST_TIME, desc='Generating workload'):
        # draw the amount of load for this time slice
        num_clients = load_level_rv.draw()
        assert num_clients <= args.clients
        for client in range(num_clients):
            out[client].get_next(workflows, request_type_rv, request_size_rv, request_range_rv, args.size_max, args.draw_size_zero)

        # the clients that are not adding load will sleep until the next time slice
        for sleeps in range(num_clients, args.target_clients):
            out[sleeps].append_sleep(BETWEEN_REQUEST_TIME)

    # to determine how many zeros we need to pad the filenames
    num_digits_folders = int(np.ceil(np.log10(args.target_clients)))
    num_digits_workflows = int(np.ceil(np.log10(max([len(x.requests) for x in out.values()]))))

    for k, client in tqdm(out.items(), desc='Writing workload'):
        current_duration = 0
        out_folder = Path(args.out_folder, f'{k:0{num_digits_folders}}')
        idx_max = None
        for i, query in enumerate(client.requests):
            if query.get('name', '') == 'Sleep':
                current_duration += query['requests'][0]['stream'][0]['duration']
            elif query['requests'][-1].get('name') == 'sleep':
                current_duration += query['requests'][-1]['duration']
            else:
                current_duration += 4
            # if we have a maximum workload time, set the maximum time here so that we stop writing later
            if args.max_workload_time > 0 and current_duration > args.max_workload_time:
                idx_max = i
                break
        # sleep forever at end
        if 'e' in args.mode:
            append_sleep_to_json(client.requests[-1], 600)
        try:
            out_folder.mkdir(parents=True)
        except FileExistsError:
            if 'n' in args.mode:
                for fname in glob.glob(str(out_folder.joinpath('*'))):
                    os.remove(fname)
        out_folder_offset = len(list(out_folder.glob('*')))

        # only iterate to idx_max
        for i, query in enumerate(client.requests[:idx_max]):
            with open(out_folder.joinpath(f'{i + out_folder_offset:0{num_digits_workflows}}.json'), 'w') as f:
                f.write(json.dumps(query, indent=2))

        max_duration = max(current_duration, max_duration)

    with open(Path(args.out_folder, 'args.json'), 'w') as f:
        f.write(json.dumps(vars(args), indent=2))

    glog.info(f'Max duration of workload: {max_duration:.2f}s ({max_duration / 60:.2f} min)')
    glog.info(
        f'Workload size: {sum(f.stat().st_size for f in Path(args.out_folder).glob("**/*") if f.is_file()) / 1024**2:.2f} MB')
    glog.info(f'Workload exported to {args.out_folder}')
    plt.plot(np.arange(len(load_level_rv.draws)), np.array(load_level_rv.draws))
    plt.ylim((0, None))
    plt.savefig(Path(args.out_folder, 'load.png'))


if __name__ == '__main__':

    cli = ArgumentParser()

    cli.add_argument('--zipf', type=float, default=1.0)
    cli.add_argument('--pareto', type=float, default=0.6)
    cli.add_argument('--size_min', type=int, default=0)
    cli.add_argument('--size_max', type=int, default=250)
    cli.add_argument('--sleep_lambda', type=float, default=4)
    cli.add_argument('--request_range', type=float, default=10)
    cli.add_argument('--clients', type=int, default=80)
    cli.add_argument('--out_folder', type=str, default='elastic/logs/workflows/custom/out')
    cli.add_argument('--seed', type=int, default=0)
    cli.add_argument('--load_period', type=int, default=10)
    cli.add_argument('--load_jitter', type=float, default=0.0)
    cli.add_argument('--min_load', type=float, default=0.75)
    cli.add_argument('--size_multiplier', type=float, default=1)
    cli.add_argument('--draw_size', type=bool, default=True)
    cli.add_argument('--mean_load', type=float, default=0.8)
    cli.add_argument('--num_workflow_types', type=int, default=0)
    cli.add_argument('--mode', type=str, default='e', help='Specify n for new workload,\
                      e to end current workload, do not use either to chain workloads on top,\
                      e.g., make first workload using n then make next ones without any parameter, then finish with e')
    cli.add_argument('--max_workload_time', type=int, default=600)
    cli.add_argument('--target_clients', type=int, default=None)
    cli.add_argument('--draw_size_zero', action='store_true', default=False)

    args = cli.parse_args()
    main(args)
