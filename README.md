# Marketing Crew AI Web Application

This project leverages CrewAI to create a web-based interface where users can input a domain and project description to generate a comprehensive marketing strategy. The application uses Flask for the web interface, Celery for background task processing, and Redis as a message broker.

## Prerequisites

1. **Python 3.10+**: Ensure you have Python installed. You can download it from [Python.org](https://www.python.org/downloads/).
2. **Poetry**: A tool for dependency management and packaging in Python. Install it from [Poetry's official website](https://python-poetry.org/).
3. **Redis**: An in-memory data structure store used as a message broker for Celery. Installation instructions can be found on [Redis.io](https://redis.io/download).

## Setup Instructions

### Step 1: Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/marketing-crew-ai.git
cd marketing-crew-ai
```

### Step 2: Install Dependencies

Use Poetry to install the project dependencies:

```bash
poetry install
```

### Step 3: Set Up Redis

#### Install Redis

**On macOS**:
```bash
brew install redis
```

**On Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install redis-server
```

#### Start Redis Server

Start the Redis server before running the application:

```bash
redis-server
```

### Step 4: Configure and Run Celery

Open a new terminal window, activate the Poetry shell, and start the Celery worker:

```bash
poetry shell
poetry run celery -A app.celery worker --loglevel=info
```

### Step 5: Run the Flask Application

In another terminal window, also within the Poetry shell, run the Flask application:

```bash
poetry run python app.py
```

### Project Structure

```
project/
├── app.py                    # Flask application entry point
├── crew_logic.py             # Core logic separated from main
├── templates/
│   ├── index.html            # HTML form for user inputs
│   └── results.html          # HTML to display results
├── static/
│   └── style.css             # Optional CSS for styling
├── marketing_posts/          # CrewAI related scripts and configurations
│   ├── main.py
│   ├── crew.py
│   └── config/
│       ├── agents.yaml
│       └── tasks.yaml
└── README.md
```

### Usage

1. **Navigate to**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
2. **Fill out the form** with the domain and project description.
3. **Submit the form**. The task will be processed in the background, and you will see the status updates on the same page.
4. **View the results** once the task is completed.

### Notes

- Ensure Redis is running before starting the Celery worker and Flask application.
- The Celery worker must be running in a separate terminal window to handle background tasks.

### Troubleshooting

- If you encounter issues with Redis, ensure it is properly installed and running.
- Check that the Celery worker is active and connected to the Redis broker.
- Verify that all dependencies are installed via Poetry and that you are operating within the Poetry shell.