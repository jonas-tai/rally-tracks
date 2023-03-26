import datetime
from dateutil import parser
import os
import json
import argparse
import numpy as np
import sys

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
                                        if float(time) < 120:
                                            time = 180
                                            hist['fixed_interval'] = f'{time}s'

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

    args = CLI.parse_args()
    main(args)
    

