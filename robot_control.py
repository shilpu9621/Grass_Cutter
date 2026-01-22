# robot_control_safe.py

import time
import threading

# ===================== OPTIONAL RASPBERRY PI IMPORTS =====================
try:
    import RPi.GPIO as GPIO # type: ignore
    import pigpio # type: ignore
    from picamera import PiCamera # type: ignore
    IS_PI = True
except ModuleNotFoundError:
    print("⚠ Running on non-Pi environment. Hardware imports skipped.")
    IS_PI = False

# ===================== MOTORS =====================
LEFT_ESC = 18
RIGHT_ESC = 19

if IS_PI:
    pi = pigpio.pi()

def set_motor_speed(esc_pin, speed):
    """
    ESC speed: 0 (stop) to 100 (full speed)
    """
    if IS_PI:
        pulse_width = int(1000 + (speed * 10))  # 1000-2000us
        pi.set_servo_pulsewidth(esc_pin, pulse_width)
    else:
        print(f"[SIMULATION] Motor {esc_pin} speed set to {speed}%")

# ===================== ULTRASONIC =====================
TRIG = 23
ECHO = 24

if IS_PI:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

def distance_cm():
    if IS_PI:
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()
        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        return round(distance, 2)
    else:
        # Simulate distance for testing
        import random
        simulated_distance = random.randint(10, 100)
        print(f"[SIMULATION] Distance: {simulated_distance} cm")
        return simulated_distance

# ===================== CAMERA =====================
if IS_PI:
    camera = PiCamera()
    camera.resolution = (640, 480)
    camera.framerate = 15

    from flask import Flask, Response # type: ignore
    import io
    app = Flask(__name__)

    def gen_frames():
        stream = io.BytesIO()
        for _ in camera.capture_continuous(stream, 'jpeg', use_video_port=True):
            stream.seek(0)
            frame = stream.read()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            stream.seek(0)
            stream.truncate()

    @app.route('/video')
    def video_feed():
        return Response(gen_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

# ===================== ROBOT LOGIC =====================
def robot_drive():
    try:
        while True:
            dist = distance_cm()
            if dist < 20:
                set_motor_speed(LEFT_ESC, 0)
                set_motor_speed(RIGHT_ESC, 0)
                print("Obstacle detected! Stopping motors.")
            else:
                set_motor_speed(LEFT_ESC, 50)
                set_motor_speed(RIGHT_ESC, 50)

            time.sleep(0.5)
    except KeyboardInterrupt:
        set_motor_speed(LEFT_ESC, 0)
        set_motor_speed(RIGHT_ESC, 0)
        if IS_PI:
            GPIO.cleanup()
            pi.stop()
        print("Robot stopped.")

# ===================== MAIN =====================
if __name__ == '__main__':
    if IS_PI:
        # Run robot logic in background thread
        threading.Thread(target=robot_drive, daemon=True).start()

        # Start Flask camera streaming
        print("Access camera at http://<Pi_IP>:5000/video")
        app.run(host='0.0.0.0', port=5000)
    else:
        print("⚠ Simulation mode: running robot logic without hardware.")
        robot_drive()
