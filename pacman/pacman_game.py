"""
pacman_game.py
Classic Pac-Man game implemented in Pygame.
Designed for both manual keyboard play (Arrow keys / WASD)
and local testing.
"""

import sys
import os
import math
import random
import pygame

# ─────────────────────────────────────────────────────────────
#  Game Configuration
# ─────────────────────────────────────────────────────────────
CELL_SIZE = 24
FPS = 60

# Colors (Classic arcade palette)
BLACK = (0, 0, 0)
NAVY_BLUE = (25, 25, 166)
WALL_BORDER = (33, 33, 222)
YELLOW = (255, 238, 0)
WHITE = (255, 255, 255)
PELLET_COLOR = (255, 183, 174)
POWER_PELLET_COLOR = (255, 183, 255)

RED = (255, 0, 0)        # Blinky
PINK = (255, 183, 255)   # Pinky
CYAN = (0, 255, 255)     # Inky
ORANGE = (255, 183, 81)  # Clyde
SCARED_BLUE = (33, 33, 255)
SCARED_WHITE = (240, 240, 255)

# Standard Pac-Man Maze (28 cols x 31 rows)
# W = Wall, . = Dot, o = Power Pellet, ' ' = Empty space, G = Ghost House, = = Door
MAZE_LAYOUT = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "W............WW............W",
    "W.WWWW.WWWWW.WW.WWWWW.WWWW.W",
    "WoWWWW.WWWWW.WW.WWWWW.WWWWoW",
    "W.WWWW.WWWWW.WW.WWWWW.WWWW.W",
    "W..........................W",
    "W.WWWW.WW.WWWWWWWW.WW.WWWW.W",
    "W.WWWW.WW.WWWWWWWW.WW.WWWW.W",
    "W......WW....WW....WW......W",
    "WWWWWW.WWWWW WW WWWWW.WWWWWW",
    "     W.WWWWW WW WWWWW.W     ",
    "     W.WW          WW.W     ",
    "     W.WW WWW==WWW WW.W     ",
    "WWWWWW.WW WGGGGGGW WW.WWWWWW",
    "      .   WGGGGGGW   .      ",
    "WWWWWW.WW WGGGGGGW WW.WWWWWW",
    "     W.WW WWWWWWWW WW.W     ",
    "     W.WW          WW.W     ",
    "     W.WW WWWWWWWW WW.W     ",
    "WWWWWW.WW WWWWWWWW WW.WWWWWW",
    "W............WW............W",
    "W.WWWW.WWWWW.WW.WWWWW.WWWW.W",
    "W.WWWW.WWWWW.WW.WWWWW.WWWW.W",
    "Wo..WW................WW..oW",
    "WWW.WW.WW.WWWWWWWW.WW.WW.WWW",
    "WWW.WW.WW.WWWWWWWW.WW.WW.WWW",
    "W......WW....WW....WW......W",
    "W.WWWWWWWWWW.WW.WWWWWWWWWW.W",
    "W.WWWWWWWWWW.WW.WWWWWWWWWW.W",
    "W..........................W",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

COLS = len(MAZE_LAYOUT[0])
ROWS = len(MAZE_LAYOUT)
SCREEN_WIDTH = COLS * CELL_SIZE
SCREEN_HEIGHT = ROWS * CELL_SIZE + 50  # 50px for HUD scoreboard

DIR_UP = (0, -1)
DIR_DOWN = (0, 1)
DIR_LEFT = (-1, 0)
DIR_RIGHT = (1, 0)
DIR_NONE = (0, 0)


