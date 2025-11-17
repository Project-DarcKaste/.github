"""
rasterizer_demo.py
Standalone software rasterizer demo in Python + Pygame.

Features:
- Simple 3D math (no external deps)
- Perspective projection
- Triangle rasterization using barycentric coordinates
- Z-buffer (depth buffer) to resolve occlusion
- Back-face culling
- Simple directional lighting (flat shading)
- Rotating cube model hardcoded

Run:
    python src/rasterizer_demo.py

Requirements:
    - Python 3.x
    - pygame (pip install pygame)

This file is intentionally standalone and does not reference other project files.
"""

import pygame
import math
import sys
from time import time

# ---------- Math helpers ----------

def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec_mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def cross(a, b):
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    )

def normalize(a):
    length = math.sqrt(dot(a, a))
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (a[0]/length, a[1]/length, a[2]/length)

# ---------- Transformations ----------

def rotate_x(v, a):
    ca = math.cos(a); sa = math.sin(a)
    y = v[1]*ca - v[2]*sa
    z = v[1]*sa + v[2]*ca
    return (v[0], y, z)

def rotate_y(v, a):
    ca = math.cos(a); sa = math.sin(a)
    x = v[2]*sa + v[0]*ca
    z = v[2]*ca - v[0]*sa
    return (x, v[1], z)

def rotate_z(v, a):
    ca = math.cos(a); sa = math.sin(a)
    x = v[0]*ca - v[1]*sa
    y = v[0]*sa + v[1]*ca
    return (x, y, v[2])

# ---------- Projection ----------

def project(v, width, height, fov, near=0.1):
    # simple perspective projection
    # v is assumed in camera space with z > 0 in front of camera
    f = 1.0 / math.tan(fov * 0.5)
    x = v[0] * f / max(v[2], near)
    y = v[1] * f / max(v[2], near)
    # map to screen coords
    sx = int((x + 1) * 0.5 * width)
    sy = int((1 - (y + 1) * 0.5) * height)
    return (sx, sy, v[2])

# ---------- Triangle utilities ----------

def edge_function(a, b, c):
    return (c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])

# ---------- Model (cube) ----------

CUBE_VERTS = [
    (-1, -1, -1),
    ( 1, -1, -1),
    ( 1,  1, -1),
    (-1,  1, -1),
    (-1, -1,  1),
    ( 1, -1,  1),
    ( 1,  1,  1),
    (-1,  1,  1),
]

# triangles as tuples of vertex indices (clockwise winding)
CUBE_TRIS = [
    # back face
    (0,1,2),(0,2,3),
    # front face
    (4,6,5),(4,7,6),
    # left
    (0,3,7),(0,7,4),
    # right
    (1,5,6),(1,6,2),
    # top
    (3,2,6),(3,6,7),
    # bottom
    (0,4,5),(0,5,1)
]

# ---------- Rasterizer ----------

