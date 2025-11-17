"""
ai_navigation.py
Experimental AI navigation script with pathfinding and 2D top-down rendering.

Features:
- Imports map_data from main.py (map generation)
- A* pathfinding algorithm for agent navigation
- Multiple AI agents with autonomous goal-seeking behavior
- 2D top-down view using Pygame
- Interactive controls: click to set goals, spawn/remove agents

Run:
    python src/testing/ai_navigation.py

Requirements:
    - Python 3.x
    - pygame (pip install pygame)
    - DarcKaste project structure (must be able to import from src/)

Controls:
    - Left Click: Set a goal for the selected agent (yellow agent)
    - Right Click: Spawn a new agent at click location
    - Delete: Remove selected agent
    - Tab: Cycle through agents
    - Space: Pause/unpause agents
    - ESC: Quit
"""

import pygame
import math
import sys
import heapq
from time import time
import os

# Add parent directory to import main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from main import generate_random_map, MAP_TILES_WIDTH, MAP_TILES_HEIGHT, TILE_SIZE
except ImportError as e:
    print(f"Error importing from main.py: {e}")
    print("Creating a fallback simple map...")
    # fallback map generation
    MAP_TILES_WIDTH = 32
    MAP_TILES_HEIGHT = 32
    TILE_SIZE = 32
    
    def generate_random_map():
        """Simple fallback map"""
        m = [[1]*MAP_TILES_WIDTH for _ in range(MAP_TILES_HEIGHT)]
        for y in range(2, MAP_TILES_HEIGHT-2):
            for x in range(2, MAP_TILES_WIDTH-2):
                m[y][x] = 0
        # add some walls
        for x in range(5, 15):
            m[10][x] = 1
        return m

# optional navmesh module (lightweight sampled visibility graph)
try:
    import navmesh
except Exception:
    navmesh = None

# ---------- A* Pathfinding ----------

class Node:
    def __init__(self, pos, g=0, h=0):
        self.pos = pos
        self.g = g  # cost from start
        self.h = h  # heuristic cost to goal
        self.f = g + h  # total estimated cost
        self.parent = None

    def __lt__(self, other):
        return self.f < other.f

def heuristic(a, b):
    """Euclidean distance heuristic (works for 8-connected grid)."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return math.hypot(dx, dy)

def is_walkable(map_data, x, y, radius=0.5):
    """Check if a position is walkable (not a wall)"""
    map_w = len(map_data[0]) if map_data else 0
    map_h = len(map_data) if map_data else 0
    if x < 0 or y < 0 or x >= map_w or y >= map_h:
        return False
    
    # check tile and neighbors for collision radius
    checks = [
        (int(x), int(y)),
        (int(x+radius), int(y)),
        (int(x-radius), int(y)),
        (int(x), int(y+radius)),
        (int(x), int(y-radius)),
    ]
    for cx, cy in checks:
        if 0 <= cx < map_w and 0 <= cy < map_h:
            if map_data[cy][cx] == 1:
                return False
    return True


def tile_walkable(map_data, x, y):
    """Check if a single tile is walkable (0). Bounds-checked.
    This is a lightweight helper used by A* so pathfinding matches tile occupancy.
    """
    map_w = len(map_data[0]) if map_data else 0
    map_h = len(map_data) if map_data else 0
    if x < 0 or y < 0 or x >= map_w or y >= map_h:
        return False
    return map_data[y][x] == 0

def astar(map_data, start, goal, max_iterations=10000):
    """A* pathfinding (grid-based). start and goal should be integer tile coords.
    Returns list of (x,y) tile coordinates from start to goal or [] if unreachable.
    """
    map_w = len(map_data[0]) if map_data else 0
    map_h = len(map_data) if map_data else 0
    sx, sy = int(start[0]), int(start[1])
    gx, gy = int(goal[0]), int(goal[1])
    if not (0 <= gx < map_w and 0 <= gy < map_h):
        return []
    if not tile_walkable(map_data, gx, gy):
        return []

    open_heap = []
    heapq.heappush(open_heap, (0 + heuristic((sx, sy), (gx, gy)), (sx, sy)))
    came_from = {}
    g_score = { (sx, sy): 0 }
    closed = set()

    iterations = 0
    while open_heap and iterations < max_iterations:
        iterations += 1
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == (gx, gy):
            # reconstruct path
            path = []
            node = current
            while node in came_from:
                path.append(node)
                node = came_from[node]
            path.append((sx, sy))
            return path[::-1]

        closed.add(current)
        cx, cy = current

        # 8-directional neighbors with costs
        neighbors = [((cx+1, cy), 1.0), ((cx-1, cy), 1.0), ((cx, cy+1), 1.0), ((cx, cy-1), 1.0),
                     ((cx+1, cy+1), 1.4142), ((cx+1, cy-1), 1.4142), ((cx-1, cy+1), 1.4142), ((cx-1, cy-1), 1.4142)]

        for (nx, ny), cost in neighbors:
            if not (0 <= nx < map_w and 0 <= ny < map_h):
                continue
            # require target tile to be free
            if not tile_walkable(map_data, nx, ny):
                continue

            # prevent cutting corners: if moving diagonally, ensure adjacent orthogonal tiles are free
            dx = nx - cx
            dy = ny - cy
            if dx != 0 and dy != 0:
                if not (tile_walkable(map_data, cx + dx, cy) and tile_walkable(map_data, cx, cy + dy)):
                    continue

            tentative_g = g_score.get(current, float('inf')) + cost
            if tentative_g < g_score.get((nx, ny), float('inf')):
                came_from[(nx, ny)] = current
                g_score[(nx, ny)] = tentative_g
                f = tentative_g + heuristic((nx, ny), (gx, gy))
                heapq.heappush(open_heap, (f, (nx, ny)))

    return []


def bresenham_line(x0, y0, x1, y1):
    """Yield integer grid coordinates on a line from (x0,y0) to (x1,y1) using Bresenham."""
    x0 = int(x0); y0 = int(y0); x1 = int(x1); y1 = int(y1)
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    if dx > dy:
        err = dx // 2
        while x != x1:
            yield x, y
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
        yield x, y
    else:
        err = dy // 2
        while y != y1:
            yield x, y
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
        yield x, y


def line_of_sight(map_data, a, b):
    """Return True if straight line from tile a to b doesn't cross blocked tiles."""
    for tx, ty in bresenham_line(a[0], a[1], b[0], b[1]):
        if not tile_walkable(map_data, tx, ty):
            return False
    return True


