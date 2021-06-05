import zenoh
from zenoh import Zenoh
import argparse
import io
import cv2
import time
import numpy as np

parser = argparse.ArgumentParser(
    prog='display_faces',
    description='zenoh face recognition example display')
parser.add_argument('-m', '--mode', type=str, choices=['peer', 'client'],
                    help='The zenoh session mode.')
parser.add_argument('-e', '--peer', type=str, metavar='LOCATOR', action='append',
                    help='Peer locators used to initiate the zenoh session.')
parser.add_argument('-l', '--listener', type=str, metavar='LOCATOR', action='append',
                    help='Locators to listen on.')
parser.add_argument('-p', '--prefix', type=str, default='/demo/facerecog',
                    help='resources prefix')
parser.add_argument('-d', '--delay', type=float, default=0.05,
                    help='delay between each refresh')
parser.add_argument('-c', '--config', type=str, metavar='FILE',
                    help='A zenoh configuration file.')

args = vars(parser.parse_args())
conf = zenoh.config_from_file(args['config']) if args['config'] is not None else {}
for arg in ['mode', 'peer', 'listener']:
    if args[arg] is not None:
        conf[arg] = args[arg] if type(args[arg]) == str else ','.join(args[arg])

cams = {}


def faces_listener(change):
    #print('[DEBUG] Received face: '+change.path)
    chunks = change.path.split('/')
    cam = chunks[-2]
    face = int(chunks[-1])

    if cam not in cams:
        cams[cam] = {}
    if face not in cams[cam]:
        cams[cam][face] = {'img': b'', 'name': '', 'time': 0}

    cams[cam][face]['img'] = bytes(change.value.get_content())
    cams[cam][face]['time'] = time.time()


def names_listener(change):
    #print('[DEBUG] Received name: {} {} => {}', change.path, change.value.get_content())
    chunks = change.path.split('/')
    cam = chunks[-3]
    face = int(chunks[-2])

    if cam not in cams:
        cams[cam] = {}
    if face not in cams[cam]:
        cams[cam][face] = {'img': b'', 'name': '', 'time': 0}

    cams[cam][face]['name'] = change.value.get_content() 


print('[INFO] Open zenoh session...')
zenoh.init_logger()
z = Zenoh(conf)
w = z.workspace()
sub1 = w.subscribe(args['prefix'] + '/faces/*/*', faces_listener)
sub2 = w.subscribe(args['prefix'] + '/faces/*/*/name', names_listener)

for data in w.get(args['prefix'] + '/faces/*/*/name') :
    names_listener(data)

print('[INFO] Display detected faces ...')

while True:
    now = time.time()

    for cam in list(cams):
        faces = cams[cam]
        vbuf = np.zeros((250, 1000, 3), np.uint8)
        for face in list(faces):
            if faces[face]['time'] > now - 0.2:
                npImage = np.load(io.BytesIO(faces[face]['img']), allow_pickle=True)
                matImage = cv2.imdecode(npImage, 1)
                h, w, _ = matImage.shape
                vbuf[40:40+h, 200*face:200*face+w] = matImage

                name = faces[face]['name']
                color = (0, 0, 255) if name == 'Unknown' else (0, 255, 0)
                cv2.putText(vbuf,
                            name,
                            (200*face + 2, 18),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.75,
                            color,
                            2)

        cv2.imshow('Cam #' + cam, vbuf)

    time.sleep(args['delay'])

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cv2.destroyAllWindows()
sub1.close()
sub2.close()
z.close()