# ─────────────────────────────────────────────────────────────
#  Game Entities
# ─────────────────────────────────────────────────────────────
class Pacman:
    def __init__(self, col, row):
        self.start_col = col
        self.start_row = row
        self.speed = 2.0
        self.radius = CELL_SIZE // 2 - 2
        self.mouth_angle = 45
        self.mouth_speed = 3
        self.mouth_opening = True
        self.reset()

    def reset(self):
        self.x = float(self.start_col * CELL_SIZE + CELL_SIZE // 2)
        self.y = float(self.start_row * CELL_SIZE + CELL_SIZE // 2)
        self.dir = DIR_NONE
        self.next_dir = DIR_NONE

    def set_direction(self, direction):
        self.next_dir = direction

    def update(self, maze):
        # Mouth chomp animation
        if self.dir != DIR_NONE:
            if self.mouth_opening:
                self.mouth_angle += self.mouth_speed
                if self.mouth_angle >= 45:
                    self.mouth_opening = False
            else:
                self.mouth_angle -= self.mouth_speed
                if self.mouth_angle <= 5:
                    self.mouth_opening = True

        cur_col = int(round((self.x - CELL_SIZE / 2.0) / CELL_SIZE))
        cur_row = int(round((self.y - CELL_SIZE / 2.0) / CELL_SIZE))
        center_x = cur_col * CELL_SIZE + CELL_SIZE / 2.0
        center_y = cur_row * CELL_SIZE + CELL_SIZE / 2.0

        # Try switching to next_dir
        if self.next_dir != DIR_NONE and self.next_dir != self.dir:
            # Immediate 180° reversal
            if (self.next_dir[0] == -self.dir[0] and self.next_dir[0] != 0) or \
               (self.next_dir[1] == -self.dir[1] and self.next_dir[1] != 0):
                self.dir = self.next_dir
            # Turning perpendicular at grid intersections
            elif abs(self.x - center_x) <= self.speed and abs(self.y - center_y) <= self.speed:
                target_col = cur_col + self.next_dir[0]
                target_row = cur_row + self.next_dir[1]
                if not maze.is_wall(target_col, target_row):
                    self.x = center_x
                    self.y = center_y
                    self.dir = self.next_dir

        # Move in current direction
        if self.dir != DIR_NONE:
            next_x = self.x + self.dir[0] * self.speed
            next_y = self.y + self.dir[1] * self.speed

            # Side tunnel wrapping
            if next_x < -CELL_SIZE // 2:
                next_x = SCREEN_WIDTH + CELL_SIZE // 2
            elif next_x > SCREEN_WIDTH + CELL_SIZE // 2:
                next_x = -CELL_SIZE // 2

            check_col = cur_col + self.dir[0]
            check_row = cur_row + self.dir[1]

            if maze.is_wall(check_col, check_row):
                # Clamp at tile center
                if (self.dir == DIR_RIGHT and next_x >= center_x) or \
                   (self.dir == DIR_LEFT and next_x <= center_x) or \
                   (self.dir == DIR_DOWN and next_y >= center_y) or \
                   (self.dir == DIR_UP and next_y <= center_y):
                    self.x = center_x
                    self.y = center_y
                    self.dir = DIR_NONE
                else:
                    self.x = next_x
                    self.y = next_y
            else:
                self.x = next_x
                self.y = next_y

    def draw(self, screen):
        cx = int(self.x)
        cy = int(self.y)

        if self.dir == DIR_RIGHT or self.dir == DIR_NONE:
            start_angle = self.mouth_angle
        elif self.dir == DIR_UP:
            start_angle = 90 + self.mouth_angle
        elif self.dir == DIR_LEFT:
            start_angle = 180 + self.mouth_angle
        elif self.dir == DIR_DOWN:
            start_angle = 270 + self.mouth_angle

        end_angle = start_angle + (360 - 2 * self.mouth_angle)

        points = [(cx, cy)]
        steps = 24
        for i in range(steps + 1):
            rad = math.radians(start_angle + (end_angle - start_angle) * i / steps)
            px = cx + self.radius * math.cos(rad)
            py = cy - self.radius * math.sin(rad)
            points.append((px, py))

        pygame.draw.polygon(screen, YELLOW, points)


class Ghost:
    def __init__(self, col, row, color, name="Ghost", initial_dir=DIR_LEFT):
        self.start_col = col
        self.start_row = row
        self.color = color
        self.name = name
        self.initial_dir = initial_dir
        self.speed = 2.0
        self.radius = CELL_SIZE // 2 - 2
        self.reset()

    def reset(self):
        self.x = float(self.start_col * CELL_SIZE + CELL_SIZE // 2)
        self.y = float(self.start_row * CELL_SIZE + CELL_SIZE // 2)
        self.dir = self.initial_dir
        self.scared = False
        self.scared_timer = 0
        self._last_tile = None

        # Inside pen (rows 12-15, cols 11-16) triggers active exit sequence
        if 11 <= self.start_col <= 16 and 12 <= self.start_row <= 15:
            self.state = "EXITING"
        else:
            self.state = "CHASE"

    def update(self, maze, pacman_pos):
        if self.scared:
            self.scared_timer -= 1
            if self.scared_timer <= 0:
                self.scared = False

        cur_col = int(round((self.x - CELL_SIZE / 2.0) / CELL_SIZE))
        cur_row = int(round((self.y - CELL_SIZE / 2.0) / CELL_SIZE))
        center_x = cur_col * CELL_SIZE + CELL_SIZE / 2.0
        center_y = cur_row * CELL_SIZE + CELL_SIZE / 2.0

        # State 1: Active Pen Exit Sequence
        if self.state == "EXITING":
            target_col = 13 if cur_col <= 13 else 14
            target_door_x = target_col * CELL_SIZE + CELL_SIZE / 2.0

            # 1. Align horizontally to door column
            if abs(self.x - target_door_x) > self.speed:
                self.dir = DIR_LEFT if self.x > target_door_x else DIR_RIGHT
            else:
                self.x = target_door_x
                # 2. Ascend vertically through the door
                if cur_row > 11:
                    self.dir = DIR_UP
                else:
                    # 3. Reached row 11 corridor outside the pen
                    self.y = 11 * CELL_SIZE + CELL_SIZE / 2.0
                    self.dir = DIR_LEFT if target_col == 13 else DIR_RIGHT
                    self.state = "CHASE"
                    self._last_tile = (cur_col, 11)

            self.x += self.dir[0] * self.speed
            self.y += self.dir[1] * self.speed
            return

        # State 2: Active Maze Pursuit
        current_tile = (cur_col, cur_row)

        # Re-evaluate direction when passing through a new tile center
        if current_tile != self._last_tile and abs(self.x - center_x) <= self.speed and abs(self.y - center_y) <= self.speed:
            self.x = center_x
            self.y = center_y
            self._last_tile = current_tile

            possible_dirs = []
            for d in [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]:
                # Don't directly reverse unless dead-end
                if (d[0] == -self.dir[0] and d[0] != 0) or (d[1] == -self.dir[1] and d[1] != 0):
                    continue
                next_c = cur_col + d[0]
                next_r = cur_row + d[1]
                if not maze.is_wall(next_c, next_r, allow_door=False):
                    possible_dirs.append(d)

            if not possible_dirs:
                # Turn around
                possible_dirs.append((-self.dir[0], -self.dir[1]))

            if possible_dirs:
                if self.scared:
                    self.dir = random.choice(possible_dirs)
                else:
                    best_dir = possible_dirs[0]
                    best_dist = float('inf')
                    for d in possible_dirs:
                        target_x = (cur_col + d[0]) * CELL_SIZE + CELL_SIZE / 2.0
                        target_y = (cur_row + d[1]) * CELL_SIZE + CELL_SIZE / 2.0
                        dist = (target_x - pacman_pos[0])**2 + (target_y - pacman_pos[1])**2
                        if dist < best_dist:
                            best_dist = dist
                            best_dir = d
                    if random.random() < 0.80:
                        self.dir = best_dir
                    else:
                        self.dir = random.choice(possible_dirs)

        self.x += self.dir[0] * self.speed
        self.y += self.dir[1] * self.speed

        # Tunnel wrap
        if self.x < -CELL_SIZE // 2:
            self.x = SCREEN_WIDTH + CELL_SIZE // 2
        elif self.x > SCREEN_WIDTH + CELL_SIZE // 2:
            self.x = -CELL_SIZE // 2

    def draw(self, screen):
        cx = int(self.x)
        cy = int(self.y)

        c = SCARED_BLUE if self.scared and (self.scared_timer > 90 or self.scared_timer % 15 < 8) else self.color
        
        # Ghost body
        pygame.draw.circle(screen, c, (cx, cy), self.radius)
        pygame.draw.rect(screen, c, (cx - self.radius, cy, self.radius * 2, self.radius))

        # Bottom skirt
        wave_width = (self.radius * 2) // 3
        for i in range(3):
            wx = cx - self.radius + i * wave_width + wave_width // 2
            wy = cy + self.radius
            pygame.draw.circle(screen, c, (wx, wy), wave_width // 2)

        # Eyes
        if not self.scared:
            eye_off_x = self.dir[0] * 3
            eye_off_y = self.dir[1] * 3
            pygame.draw.circle(screen, WHITE, (cx - 5, cy - 3), 4)
            pygame.draw.circle(screen, WHITE, (cx + 5, cy - 3), 4)
            pygame.draw.circle(screen, NAVY_BLUE, (cx - 5 + eye_off_x, cy - 3 + eye_off_y), 2)
            pygame.draw.circle(screen, NAVY_BLUE, (cx + 5 + eye_off_x, cy - 3 + eye_off_y), 2)
        else:
            pygame.draw.circle(screen, WHITE, (cx - 4, cy - 2), 2)
            pygame.draw.circle(screen, WHITE, (cx + 4, cy - 2), 2)


# ─────────────────────────────────────────────────────────────
#  Maze Board
# ─────────────────────────────────────────────────────────────
class Maze:
    def __init__(self):
        self.walls = set()
        self.doors = set()
        self.pellets = set()
        self.power_pellets = set()

        for r, row in enumerate(MAZE_LAYOUT):
            for c, val in enumerate(row):
                if val == 'W':
                    self.walls.add((c, r))
                elif val == '=':
                    self.doors.add((c, r))
                elif val == '.':
                    self.pellets.add((c, r))
                elif val == 'o':
                    self.power_pellets.add((c, r))

    def is_wall(self, c, r, allow_door=False):
        if r < 0 or r >= ROWS or c < 0 or c >= COLS:
            # Tunnels on rows 14 & 15 are walkable outside boundaries
            if (r == 14 or r == 15) and (c < 0 or c >= COLS):
                return False
            return True
        if (c, r) in self.walls:
            return True
        if (c, r) in self.doors and not allow_door:
            return True
        return False

    def draw(self, screen):
        for (c, r) in self.walls:
            x = c * CELL_SIZE
            y = r * CELL_SIZE
            pygame.draw.rect(screen, NAVY_BLUE, (x, y, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(screen, WALL_BORDER, (x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4), 1)

        for (c, r) in self.doors:
            x = c * CELL_SIZE
            y = r * CELL_SIZE + CELL_SIZE // 2 - 2
            pygame.draw.rect(screen, PINK, (x, y, CELL_SIZE, 4))

        for (c, r) in self.pellets:
            px = c * CELL_SIZE + CELL_SIZE // 2
            py = r * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(screen, PELLET_COLOR, (px, py), 3)

        for (c, r) in self.power_pellets:
            px = c * CELL_SIZE + CELL_SIZE // 2
            py = r * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(screen, POWER_PELLET_COLOR, (px, py), 7)


# ─────────────────────────────────────────────────────────────
#  Main Game Loop
# ─────────────────────────────────────────────────────────────
def run_pacman(manual_mode=True):
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    title = "Pac-Man [MANUAL MODE]" if manual_mode else "Pac-Man [AUTONOMOUS READY]"
    pygame.display.set_caption(title)
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Arial", 18, bold=True)
    big_font = pygame.font.SysFont("Arial", 32, bold=True)

    maze = Maze()
    pacman = Pacman(col=14, row=23)

    ghosts = [
        Ghost(col=13, row=11, color=RED, name="Blinky", initial_dir=DIR_LEFT),
        Ghost(col=14, row=11, color=PINK, name="Pinky", initial_dir=DIR_RIGHT),
        Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT),
        Ghost(col=15, row=14, color=ORANGE, name="Clyde", initial_dir=DIR_RIGHT),
    ]

    score = 0
    lives = 3
    game_over = False
    game_won = False

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif game_over or game_won:
                    if event.key == pygame.K_r:
                        maze = Maze()
                        pacman.reset()
                        for g in ghosts:
                            g.reset()
                        score = 0
                        lives = 3
                        game_over = False
                        game_won = False
                elif manual_mode:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        pacman.set_direction(DIR_UP)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        pacman.set_direction(DIR_DOWN)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        pacman.set_direction(DIR_LEFT)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        pacman.set_direction(DIR_RIGHT)

        if not game_over and not game_won:
            pacman.update(maze)
            pac_grid = (int(round((pacman.x - CELL_SIZE/2.0) / CELL_SIZE)),
                        int(round((pacman.y - CELL_SIZE/2.0) / CELL_SIZE)))

            # Eat dots
            if pac_grid in maze.pellets:
                maze.pellets.remove(pac_grid)
                score += 10
            elif pac_grid in maze.power_pellets:
                maze.power_pellets.remove(pac_grid)
                score += 50
                for g in ghosts:
                    g.scared = True
                    g.scared_timer = 360  # 6 seconds

            if len(maze.pellets) == 0 and len(maze.power_pellets) == 0:
                game_won = True

            for g in ghosts:
                g.update(maze, (pacman.x, pacman.y))
                dist = math.hypot(pacman.x - g.x, pacman.y - g.y)
                if dist < (pacman.radius + g.radius):
                    if g.scared:
                        score += 200
                        g.reset()
                    else:
                        lives -= 1
                        if lives <= 0:
                            game_over = True
                        else:
                            pacman.reset()
                            for gh in ghosts:
                                gh.reset()
                        break

        # Render
        screen.fill(BLACK)
        maze.draw(screen)
        pacman.draw(screen)
        for g in ghosts:
            g.draw(screen)

        # HUD
        hud_y = ROWS * CELL_SIZE
        pygame.draw.line(screen, WHITE, (0, hud_y), (SCREEN_WIDTH, hud_y), 2)
        score_surface = font.render(f"SCORE: {score}", True, WHITE)
        lives_surface = font.render(f"LIVES: {lives}", True, YELLOW)
        mode_surface = font.render("MANUAL [WASD / ARROWS]" if manual_mode else "AUTONOMOUS MODE", True, CYAN)

        screen.blit(score_surface, (20, hud_y + 15))
        screen.blit(lives_surface, (220, hud_y + 15))
        screen.blit(mode_surface, (380, hud_y + 15))

        if game_over:
            msg = big_font.render("GAME OVER - PRESS 'R' TO RESTART", True, RED)
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
        elif game_won:
            msg = big_font.render("YOU WIN! - PRESS 'R' TO PLAY AGAIN", True, YELLOW)
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT // 2 - 20))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    is_manual = True
    if len(sys.argv) > 1 and sys.argv[1].lower() == "--auto":
        is_manual = False
    run_pacman(manual_mode=is_manual)
