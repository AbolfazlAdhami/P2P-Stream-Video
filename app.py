from flask import Flask, Response, render_template_string
import cv2
import pyaudio
import time
import argparse

app = Flask(__name__)

# Configs
VIDEO_RESOLUTION = (640, 480)
JPEG_QUALITY = 75
camera = None
running = True

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
audio = None
audio_stream = None

WELCOME_MSG = """
============================================================
       Welcome to P2P Stream System
============================================================
- PORT: {port}
- browser Address: http://localhost:{port}
- Local Network: http://{local_ip}:{port}
- Video Resolution: {width}x{height}
- Audio sampling rate: {rate} Hz
- To exit: Ctrl+C in terminal
============================================================
"""


def init_camera():
    global camera
    if camera is not None:
        camera.release()
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_RESOLUTION[0])
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_RESOLUTION[1])
    print(f"[Video] Webcam opened → {VIDEO_RESOLUTION}")


def init_audio():
    global audio, audio_stream
    audio = pyaudio.PyAudio()
    audio_stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    print("[Audio] Microphone opened")


def gen_video():
    while running:
        if camera is None or not camera.isOpened():
            time.sleep(0.5)
            continue
        success, frame = camera.read()
        if not success:
            continue
        ret, buffer = cv2.imencode(
            '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    print("[Video] Video streaming stopped")


def gen_audio():
    print("[Audio] Starting audio streaming...")
    while running:
        try:
            data = audio_stream.read(CHUNK, exception_on_overflow=False)
            yield data
        except Exception as e:
            print(f"[Sound] Error reading: {e}")
            time.sleep(0.1)


@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>استریم زنده وب‌کم + صدا</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; background: #111; color: #eee; margin: 0; padding: 20px; }
            h1 { color: #4CAF50; }
            .container { max-width: 900px; margin: auto; }
            video, audio { width: 100%; max-width: 800px; border: 3px solid #333; border-radius: 10px; margin: 15px 0; }
            small { color: #aaa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>استریم زنده از وب‌کم و میکروفون</h1>
            <p>اگر صدا یا تصویر نمی‌آید، اجازه دسترسی به دوربین و میکروفون را بدهید.</p>
            <h3>ویدیو زنده</h3>
            <img src="/video_feed" alt="ویدیو زنده">

            <h3>صدا زنده (میکروفون)</h3>
            <br><br>
        </div>
    </body>
    </html>
    """, port=app.config.get('PORT', 5000))


@app.route('/video_feed')
def video_feed():
    return Response(gen_video(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/audio_feed')
def audio_feed():
    return Response(gen_audio(),
                    mimetype='audio/wav; codecs="1"',
                    headers={
                        'Content-Type': 'audio/wav',
                        'Transfer-Encoding': 'chunked'
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Streaming Video + Audio with Flask")
    parser.add_argument('--port', type=int, default=8000, help='Server Port')
    args = parser.parse_args()

    import socket
    local_ip = socket.gethostbyname(socket.gethostname())

    print(WELCOME_MSG.format(
        port=args.port,
        local_ip=local_ip,
        width=VIDEO_RESOLUTION[0],
        height=VIDEO_RESOLUTION[1],
        rate=RATE
    ))

    init_camera()
    init_audio()

    try:
        app.run(host='0.0.0.0', port=args.port, threaded=True, debug=False)
    finally:
        running = False
        if camera is not None:
            camera.release()
        if audio_stream is not None:
            audio_stream.stop_stream()
            audio_stream.close()
        if audio is not None:
            audio.terminate()
        cv2.destroyAllWindows()
        print("\n[Exit] All resources were released.")
