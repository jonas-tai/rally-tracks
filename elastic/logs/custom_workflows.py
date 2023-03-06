import datetime
from dateutil import parser
import os
import json


def find_ranges(item):
    keys = []

    if isinstance(item, list):
        for x in item:
            keys += find_ranges(x)
        return keys

    if not isinstance(item, dict):
        return keys

    for k, v in item.items():
        if k == 'range':
            keys.append(v)
        else:
            keys += find_ranges(v)
    return keys


if __name__ == '__main__':
    multiplier = 30
    outfolder = f'custom_{multiplier}'
    original_workflows_dir = 'elastic/logs/workflows'.replace('/', os.sep)

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
                            ranges = find_ranges(requests)
                            for ts in ranges:
                                if '@timestamp' in ts:
                                    lte = parser.parse(ts['@timestamp']['lte'])
                                    gte = parser.parse(ts['@timestamp']['gte'])

                                    ts['@timestamp']['lte'] = ((lte - gte) * multiplier + gte).isoformat().replace("+00:00", "Z")
                            fw.write(json.dumps(requests, indent=2))

