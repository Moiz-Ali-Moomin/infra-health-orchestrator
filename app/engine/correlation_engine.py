from typing import List, Dict, Any
import yaml
import networkx as nx
from app.engine.models import CheckResultDTO, CheckStatus, CorrelationContextDTO
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CorrelationEngine:
    """
    Principal-tier DAG Topological Correlation Engine.
    Leverages networkx and a YAML definition to identify structural root causes
    and map cascading failure blast radii mathematically rather than procedurally.
    """

    def __init__(self, topology_path: str):
        self.topology_path = topology_path
        self.graph = nx.DiGraph()
        self._load_topology()
        
    def _load_topology(self):
        try:
            with open(self.topology_path, 'r') as f:
                data = yaml.safe_load(f)
                
            for node in data.get('nodes', []):
                self.graph.add_node(node['id'])
                
            for edge in data.get('edges', []):
                # source -> target (e.g., http_check depends on database_check)
                self.graph.add_edge(edge['from'], edge['to'])
                
            logger.info(f"Loaded topological correlation graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
        except Exception as e:
            logger.error(f"Failed to load topology graph from {self.topology_path}: {e}")

    def correlate_failures(self, check_results: List[CheckResultDTO]) -> CorrelationContextDTO:
        failed_checks = {r.check_type for r in check_results if r.status != CheckStatus.HEALTHY}
        
        if not failed_checks:
            return CorrelationContextDTO(root_cause_identified=None, impacted_dependencies=[])
            
        if self.graph.number_of_nodes() == 0:
            # Fallback if topology missing
            return CorrelationContextDTO(
                root_cause_identified=next(iter(failed_checks)),
                impacted_dependencies=list(failed_checks)
            )

        root_cause = None
        
        # In a directed graph Dependency -> Upstream (Http -> DB).
        # We look for the "deepest" failing node that has other failing nodes depending on it.
        # Alternatively, we find the failing node with zero failing OUT-EDGES (dependencies).
        
        candidate_roots = []
        for failed_node in failed_checks:
            if failed_node not in self.graph:
                continue
                
            # If the node's dependencies (out-edges) are healthy (not in failed_checks),
            # then this node is structurally failing on its own.
            descendants = nx.descendants(self.graph, failed_node)
            failing_dependencies = descendants.intersection(failed_checks)
            
            if not failing_dependencies:
                candidate_roots.append(failed_node)
                
        if len(candidate_roots) == 1:
            root_cause = candidate_roots[0]
        elif len(candidate_roots) > 1:
            # Multiple independent structural failures
            root_cause = "multiple_independent_failures"
        else:
            # Cycle or isolated node fallback
            root_cause = next(iter(failed_checks))

        # Blast radius (all ancestors that depend on the root cause)
        impacted = []
        if root_cause and root_cause in self.graph:
            ancestors = nx.ancestors(self.graph, root_cause)
            impacted = list(ancestors.intersection(failed_checks))

        return CorrelationContextDTO(
            root_cause_identified=root_cause,
            impacted_dependencies=impacted
        )

