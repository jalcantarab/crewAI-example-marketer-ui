# AI Agents Web UI: Project Definition

## Objective
To create a web interface that right now allows users to take a post idea and initiate a crew of AI agents using the CrewAI framework. The web interface provides real-time feedback on the progress and output of the agents.

## Resources and Versions
1. **CrewAI Framework** (version 0.35.8): For defining and running agents and tasks.
2. **Flask** (version 3.0.3): Web framework for the user interface.
3. **Flask-SocketIO** (version 5.3.6): For real-time, bidirectional communication.
4. **Celery** (version 5.4.0): Task queue to manage asynchronous task execution.
5. **Redis** (version 5.0.7): Message broker for Celery and result backend.
6. **Python-dotenv** (version 1.0.1): For loading environment variables.
7. **Eventlet** (version 0.35.2): Concurrent networking library for WebSocket support.

## Components
1. **Flask Web Interface**: For user input and displaying results.
2. **WebSocket Communication**: For real-time updates on task progress and logs.
3. **Celery Tasks**: For running agent tasks asynchronously.
4. **CrewAI Agents and Tasks**: Defined to perform specific roles within the project.
5. **Logging and Monitoring**: To capture and display task progress and outputs in real-time.

## Architecture

### High-Level Architecture
1. **User Interface (UI)**: Flask app with forms to collect project details and display task progress and results.
2. **Backend Processing**: Celery tasks to execute CrewAI tasks asynchronously.
3. **Real-time Communication**: WebSocket for sending live updates to the frontend.
4. **Data Storage**: Redis for message brokering and temporary data storage.
5. **Logging**: Custom logging handler to capture and stream agent activities.

### Detailed Components

#### 1. Flask Web Application (app.py)
- Handles web routes and integrates with Flask-SocketIO for real-time communication.
- Initiates Celery tasks for CrewAI execution.

#### 2. Celery Task Runner (celery_config.py)
- Configures Celery for task management.
- Defines the main task for running CrewAI agents.

#### 3. WebSocket Handlers (socket_handlers.py)
- Manages WebSocket connections and event emissions.

#### 4. CrewAI Integration (crew.py)
- Defines AI agents, tasks, and the overall workflow.
- Implements custom logging and progress tracking.

#### 5. Frontend (index.html)
- Provides user interface for input and displays real-time progress and results.
- Uses WebSocket for live updates.

## Key Features
1. Real-time progress updates using WebSockets.
2. Asynchronous task execution with Celery.
3. (not working) Custom logging to stream agent activities to the frontend.
4. (pending) Structured output display for the agent / task output. 

## Development Environment
- Python 3.11
- Poetry for dependency management
- Redis server for message brokering and result backend

## Running the Application
1. Install dependencies: `poetry install`
2. Set up environment variables in `.env` file
3. Start Redis server
4. Run Celery worker: `poetry run celery -A app.celery_app worker --loglevel=info`
5. Start Flask application: `poetry run marketing_posts`
6. Access the application at `http://localhost:5001`

## Relevant Files

#### 1. Flask Web Application (app.py)
```py
import socket
from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
from socket_handlers import register_handlers
from celery_config import celery_app
from marketing_posts.crew import LinkedInPostCrew

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
def run_task(self, post_idea):
    crew = LinkedInPostCrew(socketio)

    def progress_callback(task, progress):
        self.update_state(state='PROGRESS',
                          meta={'task': task, 'progress': progress})
        socketio.emit('progress', {'task': task,
                      'progress': progress}, namespace='/')

    crew.set_progress_callback(progress_callback)

    def log_callback(message):
        socketio.emit('log', {'message': message}, namespace='/')

    # Run the crew
    result = crew.run(post_idea)

    # Process all logs
    while not crew.log_queue.empty():
        log_callback(crew.log_queue.get())

    return result


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    post_idea = request.form['post_idea']
    task = run_task.apply_async(args=[post_idea])
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

```

#### 2. Celery Task Runner (celery_config.py)
```py
import logging
from marketing_posts.crew import MarketingPostsCrew

def run(domain, description):
    inputs = {
        'customer_domain': domain,
        'project_description': description
    }
    try:
        return MarketingPostsCrew().crew().kickoff(inputs=inputs)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise


def train(n_iterations, domain, description):
    inputs = {
        'customer_domain': domain,
        'project_description': description
    }
    try:
        return MarketingPostsCrew().crew().train(n_iterations=n_iterations, inputs=inputs)
    except Exception as e:
        logging.error(f"An error occurred while training the crew: {e}")
        raise

```

#### 3. WebSocket Handlers (socket_handlers.py)
```py
from flask_socketio import emit


def register_handlers(socketio):
    @socketio.on('connect')
    def handle_connect():
        emit('connected', {'data': 'Connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    @socketio.on('start_task')
    def handle_start_task(data):
        # This could be used to start a task from the frontend if needed
        pass

```