def smooth_path(map_data, path):
    """Simplify path by removing intermediate nodes that are unnecessary using line-of-sight checks."""
    if not path:
        return path
    new_path = [path[0]]
    i = 0
    N = len(path)
    while i < N - 1:
        # find farthest j that is visible from i
        j = N - 1
        while j > i + 1:
            if line_of_sight(map_data, path[i], path[j]):
                break
            j -= 1
        new_path.append(path[j])
        i = j
    return new_path


def catmull_rom_sample(points, samples_per_segment=8):
    """Sample a Catmull-Rom spline through `points` (list of (x,y)).
    Returns a list of sampled (x,y) points (continuous coordinates).
    If there are fewer than 2 points, returns points unchanged.
    """
    if not points:
        return []
    if len(points) < 2:
        return [(float(points[0][0]), float(points[0][1]))]

    # Ensure we have float tuples
    pts = [(float(x), float(y)) for x, y in points]
    # Pad endpoints for Catmull-Rom
    if len(pts) == 2:
        # linear interpolation between two points
        a, b = pts
        sampled = []
        for i in range(samples_per_segment + 1):
            t = i / samples_per_segment
            sampled.append((a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t))
        return sampled

    extended = [pts[0]] + pts + [pts[-1]]
    sampled = []
    for i in range(0, len(pts) - 1):
        # control points p0,p1,p2,p3 for segment between p1 and p2
        p0 = extended[i]
        p1 = extended[i + 1]
        p2 = extended[i + 2]
        p3 = extended[i + 3]
        for j in range(samples_per_segment):
            t = j / float(samples_per_segment)
            t2 = t * t
            t3 = t2 * t
            # Catmull-Rom spline (centripetal factor 0.5)
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            sampled.append((x, y))
    # include final point
    sampled.append(pts[-1])
    return sampled


def repair_curved_path(map_data, curved, radius=0.25, min_segment_clearance=0.6, max_gap=2.0):
    """Remove curve samples that are not walkable and perform a lightweight repair.

    Strategy:
    - Keep only samples where `is_walkable(map_data, x, y, radius)` is True.
    - If the filtered curve is too sparse or contains large gaps between consecutive
      kept samples (> `max_gap` tiles), return an empty list to signal fallback to raw path.
    - Return the cleaned list otherwise.

    This is a pragmatic approach: it avoids following curve points inside walls
    and falls back when the spline crosses obstacles in a way that can't be
    repaired simply.
    """
    if not curved:
        return []
    cleaned = []
    for (x, y) in curved:
        if is_walkable(map_data, x, y, radius):
            cleaned.append((x, y))

    if len(cleaned) < 2:
        return []

    # ensure there are no huge gaps between consecutive kept samples
    for a, b in zip(cleaned[:-1], cleaned[1:]):
        d = math.hypot(a[0] - b[0], a[1] - b[1])
        if d > max_gap:
            # gap too large -> spline crosses obstacle area; safer to fallback
            return []

    return cleaned


def is_path_blocked(map_data, agent_pos, path, path_index, check_distance=3.0):
    """Check if the upcoming path is blocked by walls or obstacles.
    
    Returns True if the path ahead is blocked, False if path looks clear.
    Checks the next few waypoints for walkability.
    """
    if not path or path_index >= len(path):
        return False
    
    # check next waypoints within check_distance tiles
    for i in range(path_index, min(path_index + 5, len(path))):
        waypoint = path[i]
        wx, wy = float(waypoint[0]), float(waypoint[1])
        # Check if waypoint and surrounding area is walkable
        if not is_walkable(map_data, wx, wy, radius=0.4):
            return True  # waypoint is blocked
        
        # also check if this waypoint is very far away (pathfinding might have gone obsolete)
        dist = math.hypot(wx - agent_pos[0], wy - agent_pos[1])
        if dist > check_distance and i < len(path) - 1:
            # if waypoint is far and not the final goal, suspect blockage
            break
    
    return False


