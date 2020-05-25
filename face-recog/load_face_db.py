from zenoh import Zenoh
from zenoh import Encoding
from zenoh import Value
import sys
import json
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("-z", "--zenoh", type=str, default="127.0.0.1",
                help="location of the ZENOH router")
ap.add_argument("-d", "--dataset", required=True,
                help="vectors dataset location")
ap.add_argument("-p", "--prefix", type=str, default="/demo/facerecog",
                help="resources prefix")
args = vars(ap.parse_args())


def main(face_db):
    locator = args['zenoh']
    z = Zenoh.login(locator)

    # If not yet existing, add a memory storage that will store the dataset
    storage_id = 'facerecog-store'
    a = z.admin()
    if(a.get_storage(storage_id) is None):
        print('Add storage ')
        properties = {'selector': '{}/**'.format(args['prefix'])}
        a.add_storage(storage_id, properties)

    ws = z.workspace(args['prefix'])
    for k, vs in face_db.items():
        for j, v in enumerate(vs):
            uri = '{}/vectors/{}/{}'.format(args['prefix'], k, j)
            print('> Inserting face {}'.format(uri))
            sv = json.dumps(v)
            ws.put(uri, Value(sv, encoding=Encoding.STRING))

    z.logout()


if __name__ == '__main__':
    f = open(args['dataset'])
    faces = json.load(f)
    main(faces)
