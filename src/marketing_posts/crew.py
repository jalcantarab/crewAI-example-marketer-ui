import logging
from typing import Callable
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from queue import Queue

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

    def step_callback(self, agent, task, step):
        self.logger.info(
            f"Agent: {agent.role} - Task: {task.description[:50]}... - Step: {step}")
        # You can add more detailed logging or progress tracking here

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