def find_closest_reachable_goal(map_data, start, goal, search_radius=15):
    """Check if goal is reachable. If not, find closest reachable tile within search_radius.
    
    Returns (goal_tile, is_exact) where:
    - goal_tile: (x, y) integer tile coords
    - is_exact: True if the original goal was reachable, False if we had to find a fallback
    """
    goal_tile = (int(goal[0]), int(goal[1]))
    start_tile = (int(start[0]), int(start[1]))
    
    # check if goal is reachable via A*
    if tile_walkable(map_data, goal_tile[0], goal_tile[1]):
        path = astar(map_data, start_tile, goal_tile)
        if path:
            return goal_tile, True  # exact goal is reachable
    
    # goal is unreachable or not walkable; find closest walkable tile within search_radius
    map_w = len(map_data[0]) if map_data else 0
    map_h = len(map_data) if map_data else 0
    gx, gy = goal_tile
    
    best = None
    best_dist = float('inf')
    
    for dy in range(-search_radius, search_radius + 1):
        for dx in range(-search_radius, search_radius + 1):
            tx = gx + dx
            ty = gy + dy
            if 0 <= tx < map_w and 0 <= ty < map_h and tile_walkable(map_data, tx, ty):
                # check if this tile is reachable from start
                test_path = astar(map_data, start_tile, (tx, ty))
                if test_path:
                    dist = dx * dx + dy * dy
                    if dist < best_dist:
                        best_dist = dist
                        best = (tx, ty)
    
    if best:
        return best, False  # fallback goal found
    
    # no reachable goal found; return start as fallback
    return start_tile, False

# ---------- AI Agent ----------

# Distinct colors for agents
AGENT_COLORS = [
    (255, 100, 100),  # red
    (100, 255, 100),  # green
    (100, 100, 255),  # blue
    (255, 255, 100),  # yellow
    (255, 100, 255),  # magenta
    (100, 255, 255),  # cyan
    (255, 150, 100),  # orange
    (200, 100, 255),  # purple
]

