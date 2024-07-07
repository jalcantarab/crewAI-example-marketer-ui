from flask import Flask, request, render_template, jsonify
from celery import Celery
import traceback
import crew_logic
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration for Celery
app.config['CELERY_BROKER_URL'] = os.getenv(
    'CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv(
    'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


@celery.task(bind=True)
def run_task(self, domain, description):
    try:
        self.update_state(state='STARTED', meta={'status': 'Processing...'})
        crew_logic.run(domain, description)
        with open('crew.log', 'r') as file:
            output = file.read()
        self.update_state(state='SUCCESS', meta={'output': output})
    except Exception as e:
        self.update_state(state='FAILURE', meta={
            'exc_type': type(e).__name__,
            'exc_message': str(e),
            'exc_traceback': traceback.format_exc()
        })
        raise


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
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state == 'STARTED':
        response = {
            'state': task.state,
            'status': task.info.get('status', 'Started...')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.info.get('output', 'No output')
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'status': f"Exception: {task.info.get('exc_type')}: {task.info.get('exc_message')}\n{task.info.get('exc_traceback')}"
        }
    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=True)