class Rasterizer:
    def __init__(self, width=640, height=480):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Software Rasterizer Demo')
        self.clock = pygame.time.Clock()
        # render to a smaller buffer then upscale to window for performance
        self.scale = 2  # factor to downscale rendering (2 => render at half resolution)
        self.buf_w = max(2, width // self.scale)
        self.buf_h = max(2, height // self.scale)
        self.buffer = pygame.Surface((self.buf_w, self.buf_h))
        # simple z-buffer initialized to very far for buffer resolution
        self.zbuffer = [ [float('inf')] * self.buf_w for _ in range(self.buf_h) ]
        # PixelArray used per-frame for faster pixel writes (created each frame)
        self._pixelarray = None
        self._map_rgb = None

    def clear(self, color=(0,0,0)):
        # clear the offscreen buffer and reset zbuffer
        self.buffer.fill(color)
        inf = float('inf')
        for y in range(self.buf_h):
            row = self.zbuffer[y]
            for x in range(self.buf_w):
                row[x] = inf

    def draw_triangle(self, p0, p1, p2, color):
        # p0, p1, p2 are (sx, sy, z) screen coords
        min_x = max(min(p0[0], p1[0], p2[0],), 0)
        max_x = min(max(p0[0], p1[0], p2[0],), self.buf_w-1)
        min_y = max(min(p0[1], p1[1], p2[1],), 0)
        max_y = min(max(p0[1], p1[1], p2[1],), self.buf_h-1)

        area = edge_function(p0, p1, p2)
        if area == 0:
            return

        # attempt to use PixelArray for faster bulk writes; fallback to set_at if not available
        px = self._pixelarray
        if px is not None:
            color_int = self._map_rgb(color)
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    p = (x + 0.5, y + 0.5)
                    w0 = edge_function(p1, p2, p)
                    w1 = edge_function(p2, p0, p)
                    w2 = edge_function(p0, p1, p)
                    if (w0 >= 0 and w1 >= 0 and w2 >= 0) or (w0 <= 0 and w1 <= 0 and w2 <= 0):
                        w0f = w0 / area
                        w1f = w1 / area
                        w2f = w2 / area
                        z = w0f * p0[2] + w1f * p1[2] + w2f * p2[2]
                        if z < self.zbuffer[y][x]:
                            self.zbuffer[y][x] = z
                            px[x, y] = color_int
        else:
            # fallback (slower)
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    p = (x + 0.5, y + 0.5)
                    w0 = edge_function(p1, p2, p)
                    w1 = edge_function(p2, p0, p)
                    w2 = edge_function(p0, p1, p)
                    if (w0 >= 0 and w1 >= 0 and w2 >= 0) or (w0 <= 0 and w1 <= 0 and w2 <= 0):
                        w0f = w0 / area
                        w1f = w1 / area
                        w2f = w2 / area
                        z = w0f * p0[2] + w1f * p1[2] + w2f * p2[2]
                        if z < self.zbuffer[y][x]:
                            self.zbuffer[y][x] = z
                            self.buffer.set_at((x,y), color)

    def render_model(self, verts, tris, model_transform, view_pos, light_dir, fov):
        # verts: list of 3-tuples in model space
        transformed = []
        # model_transform: function to apply to each vertex
        for v in verts:
            tv = model_transform(v)
            transformed.append(tv)

        # simple camera: camera at origin looking down +Z (we'll translate by -view_pos)
        projected = []
        for v in transformed:
            # move into camera space (translate by -view_pos)
            cam = vec_sub(v, view_pos)
            # ignore points behind the camera (z <= 0) by clamping to near positive small value later
            proj = project(cam, self.buf_w, self.buf_h, fov)
            projected.append((proj[0], proj[1], cam[2]))

        # draw triangles
        for tri in tris:
            i0, i1, i2 = tri
            v0 = transformed[i0]
            v1 = transformed[i1]
            v2 = transformed[i2]
            # compute face normal in camera/view space for back-face culling and lighting
            a = vec_sub(v1, v0)
            b = vec_sub(v2, v0)
            normal = normalize(cross(a, b))
            # face facing camera? dot(normal, view_dir) < 0
            # view_dir = vector from surface to camera (camera at view_pos; here we used cam coords so camera is at origin)
            view_dir = normalize(vec_mul(v0, -1.0))
            if dot(normal, view_dir) <= 0:
                continue  # back-face culled
            # simple flat shading
            intensity = max(0.0, dot(normal, normalize(light_dir)))
            base_color = (180, 180, 180)
            shaded = (
                max(0, min(255, int(base_color[0] * intensity))),
                max(0, min(255, int(base_color[1] * intensity))),
                max(0, min(255, int(base_color[2] * intensity)))
            )
            # get projected pts
            p0 = projected[i0]
            p1 = projected[i1]
            p2 = projected[i2]
            # cull triangles whose projected z are outside viewport (optional)
            # draw filled triangle with z test
            self.draw_triangle(p0, p1, p2, shaded)

    def main_loop(self):
        running = True
        angle = 0.0
        fov = math.radians(60)
        light_dir = normalize((0.5, 1.0, -0.8))

        # model scale and translation
        def model_transform(v):
            # scale
            s = 0.8
            x, y, z = v[0]*s, v[1]*s, v[2]*s
            # rotate
            r = rotate_y((x,y,z), angle)
            r = rotate_x(r, angle * 0.5)
            # translate forward so cube is in front of camera
            return vec_add(r, (0.0, 0.0, 4.0))

        prev_time = time()
        while running:
            now = time()
            dt = now - prev_time
            prev_time = now
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        break

            # update rotation
            angle += dt * 1.2  # radians/sec

            # clear buffers
            # clear buffers (buffer-sized)
            self.clear((20, 20, 40))
            # create PixelArray for fast writes
            try:
                self._pixelarray = pygame.PixelArray(self.buffer)
                self._map_rgb = self.buffer.map_rgb
            except Exception:
                self._pixelarray = None
                self._map_rgb = None

            # render model into smaller buffer
            self.render_model(CUBE_VERTS, CUBE_TRIS, model_transform, view_pos=(0.0,0.0,0.0), light_dir=light_dir, fov=fov)

            # free PixelArray (important to unlock surface)
            if self._pixelarray is not None:
                del self._pixelarray
                self._pixelarray = None

            # scale buffer to screen for display
            scaled = pygame.transform.scale(self.buffer, (self.width, self.height))
            self.screen.blit(scaled, (0,0))
            # HUD / simple info
            fps = int(self.clock.get_fps())
            font = pygame.font.SysFont('Consolas', 18)
            txt = font.render(f'FPS: {fps}', True, (255,255,255))
            self.screen.blit(txt, (10,10))

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

# ---------- Run demo ----------

if __name__ == '__main__':
    r = Rasterizer(640, 480)
    r.main_loop()
