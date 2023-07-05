import datetime
from dateutil import parser
import os
import json
import argparse
import numpy as np
import sys

from random import choice

# TODO: make better random dates (probably with f strings for numbers)
BEFORE_TIMES = ["2022-01-21T17:52:53.314Z","2022-02-19T12:13:28.314Z","2022-03-30T21:22:58.324Z","2022-04-20T19:28:12.314Z","2022-05-25T16:00:29.324Z","2022-06-17T21:27:58.324Z","2022-01-08T09:03:50.111Z","2022-02-01T02:42:58.324Z","2022-03-14T06:33:21.314Z","2022-04-02T01:01:22.314Z","2022-05-11T09:24:28.314Z","2022-06-09T00:11:12.314Z"]
AFTER_TIMES = ["2022-07-16T12:22:00.314Z","2022-08-21T22:11:50.314Z","2022-09-22T19:21:08.314Z","2022-10-31T12:01:42.314Z","2022-11-21T22:12:34.314Z","2022-12-25T23:21:00.314Z","2022-07-01T02:51:08.314Z","2022-08-04T01:42:23.314Z","2022-09-12T11:49:01.314Z","2022-10-13T04:32:50.314Z","2022-11-02T11:00:11.314Z","2022-07-14T00:21:58.314Z"]

def find_key(item, key):
    keys = []

    if isinstance(item, list):
        for x in item:
            keys += find_key(x, key)
        return keys

    if not isinstance(item, dict):
        return keys

    for k, v in item.items():
        if k == key:
            keys.append(v)
        else:
            keys += find_key(v, key)
    return keys


def main(args):
    if args.multiplier is not None and args.fixed_duration is not None:
        print("Can only have one of multiplier and fixed duration")
        sys.exit(1)
    multiplier = args.multiplier
    outfolder = args.outfolder if args.outfolder is not None else f'custom/{multiplier}'
    original_workflows_dir = 'elastic/logs/workflows'.replace('/', os.sep)
    durations = []

    subdirs = list(os.walk(original_workflows_dir))

    for folder in subdirs[0][1]:
        if folder.startswith('custom'):
            continue
        workflow = list(os.walk(os.path.join(original_workflows_dir, folder)))
        for dirpath, dirnames, filenames in workflow:
            if len(filenames) > 0:
                for filename in filenames:
                    if filename.endswith('.json'):
                        out_path = dirpath.split(os.sep)
                        out_path.insert(3, outfolder)
                        out_path = os.sep.join(out_path)
                        os.makedirs(out_path, exist_ok=True)
                        with open(os.path.join(dirpath, filename), 'r') as fr,  open(os.path.join(out_path, filename), 'w') as fw:
                            requests = json.load(fr)
                            ranges = find_key(requests, 'range')
                            for ts in ranges:
                                if '@timestamp' in ts:
                                    if args.random:
                                        ts['@timestamp']['lte'] = choice(AFTER_TIMES)
                                        ts['@timestamp']['gte'] = choice(BEFORE_TIMES)
                                    else:
                                        lte = parser.parse(ts['@timestamp']['lte'])
                                        gte = parser.parse(ts['@timestamp']['gte'])
                                        
                                        if multiplier is not None:
                                            new_duration = (lte - gte) * multiplier
                                        else:
                                            new_duration = datetime.timedelta(days=args.fixed_duration)
                                        new_end = new_duration + gte
                                        new_value = new_end.isoformat(timespec="milliseconds")
                                        new_value = new_value.replace("+00:00", "Z")

                                        ts['@timestamp']['lte'] = new_value
                                        durations.append(new_duration.total_seconds())

                            histograms = find_key(requests, 'date_histogram')

                            for hist in histograms:
                                if 'fixed_interval' in hist:
                                    if hist['fixed_interval'].endswith('s'):
                                        time = hist['fixed_interval'].strip('s')
                                        if float(time) < args.min_hist_time:
                                            time = args.min_hist_time
                                            hist['fixed_interval'] = f'{time}s'
                                    elif hist['fixed_interval'].endswith('m'):
                                        time = hist['fixed_interval'].strip('m')
                                        if float(time) < args.min_hist_time / 60:
                                            time = args.min_hist_time / 60
                                            hist['fixed_interval'] = f'{time}m'

                            if args.size_min is not None or args.size_max is not None:
                                bodies = find_key(requests, 'body')
                                for body in bodies:
                                    if 'size' in body:
                                            body['size'] = np.clip(body['size'], args.size_min, args.size_max)

                            fw.write(json.dumps(requests, indent=2))
    
    print(f'Min search range: {np.min(durations) / (3600 * 24)}')
    print(f'Max search range: {np.max(durations) / (3600 * 24)}')

    print(f'Median search range: {np.median(durations) / (3600 * 24)}')

if __name__ == '__main__':
    CLI = argparse.ArgumentParser()
    CLI.add_argument('--multiplier', type=int)
    CLI.add_argument('--fixed_duration', type=float)
    CLI.add_argument('--size_min', type=float)
    CLI.add_argument('--size_max', type=float)
    CLI.add_argument('--outfolder', type=str)
    CLI.add_argument('--min_hist_time', type=int, default=300)
    CLI.add_argument('--random', action="store_true", default=False)

    args = CLI.parse_args()
    main(args)
    

