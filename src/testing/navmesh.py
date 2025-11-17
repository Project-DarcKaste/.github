"""
navmesh.py
Simple navmesh-like visibility graph builder and graph A* helpers for the experimental demo.

This is intentionally lightweight and pragmatic:
- Samples walkable space on a coarse grid (configurable `sample` parameter)
- Builds visibility edges between sampled nodes within `connect_radius` tiles using line-of-sight
- Provides graph-based A* (`graph_astar`) and a helper to find a path using an existing graph

Notes:
- For small maps this is perfectly fine; for large maps you can increase `sample` to reduce node count.
- The demo (`ai_navigation.py`) uses this module as an optional planner.
"""

import math

# The demo re-uses its own line-of-sight and tile helpers; to avoid circular imports,
# we accept a `los_fn` parameter where required. Caller can pass ai_navigation.line_of_sight.


def build_nav_graph(map_data, sample=2, connect_radius=8, los_fn=None):
    """Builds a sampled visibility graph from `map_data`.
    - `sample`: sample every N tiles in both axes
    - `connect_radius`: maximum distance (in tiles) to attempt an edge
    - `los_fn`: optional function `los_fn(a_tile, b_tile) -> bool` that checks line-of-sight in tile coordinates.

    Returns (nodes, adj) where:
    - nodes: list of (x,y) continuous positions (tile-space, centers)
    - adj: dict {i: [(j, cost), ...], ...}
    """
    map_h = len(map_data)
    map_w = len(map_data[0]) if map_h else 0
    nodes = []
    # sample centers
    for ty in range(0, map_h, sample):
        for tx in range(0, map_w, sample):
            cx = tx + 0.5
            cy = ty + 0.5
            # require the local tile to be walkable
            if 0 <= tx < map_w and 0 <= ty < map_h and map_data[ty][tx] == 0:
                nodes.append((cx, cy))
    # include additional border samples to help coverage
    if (map_w - 1) % sample != 0:
        for ty in range(0, map_h, sample):
            tx = map_w - 1
            if map_data[ty][tx] == 0:
                nodes.append((tx + 0.5, ty + 0.5))
    if (map_h - 1) % sample != 0:
        for tx in range(0, map_w, sample):
            ty = map_h - 1
            if map_data[ty][tx] == 0:
                nodes.append((tx + 0.5, ty + 0.5))

    # build adjacency by testing LOS between nearby nodes
    adj = {i: [] for i in range(len(nodes))}
    max_r2 = (connect_radius + 0.001) ** 2
    for i, a in enumerate(nodes):
        ax, ay = a
        for j in range(i + 1, len(nodes)):
            bx, by = nodes[j]
            dx = bx - ax
            dy = by - ay
            d2 = dx * dx + dy * dy
            if d2 <= max_r2:
                # use los_fn if available (caller should pass ai_navigation.line_of_sight)
                ok = True
                if los_fn is not None:
                    # los_fn expects tile coords; convert centers back to tile ints
                    ok = los_fn((int(ax), int(ay)), (int(bx), int(by)))
                if ok:
                    cost = math.hypot(dx, dy)
                    adj[i].append((j, cost))
                    adj[j].append((i, cost))
    return nodes, adj


def nearest_node(nodes, pos):
    """Return index of nearest node to pos=(x,y)."""
    best = None
    bestd = float('inf')
    px, py = pos
    for i, (nx, ny) in enumerate(nodes):
        d = (nx - px) ** 2 + (ny - py) ** 2
        if d < bestd:
            bestd = d
            best = i
    return best


def graph_astar(nodes, adj, start_idx, goal_idx):
    """A* over the nav-graph (nodes + adjacency). Returns list of node indices or [] if no path."""
    if start_idx is None or goal_idx is None:
        return []
    import heapq
    def heuristic(i, j):
        ax, ay = nodes[i]
        bx, by = nodes[j]
        return math.hypot(ax - bx, ay - by)

    open_heap = []
    heapq.heappush(open_heap, (heuristic(start_idx, goal_idx), start_idx))
    came_from = {}
    gscore = {start_idx: 0.0}
    closed = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal_idx:
            # rebuild
            path = []
            node = current
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.append(start_idx)
            return path[::-1]
        closed.add(current)
        for (nb, cost) in adj.get(current, []):
            if nb in closed:
                continue
            tentative = gscore.get(current, float('inf')) + cost
            if tentative < gscore.get(nb, float('inf')):
                came_from[nb] = current
                gscore[nb] = tentative
                f = tentative + heuristic(nb, goal_idx)
                heapq.heappush(open_heap, (f, nb))
    return []


def find_path_with_graph(nodes, adj, start_pos, goal_pos):
    """Find a continuous path using an existing nav-graph (nodes, adj).
    Returns a list of (x,y) positions including start and goal if a path exists, otherwise []
    """
    if not nodes or not adj:
        return []
    s_idx = nearest_node(nodes, start_pos)
    g_idx = nearest_node(nodes, goal_pos)
    if s_idx is None or g_idx is None:
        return []
    idx_path = graph_astar(nodes, adj, s_idx, g_idx)
    if not idx_path:
        return []
    # convert indices to positions and add exact start/goal at ends
    path = [start_pos]
    for i in idx_path:
        path.append(nodes[i])
    path.append(goal_pos)
    # collapse near-duplicates
    out = [path[0]]
    for p in path[1:]:
        if math.hypot(out[-1][0] - p[0], out[-1][1] - p[1]) > 1e-4:
            out.append(p)
    return out


# Lightweight convenience: build graph and query in one call
def find_path(map_data, start_pos, goal_pos, sample=2, connect_radius=8, los_fn=None):
    nodes, adj = build_nav_graph(map_data, sample=sample, connect_radius=connect_radius, los_fn=los_fn)
    return find_path_with_graph(nodes, adj, start_pos, goal_pos), nodes, adj
