import RPi.GPIO as gpio
from mfrc522 import SimpleMFRC522
import requests
import json


CardReader = SimpleMFRC522()
print('Scanning for a  card..')
print('to cancel press ctrl+c')
try:
    id, user = CardReader.read()
    print(user)
    # send to the server the request containing the username of who tried to validate his ticket
    req = requests.post("http://172.16.40.31:5000/login",
                        data={"username": user})
    print(req.content)
finally:
    gpio.cleanup()
