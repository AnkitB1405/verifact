"""Per-claim knowledge subgraph construction.

Owner: P3 (FR-22). NetworkX in-process, per ADR-003: a subgraph is at most a few
hundred nodes, so a graph server would add a service, a driver and a query
language to hold data that fits in a dict.

Transitivity is why a graph is needed at all rather than a single API lookup.
Wikidata records the Eiffel Tower's "located in the administrative territorial
entity" as the 7th arrondissement (Q259463), not Paris (Q90). Checking "the
Eiffel Tower is in Paris" against the direct statement alone would return
CONTRADICTED on a true claim. Walking the relation reaches Paris in two hops.

The node cap and hop limit are enforced, not advisory: an unbounded walk from a
well-connected entity would pull in a large part of Wikidata.
"""

from __future__ import annotations

import networkx as nx

from verifact.config import KGSettings, get_settings
from verifact.errors import RetrievalError
from verifact.logging import get_logger
from verifact.retrieval.clients import wikidata
from verifact.retrieval.clients.http import SafeClient

_log = get_logger(__name__)


def build_subgraph(
    client: SafeClient,
    root_qid: str,
    pids: tuple[str, ...],
    settings: KGSettings | None = None,
) -> nx.DiGraph:
    """Breadth-first subgraph from `root_qid`, following only `pids`.

    Restricting the walk to the predicates under test is what keeps the subgraph
    small: following every relation from a city would reach thousands of nodes in
    one hop, and none of them would be relevant to the claim.

    Nodes carry `label`; edges carry `pid`.
    """
    cfg = settings or get_settings().kg
    graph = nx.DiGraph()
    graph.add_node(root_qid)

    frontier = [root_qid]
    for hop in range(cfg.max_hops):
        next_frontier: list[str] = []
        for qid in frontier:
            if graph.number_of_nodes() >= cfg.max_nodes:
                _log.info(
                    "subgraph node cap reached",
                    extra={"root": root_qid, "cap": cfg.max_nodes, "hop": hop},
                )
                return graph
            try:
                entity = wikidata.fetch_entity(client, qid)
            except RetrievalError as exc:
                # A missing neighbour truncates the walk; it is not a failure of
                # the claim being checked.
                _log.info("subgraph node unavailable", extra={"qid": qid, "error": str(exc)})
                continue
            graph.nodes[qid]["label"] = wikidata.label_of(entity)
            for pid, values in wikidata.statements(entity).items():
                if pid not in pids:
                    continue
                for value in values:
                    if value.get("type") != "entity" or not value.get("qid"):
                        continue
                    target = value["qid"]
                    if target not in graph:
                        graph.add_node(target)
                        next_frontier.append(target)
                    graph.add_edge(qid, target, pid=pid)
        frontier = next_frontier
        if not frontier:
            break
    return graph


def reaches(graph: nx.DiGraph, source: str, target: str, max_hops: int) -> list[str] | None:
    """Shortest path from `source` to `target` within `max_hops`, or None.

    The path is returned rather than a boolean because it is the explanation
    shown to the user (FR-25): "Eiffel Tower -> 7th arrondissement -> Paris" is
    an auditable reason, whereas "true" is not.
    """
    if source not in graph or target not in graph:
        return None
    try:
        path = nx.shortest_path(graph, source, target)
    except nx.NetworkXNoPath:
        return None
    if len(path) - 1 > max_hops:
        return None
    return [str(node) for node in path]


def labelled_path(graph: nx.DiGraph, path: list[str]) -> list[str]:
    """Render a path as readable steps for the explanation payload."""
    out: list[str] = []
    for src, dst in zip(path, path[1:], strict=False):
        pid = graph.edges[src, dst].get("pid", "?")
        src_label = graph.nodes[src].get("label") or src
        dst_label = graph.nodes[dst].get("label") or dst
        out.append(f"{src_label} ({src}) --{pid}--> {dst_label} ({dst})")
    return out
