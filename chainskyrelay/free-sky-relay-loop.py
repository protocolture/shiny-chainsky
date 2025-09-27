import RPi.GPIO as GPIO
import time
from flask import Flask, request, jsonify
import logging
import threading


#Curretly using Flask to listen for webhooks
#Obviously never run this in any permanent or enterprise environment. 
#Use at own risk.
#TODO: 
#1. Move to authenticated webserver
#2. Require Pin command AND duration as separate values 
#3. Battle Harden 

app = Flask(__name__)

# Set up logging - Possibility here to get more serious logging going, however the goal here was to create an easy way to check on HA components. 
logging.basicConfig(filename='webhook.log', level=logging.DEBUG)

# Set up the GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.OUT, initial=GPIO.HIGH)  # GOSMOKE
GPIO.setup(6, GPIO.OUT, initial=GPIO.HIGH)  # SC1
GPIO.setup(13, GPIO.OUT, initial=GPIO.HIGH) # SC2
GPIO.setup(16, GPIO.OUT, initial=GPIO.HIGH) # SC3
GPIO.setup(19, GPIO.OUT, initial=GPIO.HIGH) # SC4


#Can obviously clean these up at some stage. GOSMOKE is arbitrary. Balance between exposing pins directly and coming up with goofy code names. 
pin_mapping = {
    "GOSMOKE": 5,
    "SC1": 6,
    "SC2": 13,
    "SC3": 16,
    "SC4": 19
}

def activate_pin(pin, duration):
    GPIO.output(pin, GPIO.LOW)  # Activate pin
    time.sleep(duration)
    GPIO.output(pin, GPIO.HIGH)  # Deactivate pin

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    app.logger.debug(f'Received data: {data}')
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    try:
        for key, value in data.items():
        #Check that the key value actually matches something we are interested in
            if key in pin_mapping and int(value) == 1:
                pin = pin_mapping[key]
                app.logger.debug(f'Activating {key} on pin {pin}')
                print(f'Activating {key} on pin {pin}')
                duration = 5  # Hardcoded duration, requirement only for testing. 
                threading.Thread(target=activate_pin, args=(pin, duration)).start()

        return jsonify({"message": "Success"}), 200
    except ValueError as e:
        app.logger.error(f'ValueError: {e}')
        return jsonify({"error": f'Invalid data: {e}'}), 400
    except Exception as e:
        app.logger.error(f'Exception: {e}')
        return jsonify({"error": f'Server error: {e}'}), 500

@app.route('/')
def index():
    return "Webhook listener is running", 200

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        GPIO.cleanup()
