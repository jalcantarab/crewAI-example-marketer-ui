# AI Agents Web UI: Project Definition

## Objective
To create a web interface that right now allows users to define domain and description of a product to create a marketing strategy, and we're going to change to just take a post idea and initiate a crew of AI agents using the CrewAI framework. The web interface provides real-time feedback on the progress and output of the agents.

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

#### 1. Flask Web Application (app.py)
```py
import socket
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
from typing import List, Callable
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from queue import Queue
import time

# Custom Logging Handler


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put(log_entry)


# Progress Tracking Callback
ProgressCallback = Callable[[str, float], None]


class MarketStrategy(BaseModel):
    name: str = Field(..., description="Name of the market strategy")
    tactics: List[str] = Field(...,
                               description="List of tactics to be used in the market strategy")
    channels: List[str] = Field(
        ..., description="List of channels to be used in the market strategy")
    KPIs: List[str] = Field(...,
                            description="List of KPIs to be used in the market strategy")


class CampaignIdea(BaseModel):
    name: str = Field(..., description="Name of the campaign idea")
    description: str = Field(...,
                             description="Description of the campaign idea")
    audience: str = Field(..., description="Audience of the campaign idea")
    channel: str = Field(..., description="Channel of the campaign idea")


class Copy(BaseModel):
    title: str = Field(..., description="Title of the copy")
    body: str = Field(..., description="Body of the copy")


@CrewBase
class MarketingPostsCrew():
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    log_queue: Queue = Queue()
    logger: logging.Logger = None
    progress_callback: ProgressCallback = None

    def __init__(self):
        self.setup_logging()

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

    @agent
    def lead_market_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['lead_market_analyst'],
            tools=[SerperDevTool(), ScrapeWebsiteTool()],
            verbose=True,
            memory=False,
            logger=self.logger
        )

    @agent
    def chief_marketing_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config['chief_marketing_strategist'],
            tools=[SerperDevTool(), ScrapeWebsiteTool()],
            verbose=True,
            memory=False,
            logger=self.logger
        )

    @agent
    def creative_content_creator(self) -> Agent:
        return Agent(
            config=self.agents_config['creative_content_creator'],
            verbose=True,
            memory=False,
            logger=self.logger
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
            agent=self.lead_market_analyst(),
            callback=lambda: self.log_progress("Research", 100)
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
            agent=self.lead_market_analyst(),
            callback=lambda _: self.log_progress("Research", 100)
        )

    @task
    def project_understanding_task(self) -> Task:
        return Task(
            config=self.tasks_config['project_understanding_task'],
            agent=self.chief_marketing_strategist(),
            callback=lambda _: self.log_progress("Project Understanding", 100)
        )

    @task
    def marketing_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config['marketing_strategy_task'],
            agent=self.chief_marketing_strategist(),
            output_json=MarketStrategy,
            callback=lambda _: self.log_progress("Marketing Strategy", 100)
        )

    @task
    def campaign_idea_task(self) -> Task:
        return Task(
            config=self.tasks_config['campaign_idea_task'],
            agent=self.creative_content_creator(),
            output_json=CampaignIdea,
            callback=lambda _: self.log_progress("Campaign Idea", 100)
        )

    @task
    def copy_creation_task(self) -> Task:
        return Task(
            config=self.tasks_config['copy_creation_task'],
            agent=self.creative_content_creator(),
            context=[self.marketing_strategy_task(), self.campaign_idea_task()],
            output_json=Copy,
            callback=lambda _: self.log_progress("Copy Creation", 100)
        )

    @crew
    def crew(self) -> Crew:
        self.logger.info('Creating the MarketingPosts crew')
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=2,
            logger=self.logger
        )

    def run(self, domain: str, description: str):
        self.logger.info(f"Starting MarketingPosts crew for domain: {domain}")
        self.log_progress("Overall", 0)

        crew = self.crew()
        result = crew.kickoff(
            inputs={"customer_domain": domain, "project_description": description})

        self.logger.info("MarketingPosts crew completed all tasks")
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
    <title>Marketing Strategy Generator</title>
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
        <h1 class="mb-4">Marketing Strategy Generator</h1>
        <form id="submitForm">
            <div class="mb-3">
                <label for="domain" class="form-label">Domain:</label>
                <input type="text" class="form-control" id="domain" name="domain" required>
            </div>
            <div class="mb-3">
                <label for="description" class="form-label">Project Description:</label>
                <textarea class="form-control" id="description" name="description" rows="4" required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Generate Strategy</button>
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
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    const socket = io();
    const statusElement = document.getElementById('status');
    const logsDiv = document.getElementById('logs');
    const progressContainer = document.getElementById('progress-container');
    const overallProgress = document.getElementById('overall-progress').querySelector('.progress-bar');
    const taskProgress = document.getElementById('task-progress');

    socket.on('connect', () => {
        console.log('Connected to server');
        updateStatus('Connected to server', 'info');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        updateStatus('Disconnected from server. Please refresh the page.', 'warning');
    });

    socket.on('log', (data) => {
        const logEntry = document.createElement('div');
        logEntry.textContent = data.message;
        logsDiv.appendChild(logEntry);
        logsDiv.scrollTop = logsDiv.scrollHeight;
    });

    socket.on('progress', (data) => {
        progressContainer.classList.remove('d-none');
        if (data.task === 'Overall') {
            updateOverallProgress(data.progress);
        } else {
            updateTaskProgress(data.task, data.progress);
        }
    });

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
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${task}: ${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
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
                    // Update progress based on the response
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
    }

    function displayResults(result) {
        // Implement this function to display the structured results
        console.log('Results:', result);
        // For example:
        const resultDiv = document.createElement('div');
        resultDiv.innerHTML = `
            <h3>Results</h3>
            <pre>${JSON.stringify(result, null, 2)}</pre>
        `;
        document.body.appendChild(resultDiv);
    }

    document.getElementById('submitForm').addEventListener('submit', submitForm);
</script>
</body>
</html>
```


