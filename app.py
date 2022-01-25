from urllib import response
from flask import Flask, render_template, Response
import cv2
from flask import Flask, request, Response, render_template
from flask_cors import CORS, cross_origin
from flask_mongoengine import MongoEngine
import numpy as np
from id_tracking.centroidtracker import CentroidTracker
from imutils.video import VideoStream
import imutils
from facemask_detection.detect_mask_video import detect_mask, check_mask

import json
from os.path import dirname, join
proto_path = join(dirname(__file__), 'id_tracking/deploy.prototxt')
model_path = join(dirname(__file__), 'id_tracking/res10_300x300_ssd_iter_140000.caffemodel')


app = Flask(__name__)

app.config['MONGODB_HOST'] = 'mongodb+srv://busmot:busmot@cluster0.ih22n.mongodb.net/db?retryWrites=true&w=majority'
CORS(app)

db = MongoEngine(app)

valid_users = ['andrea', 'francesco']

RFID_POS = np.array([200, 200])
list_clients = {}
list_ids = np.array([], dtype=np.int32)
list_centroids = np.array([], dtype=np.int32)
RED = (0, 0, 255)
GREEN = (0, 255, 0)
ct = CentroidTracker()
(H, W) = (None, None)
objects = []
net = cv2.dnn.readNetFromCaffe(proto_path, model_path)

camera = VideoStream(0).start()  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera
# for local webcam use cv2.VideoCapture(0)

def close_to_rfid():
    global objects, RFID_POS, list_centroids

    min_dist = 1000000
    min_id = None
    for id, centroid in list_centroids.items():
        tmp = np.linalg.norm(np.asarray(centroid) - RFID_POS)
        if tmp < min_dist:
            min_dist = tmp
            min_id = id
    return min_id

def gen_frames():
    global ct, net, camera, H, W, list_ids, objects, RED, GREEN, list_centroids  # generate frame by frame from camera
    color = (0, 0, 0)
    while True:
        # Capture frame-by-frame
        frame = camera.read()
        frame = imutils.resize(frame, 400)  # read the camera frame
        if W is None or H is None:
            (H, W) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (W, H),
            (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()
        rects = []

        # loop over the detections
        for i in range(0, detections.shape[2]):
            # filter out weak detections by ensuring the predicted
            # probability is greater than a minimum threshold 
            if detections[0, 0, i, 2] > 0.5:
                # compute the (x, y)-coordinates of the bounding box for
                # the object, then update the bounding box rectangles list
                box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                rects.append(box.astype("int"))

                # draw a bounding box surrounding the object so we can
                # visualize it
                (startX, startY, endX, endY) = box.astype("int")
                # cv2.rectangle(frame, (startX, startY), (endX, endY),
                #     color, 2)

        # update our centroid tracker using the computed set of bounding
        # box rectangles

        objects = ct.update(rects)
        list_centroids = objects
        list_ids = []

        
        # loop over the tracked objects
        for (objectID, centroid) in objects.items():
            # draw both the ID of the object and the centroid of the
            # object on the output frame

            # if list_clients[objectID]["ticket"]:
            #     color = GREEN
            # else: 
            #     color = RED
            try:
                if list_clients[objectID]["ticket"] is True and list_clients[objectID]["face_mask"]:
                    color = GREEN
                else:
                    color = RED
            except:
                color = RED 
            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, color, -1)
            if objectID not in list_ids:
                list_ids = np.append(list_ids, objectID)
                if list_ids is not None:
                    list_ids = np.unique(list_ids)
                    list_ids = [int(id) for id in list_ids]


            # requests.post('http://localhost:5000/update_list', data={'ids': list_ids})
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result



class Users(db.DynamicDocument):
    username = db.StringField(max_length=60, required=True)
    valid = db.BooleanField(required=True)

@app.route('/list_all')
def list_all():
    users = Users.objects().to_json()
    return Response(users, mimetype="application/json", status=200)

@app.route('/video_feed')
def video_feed():
    #Video streaming route. Put this in the src attribute of an img tag
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/login', methods=['POST'])
def login_user():
    global list_clients, valid_users, list_centroids
    body = request.form.to_dict()
    user = body["username"]
    user = "".join(user.split())
    # print(f'request body: {user}, valid_users: {valid_users[1]}')
    # user = Users.object(username = body["username"])
    if user in valid_users:
        detect_mask()
        value = check_mask()
        print(value)
        if value is True:
        
    # if user.valid is True and body["face_mask"] is True:
            id_track = close_to_rfid()
            list_clients[id_track]["id"] = id_track
            list_clients[id_track]["ticket"] = True
            list_clients[id_track]["face_mask"] = True
            return Response(json.dumps(list_clients), mimetype="application/json", status=200)
        else:
            return Response(json.dumps("mask not detected"), mimetype="application/json", status=404)
    else:
        return Response(json.dumps("user not in db"), mimetype="application/json", status=404)

@app.route('/update_list', methods = ['GET'])
def update_list():
    global list_ids, list_clients
    keys_to_del = []
    # print(len(list_ids), len(list_clients))
    # print(f'list_ids: {list_ids}, list_clients: {list_clients}')
    if len(list_ids) < len(list_clients):
        for i, (k, v) in enumerate(list_clients.items()):
            if v["id"] not in list_ids:
                keys_to_del.append(k)
        for key in keys_to_del:
            list_clients.pop(key)

    for id in list_ids:
        if id not in list_clients:
            list_clients[id] = {"id": id,
                                "ticket": False,
                                "face_mask": False}
            # print(list_clients.items()[0]["ticket"])


    return Response(json.dumps(list_clients), mimetype="application/json", status=200)
        # else:
        #     return Response(json.dumps({"No new id"}), mimetype="application/json", status=200)

@app.route('/time')
def getTime():
    import datetime
    time = datetime.now()
    return "RPI4 date and time: " + str(time)

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    