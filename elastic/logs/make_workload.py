from scipy.stats import pareto, zipfian, expon, uniform
import numpy as np
from argparse import ArgumentParser
from collections import defaultdict
import json
import glob
from pathlib import Path
from logs.custom_workflows import find_key
import copy
import datetime
from dateutil import parser
import numpy as np
import uuid
import os
from tqdm.auto import trange, tqdm
import glog

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


def draw_request_size(b, loc, scale, random_state, floor=True, clip=(0, None)):
    draw = pareto.rvs(b, loc=loc, scale=scale, random_state=random_state)
    draw = np.clip(draw, clip[0], clip[1])
    if floor:
        return int(draw)
    else:
        return draw


def draw_request_type(a, n, loc, random_state):
    return zipfian.rvs(a, n, loc=loc, random_state=random_state)


def draw_sleep_time(lda, random_state):
    # setting to scale = 1 / lda is equivalent to rate=lambda
    return expon.rvs(scale=1 / lda, random_state=random_state)


def draw_request_range(lda, random_state):
    return expon.rvs(scale=1 / lda, random_state=random_state)


def draw_load_level(iteration, period, clients, jitter=0, clip=(0, None), random_state=None):
    if jitter > 0:
        # add some jitter to sine wave
        noise = uniform.rvs(loc=-jitter, scale=2 * jitter, random_state=random_state)
    else:
        noise = 0

    # clip it so we don't have too much load or too little (or negative)
    scale = np.clip(
        np.sin(iteration * 2 * np.pi / period) + noise,
        clip[0],
        clip[1]
    )

    return int(np.round(clients * scale))


def import_workflows(in_folder):
    workflows = defaultdict(lambda: [])
    for workflow in ALL_WORKFLOWS:
        globs = glob.glob(str(Path(in_folder, workflow, '*.json')))
        for file in globs:
            with open(file, 'r') as f:
                workflows[workflow].append(json.load(f))
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
            new_value = new_end.isoformat(timespec="milliseconds")
            new_value = new_value.replace("+00:00", "Z")
            # set max time to min time + new duration
            ts['@timestamp']['lte'] = new_value

    bodies = find_key(query, 'body')
    for body in bodies:
        if 'size' in body:
            body['size'] = int(size)
    return query

def copy_sleep(duration):
    sleep_json = copy.deepcopy(SLEEP_TEMPLATE)
    sleep_json['id'] = generate_uuid()
    sleep_json['requests'][0]['stream'][0]['duration'] = duration
    return sleep_json

def main(args):
    out = {i: [] for i in range(args.clients)}

    max_duration = 0

    workflows = import_workflows('logs/workflows')
    # random_state = np.random.RandomState(1)
    random_state = None
    np.random.seed(1)

    for step in trange(args.num_steps, desc='Generating workload'):
        num_clients = draw_load_level(step, 5, args.clients, jitter=0.15, clip=(0.05, 1))
        assert num_clients <= args.clients
        for client in range(num_clients):
            type_idx = draw_request_type(args.zipf, len(ALL_WORKFLOWS), loc=-1, random_state=random_state)
            request_size = draw_request_size(args.pareto, loc=-1, scale=1, random_state=random_state, clip=(0, args.size_max))
            request_range = draw_request_range(args.request_range, random_state=random_state)
            requests_list = [copy_with_date_size(q, request_range, request_size) for q in workflows[ALL_WORKFLOWS[type_idx]]]
            requests_list.append(copy_sleep(draw_sleep_time(args.sleep_lambda, random_state=random_state)))

            out[client] += requests_list
    
        for sleeps in range(num_clients, args.clients):
            out[sleeps].append(copy_sleep(40))

    for k, v in tqdm(out.items(), desc='Writing'):
        current_duration = 0
        out_folder = Path(args.out_folder, f'{k:02}')
        try:
            out_folder.mkdir(parents=True)
        except FileExistsError:
            for fname in glob.glob(str(out_folder.joinpath('*'))):
                os.remove(fname)
        for i, query in enumerate(v):
            with open(out_folder.joinpath(f'{i:03}.json'), 'w') as f:
                f.write(json.dumps(query, indent=2))
            
            if query.get('name', '') == 'Sleep':
                current_duration += query['requests'][0]['stream'][0]['duration']
            else:
                current_duration += 4
        
        max_duration = max(current_duration, max_duration)
    
    glog.info(f'Max duration of workload: {max_duration}')

if __name__ == '__main__':

    cli = ArgumentParser()

    cli.add_argument('--zipf', type=float, default=1.0)
    cli.add_argument('--pareto', type=float, default=0.4)
    cli.add_argument('--size_max', type=int, default=500)
    cli.add_argument('--sleep_lambda', type=float, default=10)
    cli.add_argument('--request_range', type=float, default=15)
    cli.add_argument('--num_steps', type=int, default=50)
    cli.add_argument('--clients', type=int, default=50)
    cli.add_argument('--out_folder', type=str, default='logs/workflows/custom/out')

    args = cli.parse_args()
    main(args)
