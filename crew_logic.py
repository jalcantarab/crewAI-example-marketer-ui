import logging
import sys
from marketing_posts.crew import MarketingPostsCrew

# Initialize logging
logging.basicConfig(filename='crew.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# Redirect stdout to logging


class StreamToLogger(object):
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass


sys.stdout = StreamToLogger(logging.getLogger('STDOUT'))
sys.stderr = StreamToLogger(logging.getLogger('STDERR'))


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
