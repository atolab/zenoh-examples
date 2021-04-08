import argparse
import time
import io
import ast
import cv2
import numpy as np
import face_recognition
import zenoh

parser = argparse.ArgumentParser(
    prog='recognize_faces',
    description='zenoh face recognition example')
parser.add_argument('-m', '--mode', type=str, choices=['peer', 'client'],
                    help='The zenoh session mode.')
parser.add_argument('-e', '--peer', type=str, metavar='LOCATOR', action='append',
                    help='Peer locators used to initiate the zenoh session.')
parser.add_argument('-l', '--listener', type=str, metavar='LOCATOR', action='append',
                    help='Locators to listen on.')
parser.add_argument('-q', '--quality', type=int, default=95,
                    help='The quality of the published faces (0 - 100)')
parser.add_argument('-p', '--prefix', type=str, default='/demo/facerecog',
                    help='The resources prefix')
parser.add_argument('-d', '--delay', type=float, default=0.2,
                    help='delay between each recognition')
parser.add_argument('-c', '--config', type=str, metavar='FILE',
                    help='A zenoh configuration file.')

args = vars(parser.parse_args())
conf = zenoh.config_from_file(args['config']) if args['config'] is not None else {}
for arg in ['mode', 'peer', 'listener']:
    if args[arg] is not None:
        conf[arg] = args[arg] if type(args[arg]) == str else ','.join(args[arg])

data = {}
data['encodings'] = []
data['names'] = []
cams = {}


def add_face_to_data(fdata, key, value):
    chunks = key.split('/')
    name = chunks[-2]
    num = chunks[-1]
    fdata['names'].append(name)
    a = ast.literal_eval(value)
    fdata['encodings'].append(a)


def update_face_data(sample):
    if sample.data_info is None or sample.data_info.kind is None or sample.data_info.kind == zenoh.ChangeKind.PUT:
        print('Received face vector {}'.format(sample.res_name))
        add_face_to_data(data, sample.res_name, sample.payload.decode('utf-8'))


def faces_listener(sample):
    chunks = sample.res_name.split('/')
    cam = chunks[-2]
    face = int(chunks[-1])

    if cam not in cams:
        cams[cam] = {}

    cams[cam][face] = sample.payload


print('[INFO] Open zenoh session...')
zenoh.init_logger()
z = zenoh.net.open(conf)

print('[INFO] Retrieve faces vectors...')
for vector in z.query_collect(args['prefix'] + '/vectors/**', ''):
    add_face_to_data(data, vector.data.res_name, vector.data.payload.decode('utf-8'))

print('[INFO] Start recognition...')
sub_info = zenoh.net.SubInfo(zenoh.net.Reliability.Reliable, zenoh.net.SubMode.Push)
sub1 = z.declare_subscriber(args['prefix'] + '/vectors/**', sub_info, update_face_data)
sub2 = z.declare_subscriber(args['prefix'] + '/faces/*/*', sub_info, faces_listener)

while True:
    for cam in list(cams):
        faces = cams[cam]
        for face in list(faces):
            npImage = np.load(io.BytesIO(faces[face]), allow_pickle=True)
            matImage = cv2.imdecode(npImage, 1)
            rgb = cv2.cvtColor(matImage, cv2.COLOR_BGR2RGB)

            encodings = face_recognition.face_encodings(rgb)

            name = 'Unknown'
            if len(encodings) > 0:
                matches = face_recognition.compare_faces(data['encodings'],
                                                         encodings[0])
                if True in matches:
                    matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                    counts = {}
                    for i in matchedIdxs:
                        name = data['names'][i]
                        counts[name] = counts.get(name, 0) + 1
                    name = max(counts, key=counts.get)

            path = args['prefix'] + '/faces/' + cam + '/' + str(face) + '/name'
            z.write(path, name.encode('utf-8'))

    time.sleep(args['delay'])