#### 4. CrewAI Integration (crew.py)
```py
import logging
from typing import Callable
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from queue import Queue
from flask_socketio import SocketIO

# Progress Tracking Callback
ProgressCallback = Callable[[str, float], None]


class Story(BaseModel):
    title: str = Field(..., description="Title of the story")
    description: str = Field(..., description="Brief description of the story")


class LinkedInPost(BaseModel):
    content: str = Field(..., description="Content of the LinkedIn post")
    hashtags: list[str] = Field(..., description="List of relevant hashtags")


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)


@CrewBase
class LinkedInPostCrew():
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    log_queue: Queue = Queue()
    logger: logging.Logger = None
    progress_callback: ProgressCallback = None
    socketio: SocketIO = None

    def __init__(self, socketio):
        self.setup_logging()
        self.socketio = socketio

    def setup_logging(self):
        self.logger = logging.getLogger("CrewAI")
        self.logger.setLevel(logging.INFO)
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        self.logger.addHandler(queue_handler)

    def set_progress_callback(self, callback: ProgressCallback):
        self.progress_callback = callback

    def log_progress(self, task_name: str, progress: float):
        if self.progress_callback:
            self.progress_callback(task_name, progress)
        self.logger.info(f"Task: {task_name} - Progress: {progress:.2f}%")

    def step_callback(self, step_output):
        # Extract relevant information from step_output
        agent_name = step_output.get('agent_name', 'Unknown Agent')
        task_description = step_output.get('task_description', 'Unknown Task')
        step_details = step_output.get('step_details', 'No details provided')

        message = f"Agent: {agent_name} - Task: {task_description[:50]}... - Step: {step_details}"
        self.logger.info(message)
        if self.socketio:
            self.socketio.emit('step_update', {'message': message}, namespace='/')

    @agent
    def story_ideator(self) -> Agent:
        return Agent(
            config=self.agents_config['story_ideator'],
            verbose=True,
            memory=False,
            logger=self.logger,
            step_callback=self.step_callback
        )

    @agent
    def linkedin_post_creator(self) -> Agent:
        return Agent(
            config=self.agents_config['linkedin_post_creator'],
            verbose=True,
            memory=False,
            logger=self.logger,
            step_callback=self.step_callback
        )

    @task
    def generate_story_ideas_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_story_ideas_task'],
            agent=self.story_ideator(),
            output_json=Story,
            callback=lambda _: self.log_progress("Generate Story Ideas", 100)
        )

    @task
    def create_linkedin_post_task(self) -> Task:
        return Task(
            config=self.tasks_config['create_linkedin_post_task'],
            agent=self.linkedin_post_creator(),
            context=[self.generate_story_ideas_task()],
            output_json=LinkedInPost,
            callback=lambda _: self.log_progress("Create LinkedIn Post", 100)
        )

    @crew
    def crew(self) -> Crew:
        self.logger.info('Creating the LinkedIn Post crew')
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=2,
            logger=self.logger
        )

    def run(self, post_idea: str):
        self.logger.info(f"Starting LinkedIn Post crew for idea: {post_idea}")
        self.log_progress("Overall", 0)

        crew = self.crew()
        result = crew.kickoff(inputs={"post_idea": post_idea})

        self.logger.info("LinkedIn Post crew completed all tasks")
        self.log_progress("Overall", 100)

        return result

```

