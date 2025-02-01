import pygame
import math
import sys
import random

tenary = lambda a, b, c: b if a else c
cell_size = 20
half_size = cell_size / 2
damping = 0.9  # Reduces jitter post-collision
friction = 0.99  # General velocity damping

def generateMergerSponge(size):
    def nearest_power_of_3(n):
        power = 1
        while power < n:
            power *= 3
        return power

    size = nearest_power_of_3(size)
    
    if size == 1:
        return [[True]]
    
    smaller = generateMergerSponge(size // 3)
    smaller_size = len(smaller)
    
    result = []
    for i in range(3 * smaller_size):
        result.append([False] * (3 * smaller_size))
    
    for i in range(smaller_size):
        for j in range(smaller_size):
            if smaller[i][j]:
                result[i][j] = True
                result[i][j + smaller_size] = True
                result[i][j + 2 * smaller_size] = True
                result[i + smaller_size][j] = True
                result[i + 2 * smaller_size][j] = True
                result[i + 2 * smaller_size][j + smaller_size] = True
                result[i + 2 * smaller_size][j + 2 * smaller_size] = True
                result[i + smaller_size][j + 2 * smaller_size] = True

    return result

pygame.init()
clock = pygame.time.Clock()
geneColors = [(40, 40, 40), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Cell Simulation - Natch")

cellArrangement = generateMergerSponge(27)  # Smaller grid for better performance

def is_visible_on_screen(x, y, width, height, screen_width, screen_height):
    return not (x > screen_width or x + width < 0 or y > screen_height or y + height < 0)

class Cell:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 20
        self.membraneHealth = 50
        self.genes = ['0;0', '0;0', '0;0', '0;0', '0;0', '0;0', '0;0', '0;0']
        self._cache = {}  # Cache for polygon points
        self.doIn = True

    def _calculate_gene_points(self, pos_x, pos_y, gene_size, angle):
        cache_key = (pos_x, pos_y, gene_size, angle)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        half_size = gene_size / 4
        points = [
            (pos_x - half_size * math.cos(angle) + half_size * math.sin(angle),
             pos_y - half_size * math.sin(angle) - half_size * math.cos(angle)),
            (pos_x + half_size * math.cos(angle) + half_size * math.sin(angle),
             pos_y + half_size * math.sin(angle) - half_size * math.cos(angle)),
            (pos_x + half_size * math.cos(angle) - half_size * math.sin(angle),
             pos_y + half_size * math.sin(angle) + half_size * math.cos(angle)),
            (pos_x - half_size * math.cos(angle) - half_size * math.sin(angle),
             pos_y - half_size * math.sin(angle) + half_size * math.cos(angle))
        ]
        self._cache[cache_key] = points
        return points

    def draw(self, screen, offset_x, offset_y, zoom):
        scaled_x = round((self.x + offset_x) * zoom)
        scaled_y = round((self.y + offset_y) * zoom)
        scaled_size = round(self.size * zoom)

        if not is_visible_on_screen(scaled_x, scaled_y, scaled_size, scaled_size, screen.get_width(), screen.get_height()):
            return

        center_x = scaled_x + scaled_size // 2
        center_y = scaled_y + scaled_size // 2

        # Draw cell body
        pygame.draw.rect(screen, (210, 180, 140), (scaled_x-1, scaled_y-1, scaled_size+2, scaled_size+2))
        
        # Draw cell membrane
        membrane_width = round(self.membraneHealth / 25 * zoom)
        membrane_rect = pygame.Rect(scaled_x - 1, scaled_y - 1,
                                    scaled_size + 2, scaled_size + 2)
        pygame.draw.rect(screen, (245, 222, 179), membrane_rect, int(membrane_width))
        
        gene_radius = 6 * zoom
        gene_size = min(6 * zoom, 24 * zoom / len(self.genes))
        base_angle = math.pi / 2  # Start from top

        for i, gene in enumerate(self.genes):
            gene_x, gene_y = map(int, gene.split(';'))
            angle = base_angle + (2 * math.pi * i) / len(self.genes)

            pos_x = center_x + gene_radius * math.cos(angle)
            pos_y = center_y + gene_radius * math.sin(angle)

            # Primary gene
            points = self._calculate_gene_points(pos_x, pos_y, gene_size, angle)
            pygame.draw.polygon(screen, geneColors[gene_x], points)

            # Secondary gene
            offset_x = gene_size * math.cos(angle + math.pi) / 2
            offset_y = gene_size * math.sin(angle + math.pi) / 2
            points = self._calculate_gene_points(pos_x + offset_x, pos_y + offset_y, gene_size, angle)
            pygame.draw.polygon(screen, geneColors[gene_y], points)

class Wall:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 20
        self.membraneHealth = 0
    
    def draw(self, screen, offset_x, offset_y, zoom):
        scaled_x = round((self.x + offset_x) * zoom)
        scaled_y = round((self.y + offset_y) * zoom)
        scaled_size = round(self.size * zoom)
        
        if not is_visible_on_screen(scaled_x, scaled_y, scaled_size, scaled_size, screen.get_width(), screen.get_height()):
            return
        
        pygame.draw.rect(screen, (0, 0, 0), (scaled_x-1, scaled_y-1, scaled_size+2, scaled_size+2))

class Particle:
    def __init__(self, x, y, type, radius):
        self.x = x
        self.y = y
        self.type = type
        self.radius = radius
        self.speed = 2  # Reduced speed for more controlled movement
        self.velx = random.random() * 2 - 1
        self.vely = random.random() * 2 - 1
        
        # Normalize initial velocity
        magnitude = math.sqrt(self.velx**2 + self.vely**2)
        self.velx /= magnitude
        self.vely /= magnitude
    
    def draw(self, screen, offset_x, offset_y, zoom):
        scaled_x = (self.x + offset_x) * zoom
        scaled_y = (self.y + offset_y) * zoom
        scaled_radius = self.radius * zoom

        if not is_visible_on_screen(scaled_x - scaled_radius, scaled_y - scaled_radius, 
                                  scaled_radius * 2, scaled_radius * 2, 
                                  screen.get_width(), screen.get_height()):
            return

        color = (255,0,0) if self.type == "food" else (150,75,0)
        pygame.draw.circle(screen, color, (int(scaled_x), int(scaled_y)), int(scaled_radius))
    
    def check_wall_collision(self, walls):
        cell_size = 20  # Size of grid cells
        grid_x = int(self.x // cell_size)
        grid_y = int(self.y // cell_size)
        
        # Only check walls in neighboring grid cells
        for wall in walls:
            wall_grid_x = int(wall.x // cell_size)
            wall_grid_y = int(wall.y // cell_size)
            
            # Skip walls that are too far away
            if abs(grid_x - wall_grid_x) > 1 or abs(grid_y - wall_grid_y) > 1:
                continue
            
            # Calculate the closest point on the wall to the particle
            closest_x = max(wall.x, min(self.x, wall.x + wall.size))
            closest_y = max(wall.y, min(self.y, wall.y + wall.size))
            
            # Calculate distance between closest point and particle center
            distance_x = self.x - closest_x
            distance_y = self.y - closest_y
            distance = math.sqrt(distance_x**2 + distance_y**2)
            
            # If collision detected
            if distance < self.radius:
                # Calculate normal vector
                if distance > 0:
                    normal_x = distance_x / distance
                    normal_y = distance_y / distance
                else:
                    normal_x = 1
                    normal_y = 0
                
                # Calculate relative velocity
                dot_product = (self.velx * normal_x + self.vely * normal_y)
                
                # Apply impulse
                impulse = 2.0  # Bounce factor
                self.velx -= impulse * dot_product * normal_x
                self.vely -= impulse * dot_product * normal_y
                
                # Move particle out of wall
                penetration = self.radius - distance
                self.x += normal_x * penetration
                self.y += normal_y * penetration
                
                # Damage wall
                wall.membraneHealth -= 1

    def update(self, width, height):
        self.check_wall_collision(cells)
        
        # Apply friction
        self.velx *= friction
        self.vely *= friction

        # Calculate next position
        next_x = self.x + self.velx * self.speed
        next_y = self.y + self.vely * self.speed

        # Update position
        self.x = next_x
        self.y = next_y
        
        # Wrap around screen edges with smoother transition
        if self.x < -self.radius:
            self.x = width + self.radius
        elif self.x > width + self.radius:
            self.x = -self.radius
        if self.y < -self.radius:
            self.y = height + self.radius
        elif self.y > height + self.radius:
            self.y = -self.radius

        self.velx += random.uniform(-0.02, 0.02)
        self.vely += random.uniform(-0.02, 0.02)
        
        # Normalize velocity to maintain consistent speed
        magnitude = math.sqrt(self.velx**2 + self.vely**2)
        if magnitude > 0:
            self.velx /= magnitude
            self.vely /= magnitude
        
        # Apply subtle dampening
        self.velx *= 0.3
        self.vely *= 0.3

class Button:
    def __init__(self, x, y, width, height, color, text, action):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.text = text
        self.action = action
    
    def draw(self, screen):
        if not is_visible_on_screen(self.x, self.y, self.width, self.height, screen.get_width(), screen.get_height()):
            return
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        write_text(screen, self.text, self.x + self.width // 2, self.y + self.height // 2)
    
    def handleEvents(self):
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                print(f"Click detected at ({event.pos[0]}, {event.pos[1]})")
                if self.x <= event.pos[0] <= self.x + self.width and self.y <= event.pos[1] <= self.y + self.height:
                    print("Button clicked!")
                    self.action()

def write_text(screen, text, x, y, color=(0, 0, 0), font_size=20):
    if not is_visible_on_screen(x - 50, y - 10, 100, 20, screen.get_width(), screen.get_height()):
        return
    font = pygame.font.Font(None, font_size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    screen.blit(text_surface, text_rect)

cells = []
for y in range(len(cellArrangement)):
    for x in range(len(cellArrangement[y])):
        if not cellArrangement[y][x]:
            all_adjacent_true = True
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    nx, ny = x + dx, y + dy
                    if 0 <= ny < len(cellArrangement) and 0 <= nx < len(cellArrangement[0]):
                        if cellArrangement[ny][nx]:
                            all_adjacent_true = False
                            break
            
            if all_adjacent_true:
                cells.append(Wall(x * 20, y * 20))
            else:
                cells.append(Cell(x * 20, y * 20))

def FPSGraph():
    FPSs.append(clock.get_fps())
    if len(FPSs) > 100:
        FPSs.pop(0)
    pygame.draw.rect(screen, (200, 200, 200), (460, 5, 200, 15))
    
    # Draw FPS graph
    for i in range(len(FPSs) - 1):
        pygame.draw.line(screen, (0, 255, 0), 
            (460 + i*2, 20 - max(0, min(15, (FPSs[i] / 144) * 15))), 
            (460 + (i+1)*2, 20 - max(0, min(15, (FPSs[i+1] / 144) * 15)))
        )

clock = pygame.time.Clock()
running = True
offset_x = 0
offset_y = 0
pan_velocity_x = 0
pan_velocity_y = 0
zoom = 1.0
target_zoom = 1.0
dragging = False
last_mouse_pos = None
FPSs = []
particles = []
for _ in range(500):
    valid = False
    while not valid:
        x = random.randint(0, 550)
        y = random.randint(0, 550)
        particle = Particle(x, y, tenary(random.random() > 0.5, "food", "waste"), 2)
        
        # Check if particle is inside any cell
        in_cell = False
        for cell in cells:
            if x >= cell.x and x <= cell.x + 20 and y >= cell.y and y <= cell.y + 20:
                in_cell = True
                break
        
        if not in_cell:
            valid = True
            particles.append(particle)

animationTime = 8 # seconds
passed = 0

skipBtn = Button(350, 400, 100, 50, (0, 0, 0),"Skip", lambda: globals().update({'passed': 8}))

while passed < animationTime:
    dt = clock.tick(144) / 1000
    passed += dt
    skipBtn.handleEvents()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    
    screen.fill((0, 0, 0))
    
    if passed < 6:
        value = min(255,int(255 * (passed / 5)))
        fadeInColor = (value, value, value)
    else:
        value = min(255,int(255 * (1 - ((passed-6) / 2))))
        fadeInColor = (value, value, value)
    
    skipBtn.color = fadeInColor # type: ignore
    skipBtn.draw(screen)
    
    write_text(screen, "Developed by", 400, 250, fadeInColor, 120)
    write_text(screen, "Natch", 400, 350, fadeInColor, 120)
    
    pygame.draw.rect(screen, (180, 180, 180), (0, 0, (passed / animationTime) * 800, 4))
    
    pygame.display.flip()

while running:
    dt = clock.tick(144) / 1000.0
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                dragging = True
                last_mouse_pos = event.pos
                pan_velocity_x = 0
                pan_velocity_y = 0
            elif event.button == 4:  # Mouse wheel up
                target_zoom *= 1.1
            elif event.button == 5:  # Mouse wheel down
                target_zoom *= 0.9
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if dragging and last_mouse_pos:
                current_pos = event.pos
                dx = (current_pos[0] - last_mouse_pos[0]) / zoom
                dy = (current_pos[1] - last_mouse_pos[1]) / zoom
                offset_x += dx
                offset_y += dy
                pan_velocity_x = dx * 0.98
                pan_velocity_y = dy * 0.98
                last_mouse_pos = current_pos
    
    # Check if mouse has been stationary
    current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
    if 'last_mouse_move_time' not in locals():
        last_mouse_move_time = current_time
    
    mouse_pos = pygame.mouse.get_pos()
    if 'last_mouse_check_pos' not in locals():
        last_mouse_check_pos = mouse_pos
    
    if mouse_pos != last_mouse_check_pos: # type: ignore
        last_mouse_move_time = current_time
        last_mouse_check_pos = mouse_pos
    elif current_time - last_mouse_move_time > 0.75: # type: ignore
        pan_velocity_x = 0
        pan_velocity_y = 0

    # Smooth zoom interpolation
    # Get mouse position before zoom
    mouse_x, mouse_y = pygame.mouse.get_pos()
    world_x = (mouse_x - offset_x * zoom) / zoom
    world_y = (mouse_y - offset_y * zoom) / zoom
    
    # Apply zoom
    old_zoom = zoom
    zoom = zoom + (target_zoom - zoom) * 0.1
    target_zoom = min(64, max(0.1, target_zoom))
    
    # Adjust offset to keep mouse position fixed
    offset_x = -(world_x * zoom - mouse_x) / zoom
    offset_y = -(world_y * zoom - mouse_y) / zoom   
    
    if not dragging:
        offset_x += pan_velocity_x
        offset_y += pan_velocity_y
        pan_velocity_x *= 0.95
        pan_velocity_y *= 0.95
        
        if abs(pan_velocity_x) < 0.1: pan_velocity_x = 0
        if abs(pan_velocity_y) < 0.1: pan_velocity_y = 0

    # This is the entire draw loop.
    screen.fill((255, 255, 255))
    for cell in cells:
        cell.draw(screen, offset_x, offset_y, zoom)
    
    for particle in particles:
        particle.update(550, 550)
        particle.draw(screen, offset_x, offset_y, zoom)
    
    write_text(screen, f"FPS: {int(clock.get_fps())}", 400, 10)
    FPSGraph()
    
    pygame.display.flip()

pygame.quit()