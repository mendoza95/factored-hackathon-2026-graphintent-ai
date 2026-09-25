import networkx as nx


class GraphColoringScheduler:
    def __init__(self):
        self.graph = nx.Graph()

    def add_task(self, task_id: str):
        self.graph.add_node(task_id)

    def add_conflict(self, task_a: str, task_b: str):
        """
        Add an edge between two tasks that cannot run simultaneously.
        """
        self.graph.add_edge(task_a, task_b)

    def compute_schedule(self) -> dict[int, list[str]]:
        """
        Run Welsh-Powell greedy coloring
        to create conflict-free execution batches.

        """
        coloring = nx.coloring.greedy_color(self.graph, strategy="largest_first")
        batches: dict[int, list[str]] = {}

        for task, color in coloring.items():
            batches.setdefault(color, []).append(task)

        return batches