class Agent:
    def __init__(self, x, y, agent_id=0):
        # store positions as floats in tile-space
        self.x = float(x)
        self.y = float(y)
        self.id = agent_id
        self.goal = None
        self.path = []  # list of integer tile coords
        self.path_index = 0
        self.speed = 2.2  # tiles per second (faster)
        self.radius = 0.25
        self.color = AGENT_COLORS[agent_id % len(AGENT_COLORS)]
        # stats
        self.goals_reached = 0
        self.last_path_length = 0
        # collision / replanning state
        self.stuck_frames = 0
        self.replan_threshold = 4  # frames before attempting replan
        self.replan_cooldown = 0.5  # seconds between replans
        self._last_replan_time = 0.0
        # curved path following
        self.curved_path = []
        self.curved_index = 0
        self.use_curves = True
        # group membership for cohesive movement
        self.group_id = None
        self.group_color = None

    def set_goal(self, gx, gy, map_data, path_cache=None, nav_nodes=None, nav_adj=None, use_navmesh=False):
        """Set a new goal and compute path. Uses integer tile coords for pathfinding.
        path_cache: optional dict to cache (start,goal)->path results
        """
        # goal is continuous world coords (in tile-space, can be fractional)
        self.goal = (float(gx), float(gy))
        start_tile = (int(self.x), int(self.y))
        
        # validate goal reachability; if unreachable, find closest reachable tile
        goal_tile, is_exact = find_closest_reachable_goal(map_data, (self.x, self.y), (gx, gy))
        if not is_exact:
            print(f"  Goal ({int(gx)}, {int(gy)}) unreachable; using closest reachable tile ({goal_tile[0]}, {goal_tile[1]})")
            self.goal = (float(goal_tile[0]) + 0.5, float(goal_tile[1]) + 0.5)
        
        cache_key = (start_tile, goal_tile)

        # attempt navmesh-based planning if requested and available
        if use_navmesh and navmesh is not None and nav_nodes and nav_adj:
            try:
                nav_path = navmesh.find_path_with_graph(nav_nodes, nav_adj, (self.x, self.y), (gx, gy))
            except Exception:
                nav_path = []
            if nav_path:
                # nav_path is list of continuous positions including start and goal
                # remove the first element (start) because agent is already there
                if len(nav_path) >= 2 and math.hypot(nav_path[0][0] - self.x, nav_path[0][1] - self.y) < 1e-3:
                    nav_path = nav_path[1:]
                self.path = [(float(px), float(py)) for px, py in nav_path]
                # build curved path if desired
                if self.use_curves and len(self.path) >= 2:
                    samples = max(6, int(6 * (self.speed / 1.5)))
                    self.curved_path = catmull_rom_sample(self.path, samples_per_segment=samples)
                    repaired = repair_curved_path(map_data, self.curved_path, radius=self.radius)
                    if repaired:
                        self.curved_path = repaired
                    else:
                        self.curved_path = []
                else:
                    self.curved_path = []
                self.curved_index = 0
                self.path_index = 0
                self.last_path_length = len(self.path)
                return

        if path_cache is not None and cache_key in path_cache:
            raw_path = path_cache[cache_key][:]
        else:
            raw_path = astar(map_data, start_tile, goal_tile)
            if path_cache is not None:
                path_cache[cache_key] = raw_path[:]

        # If direct line-of-sight exists from current pos to continuous goal, go straight there
        if line_of_sight(map_data, (int(self.x), int(self.y)), (goal_tile[0], goal_tile[1])):
            # direct path: use continuous target (clicked location)
            self.path = [(float(gx), float(gy))]
        else:
            # smooth the raw tile path (tile ints) then convert to continuous waypoints (tile centers)
            sm = smooth_path(map_data, raw_path)
            self.path = [(tx + 0.5, ty + 0.5) for (tx, ty) in sm]
            # ensure final exact clicked position is included (not just tile center)
            if len(self.path) == 0 or (abs(self.path[-1][0] - gx) > 1e-4 or abs(self.path[-1][1] - gy) > 1e-4):
                self.path.append((float(gx), float(gy)))

        # build curved sampled path (Catmull-Rom) for smooth following
        if self.use_curves and len(self.path) >= 2:
            # sample more densely for smoother curves; samples per segment proportional to speed
            samples = max(6, int(6 * (self.speed / 1.5)))
            self.curved_path = catmull_rom_sample(self.path, samples_per_segment=samples)
            # repair curved samples that fall inside walls; fallback to raw path if repair fails
            repaired = repair_curved_path(map_data, self.curved_path, radius=self.radius)
            if repaired:
                self.curved_path = repaired
            else:
                # disable curved following for this path (fall back to tile-center path)
                self.curved_path = []
        else:
            self.curved_path = []
        self.curved_index = 0

        self.path_index = 0
        self.last_path_length = len(self.path)

    def update(self, dt, map_data, agents=None):
        """Update agent position along path with avoidance and dynamic rerouting.
        Pass `agents` (list) for agent-agent avoidance.
        """
        if agents is None:
            agents = []

        if not self.path or self.path_index >= len(self.path):
            # if we had a goal and we've consumed the path, mark goal reached
            if self.goal and self.last_path_length > 0 and self.path_index >= len(self.path):
                self.goals_reached += 1
                self.goal = None
            return

        # select follow list: prefer curved path when available and valid, otherwise raw path
        follow = self.curved_path if (self.curved_path and self.use_curves and self.curved_index < len(self.curved_path)) else self.path
        if not follow:
            return
        # determine index into follow list
        if follow is self.curved_path:
            idx = self.curved_index
        else:
            idx = self.path_index
        # current target is a continuous waypoint (floats)
        target = follow[idx]
        tx = float(target[0])
        ty = float(target[1])
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        # use a smaller arrival threshold for continuous movement
        if dist < 0.08:
            # snap to waypoint
            self.x = tx
            self.y = ty
            if follow is self.curved_path:
                self.curved_index += 1
            else:
                self.path_index += 1
            return

        # desired movement toward target (continuous)
        move_dist = self.speed * dt

        # compute separation from nearby agents
        sep_x = 0.0
        sep_y = 0.0
        for other in agents:
            if other is self:
                continue
            odx = self.x - other.x
            ody = self.y - other.y
            od = math.hypot(odx, ody)
            min_sep = self.radius + other.radius + 0.05
            if od < 1e-5:
                sep_x += 0.01
                sep_y += 0.01
            elif od < min_sep:
                strength = (min_sep - od) * 4.0
                sep_x += (odx / od) * strength
                sep_y += (ody / od) * strength

        # apply separation scaled by dt
        sep_x *= dt
        sep_y *= dt

        # wall avoidance (repulsive force from nearby wall tiles)
        wall_x = 0.0
        wall_y = 0.0
        # influence radius in tiles
        influence = 1.2
        map_w = len(map_data[0]) if map_data else 0
        map_h = len(map_data) if map_data else 0
        min_tx = max(0, int(math.floor(self.x - influence)))
        max_tx = min(map_w - 1, int(math.ceil(self.x + influence)))
        min_ty = max(0, int(math.floor(self.y - influence)))
        max_ty = min(map_h - 1, int(math.ceil(self.y + influence)))
        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                # if tile is a wall, compute repulsion
                if 0 <= tx < map_w and 0 <= ty < map_h and map_data[ty][tx] == 1:
                    cx = tx + 0.5
                    cy = ty + 0.5
                    dxw = self.x - cx
                    dyw = self.y - cy
                    dw = math.hypot(dxw, dyw)
                    if dw < 1e-6:
                        # extremely close to wall center: push outward
                        push_x = (math.cos(self.id + tx) + 0.1)
                        push_y = (math.sin(self.id + ty) + 0.1)
                        wall_x += push_x
                        wall_y += push_y
                    elif dw < influence:
                        # linear falloff repulsion
                        strength = (influence - dw) / influence
                        wall_x += (dxw / dw) * strength * 1.25
                        wall_y += (dyw / dw) * strength * 1.25

        # scale wall avoidance by dt and merge into separation vector
        wall_x *= dt
        wall_y *= dt
        sep_x += wall_x
        sep_y += wall_y

        if dist > 0:
            mvx = (dx / dist) * min(move_dist, dist)
            mvy = (dy / dist) * min(move_dist, dist)
        else:
            mvx = mvy = 0.0

        new_x = self.x + mvx + sep_x
        new_y = self.y + mvy + sep_y

        moved = False
        # wall collision: radius-aware check
        if is_walkable(map_data, new_x, new_y, self.radius):
            self.x = new_x
            self.y = new_y
            moved = True
        else:
            # try slide on X
            if is_walkable(map_data, self.x + mvx + sep_x, self.y, self.radius):
                self.x += mvx + sep_x
                moved = True
            # try slide on Y
            elif is_walkable(map_data, self.x, self.y + mvy + sep_y, self.radius):
                self.y += mvy + sep_y
                moved = True
            else:
                moved = False
                # try small nudges in 8 directions to escape being exactly stuck to a wall
                nudge_dist = max(0.15, self.radius * 0.6)
                nudge_found = False
                for ang_deg in (0,45,90,135,180,225,270,315):
                    ang = math.radians(ang_deg)
                    nx = self.x + math.cos(ang) * nudge_dist
                    ny = self.y + math.sin(ang) * nudge_dist
                    if is_walkable(map_data, nx, ny, self.radius):
                        self.x = nx
                        self.y = ny
                        moved = True
                        nudge_found = True
                        break
                if nudge_found:
                    # small successful escape counts as movement
                    pass

        # update path progress if we moved close to the current waypoint
        if moved:
            self.stuck_frames = 0
            # if we've reached the waypoint due to movement, advance
            if math.hypot(tx - self.x, ty - self.y) < 0.06:
                self.x = tx
                self.y = ty
                if follow is self.curved_path:
                    self.curved_index += 1
                else:
                    self.path_index += 1
        else:
            self.stuck_frames += 1

        # check if path is blocked ahead; if so, trigger rerouting immediately
        if self.goal and self.path:
            follow_list = self.curved_path if (self.curved_path and self.use_curves) else self.path
            follow_idx = self.curved_index if follow_list is self.curved_path else self.path_index
            if is_path_blocked(map_data, (self.x, self.y), follow_list, follow_idx, check_distance=3.0):
                self.stuck_frames = max(self.stuck_frames, self.replan_threshold)

        # dynamic rerouting: if stuck for several frames, try replanning
        if self.goal and self.stuck_frames >= self.replan_threshold:
            now = time()
            if now - self._last_replan_time >= self.replan_cooldown:
                self._last_replan_time = now
                start_tile = (int(self.x), int(self.y))
                goal_tile = (int(self.goal[0]), int(self.goal[1]))
                new_path = astar(map_data, start_tile, goal_tile)
                if new_path:
                    self.path = smooth_path(map_data, new_path)
                    self.path_index = 0
                    self.last_path_length = len(self.path)
                    # rebuild curved path for the new route and repair it
                    if self.use_curves and len(self.path) >= 2:
                        samples = max(6, int(6 * (self.speed / 1.5)))
                        self.curved_path = catmull_rom_sample(self.path, samples_per_segment=samples)
                        repaired = repair_curved_path(map_data, self.curved_path, radius=self.radius)
                        if repaired:
                            self.curved_path = repaired
                        else:
                            self.curved_path = []
                        self.curved_index = 0
                    else:
                        self.curved_path = []
                self.stuck_frames = 0

    def draw(self, surface, tile_size, selected=False, font=None):
        """Draw agent on surface"""
        sx = int(self.x * tile_size)
        sy = int(self.y * tile_size)
        radius = max(3, int(self.radius * tile_size))
        color = (255, 255, 255) if selected else self.color
        pygame.draw.circle(surface, color, (sx, sy), radius)
        if selected:
            pygame.draw.circle(surface, (255, 255, 0), (sx, sy), radius + 2, 2)
        # draw ID
        if font is not None:
            txt = font.render(str(self.id), True, color)
            surface.blit(txt, (sx + radius + 2, sy - 6))
        # goal marker and line
        if self.goal:
            gx = int(self.goal[0] * tile_size)
            gy = int(self.goal[1] * tile_size)
            pygame.draw.line(surface, (100, 100, 200), (sx, sy), (gx, gy), 1)
            pygame.draw.circle(surface, (100, 150, 200), (gx, gy), 3, 1)
        # path visualization (few upcoming nodes)
        if self.path:
            for i in range(self.path_index, min(self.path_index + 8, len(self.path))):
                px = int(self.path[i][0] * tile_size)
                py = int(self.path[i][1] * tile_size)
                pygame.draw.circle(surface, (120, 120, 120), (px, py), 2)

