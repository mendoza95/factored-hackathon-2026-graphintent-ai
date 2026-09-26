import networkx as nx
import time


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
        start_time = time.perf_counter()
        coloring = nx.coloring.greedy_color(self.graph, strategy="largest_first")
        self._last_execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        nx.set_node_attributes(self.graph, coloring, "color")

        batches: dict[int, list[str]] = {}

        for task, color in coloring.items():
            batches.setdefault(color, []).append(task)

        return batches

    def get_optimization_metrics(self) -> dict[str, float | int]:
        """Return execution and graph metrics for monitoring."""
        # Calculate chromatic number from assigned color attributes
        colors = {
            data.get("color")
            for _, data in self.graph.nodes(data=True)
            if "color" in data
        }
        chromatic_number = len(colors) if colors else 0

        return {
            "nodes_count": self.graph.number_of_nodes(),
            "edges_count": self.graph.number_of_edges(),
            "chromatic_number": chromatic_number,
            "total_execution_time_ms": round(self._last_execution_time_ms, 3),
        }
