import zenoh
from zenoh import Zenoh, Value
import sys
import json
import argparse

parser = argparse.ArgumentParser(
    prog='detect_faces',
    description='zenoh face recognition example face detector')
parser.add_argument('-m', '--mode', type=str, choices=['peer', 'client'],
                    help='The zenoh session mode.')
parser.add_argument('-e', '--peer', type=str, metavar='LOCATOR', action='append',
                    help='Peer locators used to initiate the zenoh session.')
parser.add_argument('-l', '--listener', type=str, metavar='LOCATOR', action='append',
                    help='Locators to listen on.')
parser.add_argument('-d', '--dataset', required=True,
                    help='vectors dataset location')
parser.add_argument('-p', '--prefix', type=str, default='/demo/facerecog',
                    help='resources prefix')
parser.add_argument('-c', '--config', type=str, metavar='FILE',
                    help='A zenoh configuration file.')

args = vars(parser.parse_args())
conf = zenoh.config_from_file(args['config']) if args['config'] is not None else {}
for arg in ['mode', 'peer', 'listener']:
    if args[arg] is not None:
        conf[arg] = args[arg] if type(args[arg]) == str else ','.join(args[arg])

f = open(args['dataset'])
faces = json.load(f)

print('[INFO] Open zenoh session...')
zenoh.init_logger()
z = Zenoh(conf)
w = z.workspace()

# If not yet existing, add a memory storage that will store the dataset
storage_admin_path = '/@/router/local/plugin/storages/backend/memory/storage/facerecog-store'
if not w.get(storage_admin_path):
    path_expr = '{}/**'.format(args['prefix'])
    print('Add storage: on {}'.format(path_expr))
    properties = {'path_expr': path_expr}
    w.put(storage_admin_path, properties)

for k, vs in faces.items():
    for j, v in enumerate(vs):
        uri = '{}/vectors/{}/{}'.format(args['prefix'], k, j)
        print('> Inserting face {}'.format(uri))
        w.put(uri, Value.Json(json.dumps(v)))

z.close()

print('[INFO] Done.')
