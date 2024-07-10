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