#### 5. Frontend (index.html)
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkedIn Post Generator</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { background-color: #f8f9fa; }
        #logs { height: 300px; overflow-y: auto; font-family: monospace; font-size: 14px; }
        .progress { height: 25px; }
    </style>
</head>
<body>
    <div class="container py-5">
        <h1 class="mb-4">LinkedIn Post Generator</h1>
        <form id="submitForm">
            <div class="mb-3">
                <label for="post_idea" class="form-label">Post Idea:</label>
                <textarea class="form-control" id="post_idea" name="post_idea" rows="4" required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Generate LinkedIn Post</button>
        </form>
        <div id="status" class="alert mt-3 d-none"></div>
        <div id="progress-container" class="mt-4 d-none">
            <h3>Progress</h3>
            <div id="overall-progress" class="progress mb-3">
                <div class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
            </div>
            <div id="task-progress"></div>
        </div>
        <h2 class="mt-4">Logs</h2>
        <div id="logs" class="border p-3 bg-light"></div>
        <div id="result-container" class="mt-4 d-none">
            <h2>Generated LinkedIn Post</h2>
            <div id="post-content" class="border p-3 bg-white"></div>
            <div id="post-hashtags" class="mt-2"></div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    const socket = io();
    const statusElement = document.getElementById('status');
    const logsDiv = document.getElementById('logs');
    const progressContainer = document.getElementById('progress-container');
    const overallProgress = document.getElementById('overall-progress').querySelector('.progress-bar');
    const taskProgress = document.getElementById('task-progress');
    const resultContainer = document.getElementById('result-container');
    const postContent = document.getElementById('post-content');
    const postHashtags = document.getElementById('post-hashtags');

    socket.on('connect', () => {
        console.log('Connected to server');
        updateStatus('Connected to server', 'info');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        updateStatus('Disconnected from server. Please refresh the page.', 'warning');
    });

    socket.on('log', (data) => {
        addLogEntry(data.message);
    });

    socket.on('step_update', (data) => {
        addLogEntry(data.message);
    });

    socket.on('progress', (data) => {
        progressContainer.classList.remove('d-none');
        if (data.task === 'Overall') {
            updateOverallProgress(data.progress);
        } else {
            updateTaskProgress(data.task, data.progress);
        }
    });

    function addLogEntry(message) {
        const logEntry = document.createElement('div');
        logEntry.textContent = message;
        logsDiv.appendChild(logEntry);
        logsDiv.scrollTop = logsDiv.scrollHeight;
    }

    function updateOverallProgress(progress) {
        overallProgress.style.width = `${progress}%`;
        overallProgress.textContent = `${progress}%`;
        overallProgress.setAttribute('aria-valuenow', progress);
    }

    function updateTaskProgress(task, progress) {
        const taskId = `progress-${task.replace(/\s+/g, '-').toLowerCase()}`;
        let taskBar = document.getElementById(taskId);
        if (!taskBar) {
            taskBar = createTaskProgressBar(task, taskId);
        }
        const progressBar = taskBar.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${task}: ${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
    }

    function createTaskProgressBar(task, taskId) {
        const taskBar = document.createElement('div');
        taskBar.className = 'progress mb-2';
        taskBar.innerHTML = `
            <div id="${taskId}" class="progress-bar" role="progressbar" 
                style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                ${task}: 0%
            </div>`;
        taskProgress.appendChild(taskBar);
        return taskBar;
    }

    function submitForm(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        
        updateStatus('Submitting...', 'info');
        
        fetch('/submit', { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                updateStatus('Task submitted. Processing...', 'info');
                resetProgress();
                checkStatus(data.task_id);
            })
            .catch(error => updateStatus('Error submitting task: ' + error.message, 'danger'));
    }

    function checkStatus(taskId) {
        fetch('/results/' + taskId)
            .then(response => response.json())
            .then(data => {
                if (data.state === 'SUCCESS') {
                    updateStatus('Task completed successfully!', 'success');
                    displayResults(data.result);
                } else if (data.state === 'FAILURE') {
                    updateStatus('Task failed. Please try again.', 'danger');
                } else if (data.state === 'PROGRESS') {
                    updateTaskProgress(data.task, data.progress);
                    setTimeout(() => checkStatus(taskId), 1000);
                } else {
                    setTimeout(() => checkStatus(taskId), 1000);
                }
            })
            .catch(error => updateStatus('Error checking status: ' + error.message, 'danger'));
    }

    function updateStatus(message, type) {
        statusElement.textContent = message;
        statusElement.className = `alert mt-3 alert-${type}`;
        statusElement.classList.remove('d-none');
    }

    function resetProgress() {
        progressContainer.classList.add('d-none');
        updateOverallProgress(0);
        taskProgress.innerHTML = '';
        resultContainer.classList.add('d-none');
    }

    function displayResults(result) {
        resultContainer.classList.remove('d-none');
        postContent.textContent = result.content;
        postHashtags.textContent = result.hashtags.join(' ');
    }

    document.getElementById('submitForm').addEventListener('submit', submitForm);
    </script>
</body>
</html>
```


#### 6. Agent & Task Definition (src/marketing_posts/config/agents.yaml & src/marketing_posts/config/tasks.yaml)
```yaml
story_ideator:
  role: >
    Story Ideator
  goal: >
    Generate creative and engaging story ideas based on the given post idea.
  backstory: >
    You are a creative writer with a knack for transforming simple ideas into 
    captivating narratives. Your role is to take a post idea and generate 
    potential story angles that would resonate with a LinkedIn audience.

linkedin_post_creator:
  role: >
    LinkedIn Post Creator
  goal: >
    Craft compelling LinkedIn posts based on the story ideas provided.
  backstory: >
    As a social media expert specializing in LinkedIn content, you excel at 
    creating posts that engage professionals and drive meaningful conversations. 
    Your posts are known for their blend of insightful content and strategic use 
    of LinkedIn's features.
```

```yaml
generate_story_ideas_task:
  description: >
    Based on the given post idea: {post_idea}, generate 3 potential story angles 
    that could be used to create an engaging LinkedIn post. Consider the 
    professional nature of LinkedIn and aim for stories that would resonate with 
    a business-oriented audience.
  expected_output: >
    A list of 3 story ideas, each with a title and brief description.

create_linkedin_post_task:
  description: >
    Using the story ideas generated from the previous task, create a compelling 
    LinkedIn post. The post should be engaging, professional, and tailored to 
    the LinkedIn audience. Include relevant hashtags that will increase the 
    post's visibility.
  expected_output: >
    A complete LinkedIn post including the main content and a list of relevant 
    hashtags.

```

## Next Steps
1. When the progress is 100, we want the UI to show that the task (with name in the field 'task') has been completed, so the existing alert turns a new color, takes the name of the task, and a new alert appears below with the next task name and the status.
For this, we will not only need to update the front end, but also the back-end to provide the new task id to check against (We assume that new task, new result ID)
Finally, when progress is 100, we should set the state to SUCCESS unless it's a FAILURE

This should continue until all tasks are completed in which case, all alerts should be a success, each with the name of their task.