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
model_path = join(dirname(__file__),
                  'id_tracking/res10_300x300_ssd_iter_140000.caffemodel')

# initializing Flask application (server)
app = Flask(__name__)

# configuring database
app.config['MONGODB_HOST'] = 'mongodb+srv://busmot:busmot@cluster0.ih22n.mongodb.net/db?retryWrites=true&w=majority'
CORS(app)
db = MongoEngine(app)

# RFID ticket validation machine is arbitrarly placed in the center of the frame
RFID_POS = np.array([200, 200])

# dictionary containing all the tracked clients with their respective information about ticket and mask
list_clients = {}
# ids and centroids positions tracked by the object tracking module
list_ids = np.array([], dtype=np.int32)
list_centroids = np.array([], dtype=np.int32)

RED = (0, 0, 255)
GREEN = (0, 255, 0)

# initializing centroid tracker and loading the backbone for object detection
ct = CentroidTracker()
(H, W) = (None, None)
objects = []
net = cv2.dnn.readNetFromCaffe(proto_path, model_path)

# starting the video stream from the webcam
camera = VideoStream(0).start()


def close_to_rfid():
    '''Calculates which id tracked by the object detection module is the closest to the RFID ticket validation machine location'''
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
    '''Object tracking module. Finds all the subjects in the frame and tracks them with their respective IDs'''

    global ct, net, camera, H, W, list_ids, objects, RED, GREEN, list_centroids
    color = (0, 0, 0)

    while True:
        # Capture frame-by-frame
        frame = camera.read()
        frame = imutils.resize(frame, 400)  # read the camera frame
        if W is None or H is None:
            (H, W) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (W, H),
                                     (104.0, 177.0, 123.0))  # turns frame into blob format
        net.setInput(blob)
        detections = net.forward()  # predicts the objects in the frame
        rects = []

        # loop over the detections
        for i in range(0, detections.shape[2]):
            # filter out weak detections by ensuring the predicted probability is greater than a minimum threshold
            if detections[0, 0, i, 2] > 0.5:
                # compute the (x, y)-coordinates of the bounding box for the object, then update the bounding box rectangles list
                box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                rects.append(box.astype("int"))
                (startX, startY, endX, endY) = box.astype("int")

        # update our centroid tracker using the computed set of bounding box rectangles
        objects = ct.update(rects)
        list_centroids = objects  # store all the tracked centroids
        #list_ids = []

        # loop over the tracked objects
        for (objectID, centroid) in objects.items():
            # draw both the ID of the object and the centroid of the object on the output frame
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

            # Updating the currently tracked ids
            if objectID not in list_ids:
                list_ids = np.append(list_ids, objectID)
                if list_ids is not None:
                    list_ids = np.unique(list_ids)
                    list_ids = [int(id) for id in list_ids]

        # encode frames, keep them in a buffer and send them to the busMOT dashboard
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

# defines a Users collection in mongoEngine
class Users(db.DynamicDocument):
    username = db.StringField(max_length=60, required=True)
    valid = db.BooleanField(required=True)


@app.route('/list_all')
def list_all():
    '''Lists all the users in the database'''
    users = Users.objects().to_json()
    return Response(users, mimetype="application/json", status=200)


@app.route('/video_feed')
def video_feed():
    '''Sends the video feed to the front-end'''
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/login', methods=['POST'])
def login_user():
    '''Logins the user who tried to validate his ticket. Waits for request from the RFID validation module'''
    global list_clients, valid_users, list_centroids
    body = request.form.to_dict()
    user = body["username"]
    user = "".join(user.split())
    # print(f'request body: {user}, valid_users: {valid_users[1]}')
    # user = Users.object(username = body["username"])
    try:  # checks that the user who tried to validate his ticket has a subscription
        valid_user = Users.objects(username = user)
        if valid_user.valid:
            detect_mask()  # detects the mask in 10 frames
            # checks that in at least 6 frames out of 10 the mask is on.
            value = check_mask()
            print(value)
            if value is True:
                # finds the tracked subjects who is the closest to the RFID machine and sets his ticket and mask properties to True
                id_track = close_to_rfid()
                list_clients[id_track]["id"] = id_track
                list_clients[id_track]["ticket"] = True
                list_clients[id_track]["face_mask"] = True
                return Response(json.dumps(list_clients), mimetype="application/json", status=200)
            else:
                return Response(json.dumps("Mask not worn properly"), mimetype="application/json", status=404)
        else: 
            return Response(json.dumps("User subscription is not valid"), mimetype="application/json", status=404)
    except:
        return Response(json.dumps("User not in DB"), mimetype="application/json", status=404)


@app.route('/update_list', methods=['GET'])
def update_list():
    '''Updates the users list. The final list will contain only the actively tracked users'''
    global list_ids, list_clients

    # compares the list of ids returned by the object tracking module with the list of the users to send to the front-end. Pops from the list to send to the front-end all the users that are not tracked anymore.
    keys_to_del = []
    if len(list_ids) < len(list_clients):
        for i, (k, v) in enumerate(list_clients.items()):
            if v["id"] not in list_ids:
                keys_to_del.append(k)
        for key in keys_to_del:
            list_clients.pop(key)
    # adds all the new tracked id to the list to send to the front-end, initially setting their ticker and mask properties to false.
    for id in list_ids:
        if id not in list_clients:
            list_clients[id] = {"id": id,
                                "ticket": False,
                                "face_mask": False}
    # sends the updated list of users to the front-end
    return Response(json.dumps(list_clients), mimetype="application/json", status=200)


@app.route('/')
def index():
    """Renders the busMOT dashboard"""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