#### 6. Agent & Task Definition (src/marketing_posts/config/agents.yaml & src/marketing_posts/config/tasks.yaml)
```yaml
lead_market_analyst:
  role: >
    Lead Market Analyst
  goal: >
    Conduct amazing analysis of the products and competitors, providing in-depth
    insights to guide marketing strategies.
  backstory: >
    As the Lead Market Analyst at a premier digital marketing firm, you specialize
    in dissecting online business landscapes.

chief_marketing_strategist:
  role: >
    Chief Marketing Strategist
  goal: >
    Synthesize amazing insights from product analysis to formulate incredible
    marketing strategies.
  backstory: >
    You are the Chief Marketing Strategist at a leading digital marketing agency,
    known for crafting bespoke strategies that drive success.

creative_content_creator:
  role: >
    Creative Content Creator
  goal: >
    Develop compelling and innovative content for social media campaigns, with a
    focus on creating high-impact ad copies.
  backstory: >
    As a Creative Content Creator at a top-tier digital marketing agency, you
    excel in crafting narratives that resonate with audiences. Your expertise
    lies in turning marketing strategies into engaging stories and visual
    content that capture attention and inspire action.

chief_creative_director:
  role: >
    Chief Creative Director
  goal: >
    Oversee the work done by your team to make sure it is the best possible and
    aligned with the product goals, review, approve, ask clarifying questions or
    delegate follow-up work if necessary.
  backstory: >
    You are the Chief Content Officer at a leading digital marketing agency
    specializing in product branding. You ensure your team crafts the best
    possible content for the customer.

```

```yaml
research_task:
  description: >
    Conduct a thorough research about the customer and competitors in the context
    of {customer_domain}.
    Make sure you find any interesting and relevant information given the
    current year is 2024.
    We are working with them on the following project: {project_description}.
  expected_output: >
    A complete report on the customer and their customers and competitors,
    including their demographics, preferences, market positioning and audience engagement.

project_understanding_task:
  description: >
    Understand the project details and the target audience for
    {project_description}.
    Review any provided materials and gather additional information as needed.
  expected_output: >
    A detailed summary of the project and a profile of the target audience.

marketing_strategy_task:
  description: >
    Formulate a comprehensive marketing strategy for the project
    {project_description} of the customer {customer_domain}.
    Use the insights from the research task and the project understanding
    task to create a high-quality strategy.
  expected_output: >
    A detailed marketing strategy document that outlines the goals, target
    audience, key messages, and proposed tactics, make sure to have name, tatics, channels and KPIs

campaign_idea_task:
  description: >
    Develop creative marketing campaign ideas for {project_description}.
    Ensure the ideas are innovative, engaging, and aligned with the overall marketing strategy.
  expected_output: >
    A list of 5 campaign ideas, each with a brief description and expected impact.

copy_creation_task:
  description: >
    Create marketing copies based on the approved campaign ideas for {project_description}.
    Ensure the copies are compelling, clear, and tailored to the target audience.
  expected_output: >
    Marketing copies for each campaign idea.

```

## Next Steps
1. Implement A simpler Crew of Agents and tasks, that take a large text field post idea description, and use a crew with two agents, one to think of possible stories to tell around that idea with the information available, and another one to take the possible stories and create a complete LinkedIn post for that idea.