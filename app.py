from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
from socket_handlers import register_handlers
from celery_config import celery_app
from marketing_posts.crew import MarketingPostsCrew

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

# Initialize SocketIO
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Register socket handlers
register_handlers(socketio)


@celery_app.task(bind=True)
def run_task(self, domain, description):
    crew = MarketingPostsCrew()

    def progress_callback(task, progress):
        self.update_state(state='PROGRESS',
                          meta={'task': task, 'progress': progress})
        socketio.emit('progress', {'task': task,
                      'progress': progress}, namespace='/')

    crew.set_progress_callback(progress_callback)

    def log_callback(message):
        socketio.emit('log', {'message': message}, namespace='/')

    # Initial log queue processing
    while not crew.log_queue.empty():
        log_callback(crew.log_queue.get())

    # Run the crew
    result = crew.run(domain, description)

    # Final log queue processing
    while not crew.log_queue.empty():
        log_callback(crew.log_queue.get())

    return result


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    domain = request.form['domain']
    description = request.form['description']
    task = run_task.apply_async(args=[domain, description])
    return jsonify({'task_id': task.id}), 202


@app.route('/results/<task_id>')
def results(task_id):
    task = run_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'task': task.info.get('task', ''),
            'progress': task.info.get('progress', 0)
        }
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'status': str(task.info),
        }
    else:
        response = {'state': task.state, 'status': str(task.info)}
    return jsonify(response)


def find_free_port(start_port=5000, max_port=5999):
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    raise IOError("No free ports")


def main():
    port = int(os.getenv('PORT', 5001))
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=port)
    except OSError:
        print(f"Port {port} is in use. Trying to find a free port...")
        free_port = find_free_port(start_port=port+1)
        print(f"Found free port: {free_port}")
        socketio.run(app, debug=True, host='0.0.0.0', port=free_port)


if __name__ == '__main__':
    main()
