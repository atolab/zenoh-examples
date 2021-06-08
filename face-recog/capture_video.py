import argparse
from imutils.video import VideoStream
import imutils
import time
import io
import cv2
import random
import zenoh
from zenoh import Zenoh
import binascii
import numpy as np

parser = argparse.ArgumentParser(
    prog='capture_video',
    description='zenoh face recognition example face detector')
parser.add_argument('-m', '--mode', type=str, choices=['peer', 'client'],
                    help='The zenoh session mode.')
parser.add_argument('-e', '--peer', type=str, metavar='LOCATOR', action='append',
                    help='Peer locators used to initiate the zenoh session.')
parser.add_argument('-l', '--listener', type=str, metavar='LOCATOR', action='append',
                    help='Locators to listen on.')
parser.add_argument('-i', '--id', type=int, default=random.randint(1, 999),
                    help='The Camera ID.')
parser.add_argument('-w', '--width', type=int, default=500,
                    help='width of the published frames')
parser.add_argument('-q', '--quality', type=int, default=95,
                    help='quality of the published frames (0 - 100)')
parser.add_argument('-d', '--delay', type=float, default=0.05,
                    help='delay between each frame in seconds')
parser.add_argument('-p', '--prefix', type=str, default='/demo/facerecog',
                    help='resources prefix')
parser.add_argument('-c', '--config', type=str, metavar='FILE',
                    help='A zenoh configuration file.')

args = vars(parser.parse_args())
conf = zenoh.config_from_file(args['config']) if args['config'] is not None else {}
for arg in ['mode', 'peer', 'listener']:
    if args[arg] is not None:
        conf[arg] = args[arg] if type(args[arg]) == str else ','.join(args[arg])

jpeg_opts = [int(cv2.IMWRITE_JPEG_QUALITY), args['quality']]
cam_id = args['id']

print('[INFO] Open zenoh session...')

zenoh.init_logger()
z = Zenoh(conf)
w = z.workspace()

print('[INFO] Start video stream - Cam #{}'.format(cam_id))
vs = VideoStream(src=0).start()
time.sleep(1.0)

while True:
    raw = vs.read()
    frame = imutils.resize(raw, width=500)

    _, jpeg = cv2.imencode('.jpg', frame, jpeg_opts)
    buf = io.BytesIO()
    np.save(buf, jpeg, allow_pickle=True)

    #print('[DEBUG] Put frame: {}/cams/{}'.format(args['prefix'], cam_id))
    w.put('{}/cams/{}'.format(args['prefix'], cam_id), buf.getvalue())

    time.sleep(args['delay'])

vs.stop()
z.close()
