import logging
import random
from collections import defaultdict

logger = logging.getLogger(__name__)

class ModelPerformanceTracker:
    """
    Tracks model performance based on the number of attempts needed to generate working tests.
    """

    def __init__(self):
        # Metrics: {model_name: {'executions': int, 'successes': int, 'failures': int, 'total_attempts': int}}
        self.metrics = defaultdict(lambda: {'executions': 0, 'successes': 0, 'failures': 0, 'total_attempts': 0})
    
    def record_execution(self, model_name, attempts, success=True):
        """
        Records a model's test generation attempt.
        
        :param model_name: Name of the model used.
        :param attempts: Number of tries it took to generate a passing test.
        :param success: Whether the generated test passed.
        """
        self.metrics[model_name]['executions'] += 1
        self.metrics[model_name]['total_attempts'] += attempts

        if success:
            self.metrics[model_name]['successes'] += 1
        else:
            self.metrics[model_name]['failures'] += 1
        
        logger.info(f"Recorded execution for {model_name}: attempts={attempts}, success={success}")

    def get_average_attempts(self, model_name):
        """
        Calculates the average number of attempts per successful test.
        """
        successes = self.metrics[model_name]['successes']
        total_attempts = self.metrics[model_name]['total_attempts']
        
        if successes == 0:
            return float('inf')  # If no successes, penalize heavily
        return total_attempts / successes

    def rank_models(self):
        """
        Returns a list of models sorted by the fewest average attempts needed for success.
        """
        ranking = {}
        for model in self.metrics:
            ranking[model] = self.get_average_attempts(model)

        sorted_models = sorted(ranking.items(), key=lambda x: x[1])  # Lower is better
        logger.info("Model ranking (lower avg attempts is better): " + str(sorted_models))
        return sorted_models

    def choose_model(self, epsilon=0.1):
        """
        Selects a model using an epsilon-greedy strategy:
        - With probability `epsilon`, explore (pick random).
        - Otherwise, exploit (pick the model requiring the fewest attempts).
        """
        ranked = self.rank_models()
        if not ranked:
            return None  # No data yet

        if random.random() < epsilon:
            # Exploration: pick a random model from tracked models
            model_names = list(self.metrics.keys())
            chosen = random.choice(model_names)
            logger.info(f"Epsilon-Greedy: Randomly selected {chosen}")
            return chosen
        else:
            # Exploitation: pick the best-ranked model (fewer avg attempts)
            chosen = ranked[0][0]
            logger.info(f"Epsilon-Greedy: Selected best model {chosen}")
            return chosen

    def print_metrics(self):
        """
        Prints model performance metrics.
        """
        for model, data in self.metrics.items():
            avg_attempts = self.get_average_attempts(model)
            logger.info(f"Model: {model} | Executions: {data['executions']} | Successes: {data['successes']} | "
                        f"Failures: {data['failures']} | Avg Attempts per Success: {avg_attempts:.2f}")

# ---------------------------
# Example Usage:
# ---------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    tracker = ModelPerformanceTracker()

    # Simulate executions with different models
    tracker.record_execution("O3-mini", attempts=1, success=True)
    tracker.record_execution("O3-mini", attempts=3, success=False)
    tracker.record_execution("O4", attempts=1, success=True)
    tracker.record_execution("O4", attempts=2, success=True)
    tracker.record_execution("O5-Async", attempts=4, success=False)

    tracker.print_metrics()
    ranking = tracker.rank_models()
    print("Final Ranking:", ranking)

    # Epsilon-greedy selection
    chosen_model = tracker.choose_model(epsilon=0.2)
    print("Chosen Model:", chosen_model)
