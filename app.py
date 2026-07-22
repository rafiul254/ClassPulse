import os
import json
import time
from datetime import datetime
from flask import (Flask, render_template, Response,
                   jsonify, request, stream_with_context)

from detector     import Detector
from database     import Database
from mqtt_handler import MQTTPublisher
from config       import FLASK_HOST, FLASK_PORT, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

os.makedirs('sessions', exist_ok=True)
os.makedirs('reports',  exist_ok=True)

db       = Database()
mqtt     = MQTTPublisher()
detector = Detector()

detector.set_db(db)
detector.set_mqtt(mqtt)

detector.start()
mqtt.connect()


@app.route('/')
def index():

    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(
        detector.gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
    )


@app.route('/stream')
def stream():

    def event_gen():
        while True:
            data = detector.get_stats()
            yield f'data: {json.dumps(data)}\n\n'
            time.sleep(0.8)

    return Response(
        stream_with_context(event_gen()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection':       'keep-alive',
        },
    )



@app.route('/api/start_session', methods=['POST'])
def start_session():
    body = request.get_json(silent=True) or {}
    name = body.get('name', '').strip()
    if not name:
        name = f"Session — {datetime.now().strftime('%d %b %Y, %H:%M')}"

    sid = db.start_session(name)
    detector.set_session(sid)
    return jsonify({'status': 'ok', 'session_id': sid, 'name': name})


@app.route('/api/end_session', methods=['POST'])
def end_session():
    sid = detector.get_session_id()
    if not sid:
        return jsonify({'status': 'error', 'message': 'No active session'}), 400

    stats = detector.get_stats()
    db.end_session(sid, stats.get('class_attention', 0))
    detector.set_session(None)
    return jsonify({'status': 'ok', 'session_id': sid})


@app.route('/api/stats')
def api_stats():

    return jsonify(detector.get_stats())


@app.route('/api/sessions')
def api_sessions():

    return jsonify(db.get_sessions())


@app.route('/report/<int:session_id>')
def report(session_id):
    session = db.get_session(session_id)
    logs    = db.get_logs(session_id)
    alerts  = db.get_alerts(session_id)
    return render_template('report.html',
                           session=session,
                           logs=logs,
                           alerts=alerts)


@app.route('/api/export/<int:session_id>')
def export_csv(session_id):

    csv_data = db.export_csv(session_id)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition':
                f'attachment; filename=classpulse_session_{session_id}.csv'
        },
    )


if __name__ == '__main__':
    print()
    print('╔══════════════════════════════════════════════╗')
    print('║         ClassPulse — Starting                ║')
    print('║  Dashboard → http://localhost:5000           ║')
    print('╚══════════════════════════════════════════════╝')
    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=False,
            threaded=True,
            use_reloader=False,
        )
    finally:
        detector.stop()
        mqtt.disconnect()
