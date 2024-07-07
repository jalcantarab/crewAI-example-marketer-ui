import logging
from marketing_posts.crew import MarketingPostsCrew

# Initialize logging
logging.basicConfig(filename='crew.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')


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