# ---------- Navigation Demo ----------

class NavigationDemo:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('AI Navigation Demo (Top-Down 2D)')
        self.clock = pygame.time.Clock()

        # generate map
        print("Generating map...")
        self.map_data = generate_random_map()
        self.map_w = len(self.map_data[0])
        self.map_h = len(self.map_data)

        # calculate base tile size to fit in window
        self.base_tile_size = max(4, min(width // self.map_w, height // self.map_h))
        self.zoom = 1.0
        self.camera_x = 0
        self.camera_y = 0
        print(f"Map: {self.map_w}x{self.map_h}, base_tile_size: {self.base_tile_size}")

        self.agents = []
        self.selected_agent = None
        self.paused = False
        self.path_cache = {}
        # navmesh fields (built on demand)
        self.nav_nodes = None
        self.nav_adj = None
        self.use_navmesh = False
        self.small_font = pygame.font.SysFont('Consolas', 12)
        self.font = pygame.font.SysFont('Consolas', 14)
        # panning state
        self.panning = False
        self.pan_button = None
        self.pan_last = (0, 0)
        # debug toggles
        self.show_los = False
        self.spawn_agent(2, 2)  # spawn initial agent
        
    def spawn_agent(self, tx, ty):
        """Spawn a new agent at tile coordinates"""
        if tile_walkable(self.map_data, int(tx), int(ty)):
            agent = Agent(tx, ty, len(self.agents))
            self.agents.append(agent)
            self.selected_agent = agent
            # clear cache because starts changed
            self.path_cache.clear()
            print(f"Spawned agent {agent.id} at ({tx:.1f}, {ty:.1f})")

    def set_goal(self, px, py):
        """Set goal for selected agent at pixel coordinates (accounting for camera/zoom)"""
        if self.selected_agent:
            tile_size = self.base_tile_size * self.zoom
            world_x = (px + self.camera_x) / tile_size
            world_y = (py + self.camera_y) / tile_size
            self.selected_agent.set_goal(world_x, world_y, self.map_data, self.path_cache,
                                         nav_nodes=self.nav_nodes, nav_adj=self.nav_adj, use_navmesh=self.use_navmesh)
            print(f"Agent {self.selected_agent.id} moving to ({world_x:.1f}, {world_y:.1f})")

    def remove_agent(self, agent):
        """Remove an agent"""
        if agent in self.agents:
            self.agents.remove(agent)
            if self.selected_agent == agent:
                self.selected_agent = self.agents[0] if self.agents else None
            print(f"Removed agent {agent.id}")

    def cycle_agent(self):
        """Select next agent"""
        if self.agents:
            idx = self.agents.index(self.selected_agent) if self.selected_agent in self.agents else -1
            idx = (idx + 1) % len(self.agents)
            self.selected_agent = self.agents[idx]
            print(f"Selected agent {self.selected_agent.id}")

    def random_walkable_pos(self):
        """Return a random walkable tile position."""
        import random
        for _ in range(100):
            tx = random.randint(0, self.map_w - 1)
            ty = random.randint(0, self.map_h - 1)
            if tile_walkable(self.map_data, tx, ty):
                return (float(tx) + 0.5, float(ty) + 0.5)
        return (2.0, 2.0)  # fallback

    def spawn_random_goal(self):
        """Set a random goal for the selected agent."""
        if self.selected_agent:
            goal_pos = self.random_walkable_pos()
            self.selected_agent.set_goal(goal_pos[0], goal_pos[1], self.map_data, self.path_cache,
                                         nav_nodes=self.nav_nodes, nav_adj=self.nav_adj, use_navmesh=self.use_navmesh)
            print(f"Agent {self.selected_agent.id} set random goal at ({goal_pos[0]:.1f}, {goal_pos[1]:.1f})")

    def spawn_multiple_agents(self, count=5, group_proximity=5.0):
        """Spawn multiple agents with random positions and shared goals.
        
        Agents spawning within group_proximity distance will share similar goals,
        creating cohesive groups that move together toward the same destination area.
        Each group gets a unique color for path visualization.
        Goals are generated near the group's spawn center for tighter cohesion.
        """
        import random
        # group colors (distinct and contrasting)
        group_colors = [
            (255, 100, 100),  # red
            (100, 255, 100),  # green
            (100, 100, 255),  # blue
            (255, 255, 100),  # yellow
            (255, 100, 255),  # magenta
            (100, 255, 255),  # cyan
        ]
        
        new_agents = []
        agent_groups = []  # track which agents are in groups
        
        for _ in range(count):
            start_pos = self.random_walkable_pos()
            agent = Agent(start_pos[0], start_pos[1], len(self.agents))
            self.agents.append(agent)
            new_agents.append(agent)
            
            # find if this agent spawns near other newly spawned agents
            nearby_agents = []
            for other in new_agents[:-1]:  # check previously spawned agents
                dist = math.hypot(start_pos[0] - other.x, start_pos[1] - other.y)
                if dist < group_proximity:
                    nearby_agents.append(other)
            
            # if agent spawns near others, assign them to a group
            if nearby_agents:
                # find the group of the first nearby agent
                group_idx = None
                for i, group in enumerate(agent_groups):
                    if nearby_agents[0] in group:
                        group_idx = i
                        break
                
                if group_idx is not None:
                    # add to existing group
                    agent_groups[group_idx].append(agent)
                else:
                    # create new group with the nearby agents
                    new_group = nearby_agents + [agent]
                    agent_groups.append(new_group)
            else:
                # solo agent (no nearby spawns)
                agent_groups.append([agent])
        
        # assign goals and group colors: agents in same group share the same goal and color
        for group_idx, group in enumerate(agent_groups):
            if group:
                # calculate group center spawn location
                group_center_x = sum(a.x for a in group) / len(group)
                group_center_y = sum(a.y for a in group) / len(group)
                
                # generate goal near the group center (within a 15-tile radius for tightness)
                goal_radius = 15.0
                goal_attempts = 0
                shared_goal = None
                while goal_attempts < 50 and shared_goal is None:
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(5.0, goal_radius)  # minimum 5 tiles away, max 15
                    gx = group_center_x + math.cos(angle) * dist
                    gy = group_center_y + math.sin(angle) * dist
                    
                    # check if this goal position is walkable
                    if tile_walkable(self.map_data, int(gx), int(gy)):
                        shared_goal = (gx, gy)
                    goal_attempts += 1
                
                # fallback if we couldn't find a walkable goal nearby
                if shared_goal is None:
                    shared_goal = self.random_walkable_pos()
                
                # assign group color
                group_color = group_colors[group_idx % len(group_colors)]
                for agent in group:
                    agent.group_id = group_idx
                    agent.group_color = group_color
                    agent.set_goal(shared_goal[0], shared_goal[1], self.map_data, self.path_cache,
                                   nav_nodes=self.nav_nodes, nav_adj=self.nav_adj, use_navmesh=self.use_navmesh)
                    print(f"Spawned agent {agent.id} at ({agent.x:.1f}, {agent.y:.1f}) with shared group goal ({shared_goal[0]:.1f}, {shared_goal[1]:.1f}) [Group {group_idx}]")
        
        self.selected_agent = self.agents[-1] if self.agents else None

    def draw(self):
        """Render the scene"""
        self.screen.fill((20, 20, 30))
        tile_size = self.base_tile_size * self.zoom

        # draw map (only visible tiles)
        min_tx = max(0, int((self.camera_x) / tile_size) - 1)
        max_tx = min(self.map_w - 1, int((self.camera_x + self.width) / tile_size) + 1)
        min_ty = max(0, int((self.camera_y) / tile_size) - 1)
        max_ty = min(self.map_h - 1, int((self.camera_y + self.height) / tile_size) + 1)
        for y in range(min_ty, max_ty + 1):
            for x in range(min_tx, max_tx + 1):
                if self.map_data[y][x] == 1:
                    sx = int(x * tile_size - self.camera_x)
                    sy = int(y * tile_size - self.camera_y)
                    pygame.draw.rect(self.screen, (80, 80, 80), (sx, sy, int(tile_size), int(tile_size)))

        # draw path visualization: all tile waypoints for all agents (use group color if available, else cyan)
        for agent in self.agents:
            if agent.path:
                path_pts = []
                for (px, py) in agent.path[agent.path_index:]:
                    sx = int(px * tile_size - self.camera_x)
                    sy = int(py * tile_size - self.camera_y)
                    if -10 < sx < self.width + 10 and -10 < sy < self.height + 10:
                        path_pts.append((sx, sy))
                if len(path_pts) >= 2:
                    # use group color if agent is in a group, otherwise cyan
                    path_color = agent.group_color if agent.group_color else (0, 200, 200)
                    pygame.draw.lines(self.screen, path_color, False, path_pts, 2)  # thicker colored path polyline

        # draw navmesh debug (nodes and edges) if enabled
        if self.use_navmesh and getattr(self, 'nav_nodes', None) and getattr(self, 'nav_adj', None):
            for i, (nx, ny) in enumerate(self.nav_nodes):
                sx = int(nx * tile_size - self.camera_x)
                sy = int(ny * tile_size - self.camera_y)
                if -8 < sx < self.width + 8 and -8 < sy < self.height + 8:
                    pygame.draw.circle(self.screen, (180, 120, 180), (sx, sy), 2)
                    for (j, cost) in self.nav_adj.get(i, [])[:4]:
                        bx, by = self.nav_nodes[j]
                        bsx = int(bx * tile_size - self.camera_x)
                        bsy = int(by * tile_size - self.camera_y)
                        pygame.draw.aaline(self.screen, (100, 80, 100), (sx, sy), (bsx, bsy))

        # draw grid (sparse for large zoom-outs)
        if tile_size > 6:
            for x in range(0, int(self.map_w * tile_size), int(tile_size)):
                sx = x - self.camera_x
                if -1 < sx < self.width:
                    pygame.draw.line(self.screen, (40, 40, 50), (sx, 0), (sx, self.height), 1)
            for y in range(0, int(self.map_h * tile_size), int(tile_size)):
                sy = y - self.camera_y
                if -1 < sy < self.height:
                    pygame.draw.line(self.screen, (40, 40, 50), (0, sy), (self.width, sy), 1)

        # draw group areas (convex hulls or bounding circles around grouped agents)
        groups = {}
        for agent in self.agents:
            if agent.group_id is not None:
                if agent.group_id not in groups:
                    groups[agent.group_id] = []
                groups[agent.group_id].append(agent)
        
        for group_id, group_agents in groups.items():
            if len(group_agents) > 1:  # only draw areas for groups with 2+ agents
                # calculate bounding circle (center and radius)
                group_x = sum(a.x for a in group_agents) / len(group_agents)
                group_y = sum(a.y for a in group_agents) / len(group_agents)
                max_dist = max(math.hypot(a.x - group_x, a.y - group_y) for a in group_agents)
                radius = max_dist + 1.5  # add buffer around agents
                
                # get group color (from first agent in group)
                group_color = group_agents[0].group_color if group_agents[0].group_color else (100, 100, 100)
                
                # convert to screen coords
                screen_cx = int(group_x * tile_size - self.camera_x)
                screen_cy = int(group_y * tile_size - self.camera_y)
                screen_radius = int(radius * tile_size)
                
                # draw semi-transparent circle
                if -screen_radius < screen_cx < self.width + screen_radius and -screen_radius < screen_cy < self.height + screen_radius:
                    # draw as unfilled circle with semi-transparent overlay
                    pygame.draw.circle(self.screen, group_color, (screen_cx, screen_cy), screen_radius, 1)

        # draw agents
        for agent in self.agents:
            is_sel = agent == self.selected_agent
            # transform agent world coords to screen coords
            sx = int(agent.x * tile_size - self.camera_x)
            sy = int(agent.y * tile_size - self.camera_y)
            radius = max(3, int(agent.radius * tile_size))
            color = (255, 255, 255) if is_sel else agent.color
            pygame.draw.circle(self.screen, color, (sx, sy), radius)
            if is_sel:
                pygame.draw.circle(self.screen, (255, 255, 0), (sx, sy), radius + 2, 2)

            # agent ID
            txt = self.small_font.render(str(agent.id), True, color)
            self.screen.blit(txt, (sx + radius + 2, sy - 6))

            # goal and path
            if agent.goal:
                gx = int(agent.goal[0] * tile_size - self.camera_x)
                gy = int(agent.goal[1] * tile_size - self.camera_y)
                pygame.draw.line(self.screen, (100, 100, 200), (sx, sy), (gx, gy), 1)
                pygame.draw.circle(self.screen, (100, 150, 200), (gx, gy), 3, 1)
            if agent.path:
                for i in range(agent.path_index, min(agent.path_index + 10, len(agent.path))):
                    px = int(agent.path[i][0] * tile_size - self.camera_x)
                    py = int(agent.path[i][1] * tile_size - self.camera_y)
                    if -5 < px < self.width + 5 and -5 < py < self.height + 5:
                        pygame.draw.circle(self.screen, (100, 100, 100), (px, py), 2)

            # draw curved path (smooth) if present
            if getattr(agent, 'curved_path', None):
                pts = []
                for (cxp, cyp) in agent.curved_path:
                    sxp = int(cxp * tile_size - self.camera_x)
                    syp = int(cyp * tile_size - self.camera_y)
                    pts.append((sxp, syp))
                if len(pts) >= 2:
                    pygame.draw.lines(self.screen, (180, 180, 255), False, pts, 2)

        # HUD Statistics
        font = self.font
        y_pos = 10
        stats_lines = [
            f'Agents: {len(self.agents)} | FPS: {int(self.clock.get_fps())} | Zoom: {self.zoom:.1f}x',
            f'Cache: {len(self.path_cache)} | Paused: {self.paused}',
            f'NavNodes: {len(self.nav_nodes) if getattr(self, "nav_nodes", None) else 0} | UseNavmesh: {self.use_navmesh}',
        ]
        for line in stats_lines:
            txt = font.render(line, True, (200, 200, 200))
            self.screen.blit(txt, (10, y_pos))
            y_pos += 20

        if self.selected_agent:
            agent = self.selected_agent
            agent_info = [
                f'Agent {agent.id}: pos=({agent.x:.1f}, {agent.y:.1f})',
                f'Goal reached: {agent.goals_reached} | Path length: {agent.last_path_length}',
                f'Path progress: {agent.path_index}/{len(agent.path)}',
            ]
            for line in agent_info:
                txt = font.render(line, True, agent.color)
                self.screen.blit(txt, (10, y_pos))
                y_pos += 18

        # Controls (split across two lines for clarity)
        txt = font.render('LClick: Goal | RClick: Spawn | Tab: Cycle | Del: Remove | G: Random Goal | M: Multi-Spawn (5) | N: Navmesh | Esc: Quit', True, (150, 150, 150))
        self.screen.blit(txt, (10, self.height - 40))
        txt2 = font.render('Path: cyan | Curve: blue | Space: Pause | Zoom: Scroll | Pan: Arrow keys/WASD/Ctrl+Drag', True, (150, 150, 150))
        self.screen.blit(txt2, (10, self.height - 20))

    def main_loop(self):
        """Main loop"""
        running = True
        prev_time = time()
        
        while running:
            now = time()
            dt = min(now - prev_time, 0.016)  # cap at ~60 FPS for dt
            prev_time = now
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        break
                    if event.key == pygame.K_l:
                        self.show_los = not self.show_los
                        print(f"Show LOS: {self.show_los}")
                    if event.key == pygame.K_n:
                        # toggle navmesh on/off; build on first use
                        if not self.use_navmesh:
                            if navmesh is None:
                                print("Navmesh module not available.")
                            else:
                                print("Building navmesh (sample=2, connect_radius=8)...")
                                try:
                                    self.nav_nodes, self.nav_adj = navmesh.build_nav_graph(self.map_data, sample=2, connect_radius=8, los_fn=line_of_sight)
                                    self.use_navmesh = True
                                    print(f"Navmesh built: nodes={len(self.nav_nodes)}, edges~={sum(len(v) for v in self.nav_adj.values())}")
                                except Exception as e:
                                    print(f"Navmesh build failed: {e}")
                        else:
                            self.use_navmesh = False
                            print("Navmesh disabled")
                    if event.key == pygame.K_TAB:
                        self.cycle_agent()
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                        print(f"Paused: {self.paused}")
                    if event.key == pygame.K_DELETE:
                        if self.selected_agent:
                            self.remove_agent(self.selected_agent)
                    if event.key == pygame.K_g:
                        # spawn random goal for selected agent
                        self.spawn_random_goal()
                    if event.key == pygame.K_m:
                        # spawn multiple agents with random goals (up to 10 total)
                        count = 5
                        self.spawn_multiple_agents(count)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # start panning with middle mouse or Ctrl+left-drag
                    mods = pygame.key.get_mods()
                    is_ctrl = mods & pygame.KMOD_CTRL
                    if event.button == 2 or (event.button == 1 and is_ctrl):
                        self.panning = True
                        self.pan_button = event.button
                        self.pan_last = event.pos
                        continue
                    if event.button == 1:  # left click = set goal
                        self.set_goal(event.pos[0], event.pos[1])
                    if event.button == 3:  # right click = spawn
                        tile_size = self.base_tile_size * self.zoom
                        tx = (event.pos[0] + self.camera_x) / tile_size
                        ty = (event.pos[1] + self.camera_y) / tile_size
                        self.spawn_agent(tx, ty)
                    if event.button == 4:  # scroll up = zoom in
                        self.zoom = min(self.zoom * 1.12, 3.0)
                    if event.button == 5:  # scroll down = zoom out
                        self.zoom = max(self.zoom / 1.12, 0.3)
                if event.type == pygame.MOUSEBUTTONUP:
                    # stop panning
                    if event.button == 2 or (event.button == 1 and (pygame.key.get_mods() & pygame.KMOD_CTRL)):
                        self.panning = False
                        self.pan_button = None
                if event.type == pygame.MOUSEMOTION:
                    if self.panning:
                        # pan camera opposite of mouse motion so drag feels natural
                        dx, dy = event.rel
                        self.camera_x -= dx
                        self.camera_y -= dy
                        # update last position
                        self.pan_last = event.pos
            
            # update agents
            if not self.paused:
                for agent in self.agents:
                    agent.update(dt, self.map_data, self.agents)

            # clamp camera to world bounds
            tile_size = self.base_tile_size * self.zoom
            max_camera_x = max(0, int(self.map_w * tile_size) - self.width)
            max_camera_y = max(0, int(self.map_h * tile_size) - self.height)
            self.camera_x = max(0, min(self.camera_x, max_camera_x))
            self.camera_y = max(0, min(self.camera_y, max_camera_y))

            # draw
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

            # handle camera pan with arrow keys or WASD
            keys = pygame.key.get_pressed()
            pan_speed = max(4, int(8 * (1.0 / max(self.zoom, 0.001))))
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.camera_x -= pan_speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.camera_x += pan_speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.camera_y -= pan_speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.camera_y += pan_speed
        
        pygame.quit()

# ---------- Run demo ----------

if __name__ == '__main__':
    demo = NavigationDemo(800, 600)
    demo.main_loop()
