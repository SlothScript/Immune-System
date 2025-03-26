import pygame
import math
import sys
import random

ternary = lambda a, b, c: b if a else c
tick = 0
cell_size = 20
half_size = cell_size / 2
damping = 0.9  # Reduces jitter post-collision
friction = 0.99  # General velocity damping
cellEditMode = False

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
geneColors = [(40, 40, 40), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (180, 100, 220), (83, 195, 182)]
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Cell Simulation - Natch")

def is_visible_on_screen(x, y, width, height, screen_width, screen_height):
    return not (x > screen_width or x + width < 0 or y > screen_height or y + height < 0)

class Laser:
    def __init__(self, x, y, targetX, targetY, thickess, amplitude):
        self.x = x
        self.y = y
        self.tx = targetX
        self.ty = targetY
        self.thickness = thickess
        self.amplitude = amplitude
        self.ot = self.thickness
    
    def draw(self, screen, offset_x, offset_y, zoom):
            self.thickness = max(0.1, self.thickness - 0.2)
            if self.thickness == 0.1:
                return
            
            dx = self.tx - self.x
            dy = self.ty - self.y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance == 0:
                lasers.remove(self)
            
            num_points = 50
            points = []
            
            for i in range(num_points):
                progress = i / (num_points - 1)
                x = self.x + dx * progress
                y = self.y + dy * progress
                edge_damping = math.sin(progress * math.pi)  # Creates a smooth curve that peaks in middle
                wave_offset = math.sin(progress * 6 * math.pi + (self.thickness * 2)) * self.amplitude * edge_damping
                perpendicular_x = -dy / distance
                perpendicular_y = dx / distance
                x += perpendicular_x * wave_offset
                y += perpendicular_y * wave_offset
                
                screen_x = (x + offset_x) * zoom
                screen_y = (y + offset_y) * zoom
                points.append((screen_x, screen_y))
                
            if len(points) >= 2:
                pygame.draw.lines(screen, (255, 0, 0), False, points, max(1, int(self.thickness * zoom)))

class Cell:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 20
        self.membraneHealth = 120
        self.genes = ['6;8', '3;3', '3;3', '1;1', '6;7', '2;2', '4;6a', '5;6a']
        self.geneHealth = [100, 100, 100, 100, 100, 100, 100, 100]
        self._cache = {}  # Cache for polygon points
        self.memory = ""
        self.doIn = True
        self.onGeneNumber = 0
        self.geneBrightness = 0
        self.energy = 100
        self.myTick = 0

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
        membrane_width = round(self.membraneHealth / 60 * zoom)
        membrane_rect = pygame.Rect(scaled_x - 1, scaled_y - 1,
                                    scaled_size + 2, scaled_size + 2)
        pygame.draw.rect(screen, (245, 222, 179), membrane_rect, int(membrane_width))
        
        # Draw inside/outside indicator (doIn)
        if self.doIn:
            pygame.draw.polygon(screen, (127,127,127), ((center_x - scaled_size*0.2 + scaled_size//1.7, center_y - scaled_size*0.2 + scaled_size//1.7), (center_x - scaled_size*0.45 + scaled_size//1.7, center_y - scaled_size*0.2 + scaled_size//1.7), (center_x - scaled_size*0.2 + scaled_size//1.7, center_y - scaled_size*0.45 + scaled_size//1.7)))
        else:
            pygame.draw.polygon(screen, (220,220,220), ((center_x - scaled_size*0.2 + scaled_size//1.7, center_y - scaled_size*0.2 + scaled_size//1.7), (center_x - scaled_size*0.45 + scaled_size//1.7, center_y - scaled_size*0.2 + scaled_size//1.7), (center_x - scaled_size*0.2 + scaled_size//1.7, center_y - scaled_size*0.45 + scaled_size//1.7)))
        
        pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), scaled_size // 6, math.floor(scaled_size // 30))
        
        # Draw selector
        if len(self.genes) > 0:
            gene_radius = 6 * zoom
            gene_size = min(6 * zoom, 24 * zoom / len(self.genes))
            angle = math.pi / 2 + (2 * math.pi * tick) / len(self.genes)

            # Calculate start point (from circle)
            start_x = center_x + (scaled_size // 6) * math.cos(angle)
            start_y = center_y + (scaled_size // 6) * math.sin(angle)

            # Calculate end point (just past the gene)
            end_x = center_x + (gene_radius + gene_size/2) * math.cos(angle)
            end_y = center_y + (gene_radius + gene_size/2) * math.sin(angle)

            # Calculate trapezoid points with consistent width
            width = gene_size * 0.3
            perp_x = math.cos(angle + math.pi/2)
            perp_y = math.sin(angle + math.pi/2)
            
            points = [
                (start_x - width * perp_x, start_y - width * perp_y),
                (start_x + width * perp_x, start_y + width * perp_y),
                (end_x + width * 1.5 * perp_x, end_y + width * 1.5 * perp_y),
                (end_x - width * 1.5 * perp_x, end_y - width * 1.5 * perp_y)
            ]
            
            pygame.draw.polygon(screen, (255, 255, 255), points)

        gene_radius = 6 * zoom
        gene_size = min(6 * zoom, 24 * zoom / len(self.genes))
        base_angle = math.pi / 2  # Start from top

        for i, gene in enumerate(self.genes):
            try:
                gene_x, gene_y = map(int, gene.split(';'))
            except:
                gene_x = int(gene.split(';')[0])
                gene_y = int(''.join(filter(str.isdigit, gene.split(';')[1])))
            angle = base_angle + (2 * math.pi * i) / len(self.genes)

            pos_x = center_x + gene_radius * math.cos(angle)
            pos_y = center_y + gene_radius * math.sin(angle)
            
            if tick - math.floor(tick) <= 0.1:
                self.geneBrightness = 128
            else:
                self.geneBrightness -= 1
                if self.geneBrightness < 0:
                    self.geneBrightness = 0

            # Primary gene
            points = self._calculate_gene_points(pos_x, pos_y, gene_size, angle)
            color = geneColors[gene_x]
            if math.floor(tick) % len(self.genes) == i:
                color = tuple(max(0, min(255, int(c + self.geneBrightness))) for c in color)
            color = tuple(max(0, min(255, c - int(255 - self.geneHealth[self.genes.index(gene)]*2.55))) for c in color)
            pygame.draw.polygon(screen, color, points)

            # Secondary gene
            offset_x = gene_size * math.cos(angle + math.pi) / 2
            offset_y = gene_size * math.sin(angle + math.pi) / 2
            points = self._calculate_gene_points(pos_x + offset_x, pos_y + offset_y, gene_size, angle)
            color = geneColors[gene_y]
            if math.floor(tick) % len(self.genes) == i:
                color = tuple(min(255, c + self.geneBrightness) for c in color)
            pygame.draw.polygon(screen, color, points)

    def update(self):
        if self.membraneHealth < 1:
            newParticles = [Particle(self.x, self.y, 'waste', 2) for _ in range(10)]
            particles.extend(newParticles)
            for i, cell in enumerate(cells):
                if cell == self:
                    cells.pop(i)
                    break
        
        if self.myTick != math.floor(tick):
            self.myTick = math.floor(tick)
            self.executeGene(math.floor(tick) % len(self.genes))
    
    def executeGene(self, index):
        try:
            gene = self.genes[index]
        except:
            return
        
        self.energy -= 3
        self.geneHealth[index] -= random.randint(1, 4)
        
        geneA, geneB = gene.split(';')
        geneA = int(geneA)
        try:
            geneB = int(geneB)
        except:
            pass
        
        if geneA == 1:
            if geneB == 1 and not self.doIn:
                foodParts = self.getInternalParticles('food')
                if foodParts:
                    for food in foodParts:
                        self.drawLaser(food.x, food.y)
                        particles.remove(food)
                        self.energy += 10
                        particles.append(Particle(self.x, self.y, 'waste', 2))
            elif geneB == 3 and not self.doIn:
                self.membraneHealth = 0
                self.drawLaser(self.x - 20, self.y - 20)
                self.drawLaser(self.x + 20, self.y - 20)
                self.drawLaser(self.x - 20, self.y + 20)
                self.drawLaser(self.x + 20, self.y + 20)
        elif geneA == 2:
            if geneB == 3 and not self.doIn:
                self.membraneHealth = 0
                self.drawLaser(self.x - 20, self.y - 20)
                self.drawLaser(self.x + 20, self.y - 20)
                self.drawLaser(self.x - 20, self.y + 20)
                self.drawLaser(self.x + 20, self.y + 20)
            elif geneB == 2 and self.doIn:
                wasteParts = self.getInternalParticles('waste')
                if wasteParts:
                    # Weight particles by inverse distance - closer particles more likely
                    weights = []
                    for waste in wasteParts:
                        distance = math.sqrt((waste.x - self.x)**2 + (waste.y - self.y)**2)
                        weights.append(1.0 / (distance + 1))  # Add 1 to avoid division by zero
                    waste = random.choices(wasteParts, weights=weights, k=1)[0]
                    self.drawLaser(waste.x, waste.y)
                    particles.remove(waste)
            elif geneB == 1 and self.doIn:
                foodParts = self.getInternalParticles('food')
                if foodParts:
                    food = random.choice(foodParts)
                    self.drawLaser(food.x, food.y)
                    particles.remove(food)
                    particles.append(Particle(self.x, self.y, 'waste', 2))
        elif geneA == 3:
            if geneB == 3 and not self.doIn:
                self.membraneHealth += 25
                if self.membraneHealth > 120:
                    self.membraneHealth = 120
        elif geneA in [4, 5, 7]:
            self.processADNA(geneA, geneB)
            pass
        elif geneA == 6:
            if geneB == 7:
                self.doIn = True
            elif geneB == 8:
                self.doIn = False
    
    def processADNA(self, geneA, geneB):
        # format:
        # 4/5(firstGene.lastGenne)
        # 6a/b
        
        target_genes = []
        
        # ADNA nono's:
        if geneA in [3,6]:
            print("Invalid geneA:", geneA)
            return
        
        # Select target genes
        if geneB[0] in ['4', '5']:
            startGene = geneB.split(".")[0][2:]
            endGene = geneB.split(".")[1][:-1]
            
            if startGene in self.genes and endGene in self.genes:
                target_genes = self.genes[self.genes.index(startGene):self.genes.index(endGene)]
        
        elif geneB[0] == '6':
            if geneB[1] == 'a':
                target_genes = [min(self.genes, key=lambda gene: self.geneHealth[self.genes.index(gene)])]
            elif geneB[1] == 'b':
                target_genes = [max(self.genes, key=lambda gene: self.geneHealth[self.genes.index(gene)])]
        
        # Apply effects to target genes
        for gene in target_genes:
            if geneA in [1, 2]:
                if geneA == 1:
                    self.energy += 3
                self.genes.remove(gene)
                particles.append(Particle(self.x, self.y, 'waste', 2))
            elif geneA == 4:
                self.memory = gene
            elif geneA == 5:
                self.genes[self.genes.index(gene)] = self.memory
        
    def drawLaser(self, x, y):
        lasers.append(Laser(self.x, self.y, x, y, 5, 2))

    def getInternalParticles(self, typeFilter=None):
        # Check particles in a 20 radius area around the cell center
        nearby_particles = []
        for particle in particles:
            distance = math.sqrt((particle.x - (self.x + self.size/2))**2 + (particle.y - (self.y + self.size/2))**2)
            if distance <= 10:
                if typeFilter is None or particle.type == typeFilter:
                    nearby_particles.append(particle)
        
        # Draw detection range circle
        pygame.draw.circle(screen, (100,100,100), (int((self.x + self.size/2 + offset_x) * zoom), int((self.y + self.size/2 + offset_y) * zoom)), int(10 * zoom), 1)
        
        if not typeFilter:
            return nearby_particles
        
        return [particle for particle in nearby_particles if particle.type == typeFilter]

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
    
    def update(self):
        pass

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
            if type(wall) == Cell and self.type == "food":
                # Calculate if particle is inside the cell
                is_inside = (self.x > wall.x and self.x < wall.x + wall.size and 
                             self.y > wall.y and self.y < wall.y + wall.size)
                
                # Only damage cell if particle is actually touching the membrane
                if is_inside:
                    if not hasattr(self, 'last_damaged_cell') or self.last_damaged_cell != wall:
                        wall.membraneHealth -= 1
                        self.last_damaged_cell = wall
                else:
                    continue
            
            wall_grid_x = int(wall.x // cell_size)
            wall_grid_y = int(wall.y // cell_size)
            
            # Skip walls that are too far away
            if abs(grid_x - wall_grid_x) > 1 or abs(grid_y - wall_grid_y) > 1:
                continue
            
            # Calculate points for the wall's membrane (1 pixel thick border)
            membrane_points = [
                (wall.x, wall.y),                          # Top left
                (wall.x + wall.size, wall.y),             # Top right
                (wall.x + wall.size, wall.y + wall.size), # Bottom right
                (wall.x, wall.y + wall.size)              # Bottom left
            ]
            
            # Check collision with each membrane edge
            for i in range(len(membrane_points)):
                p1 = membrane_points[i]
                p2 = membrane_points[(i + 1) % len(membrane_points)]
                
                # Calculate closest point on the line segment (membrane edge)
                edge_length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                if edge_length == 0:
                    continue
                
                # Vector from p1 to particle
                v1_x = self.x - p1[0]
                v1_y = self.y - p1[1]
                
                # Vector from p1 to p2
                v2_x = p2[0] - p1[0]
                v2_y = p2[1] - p1[1]
                
                # Calculate projection
                t = max(0, min(1, (v1_x * v2_x + v1_y * v2_y) / edge_length**2))
                
                # Find closest point on line segment
                closest_x = p1[0] + t * v2_x
                closest_y = p1[1] + t * v2_y
                
                # Calculate distance between closest point and particle center
                distance_x = self.x - closest_x
                distance_y = self.y - closest_y
                distance = math.sqrt(distance_x**2 + distance_y**2)
                
                # If collision detected with membrane
                if distance < self.radius + 1:  # 1 pixel for membrane thickness
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
                    
                    # Move particle out of membrane
                    penetration = (self.radius + 1) - distance
                    self.x += normal_x * penetration
                    self.y += normal_y * penetration
                    
                    # Damage wall
                    wall.membraneHealth -= 1
                    break

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
                if self.x <= event.pos[0] <= self.x + self.width and self.y <= event.pos[1] <= self.y + self.height:
                    self.action()

def write_text(screen, text, x, y, color=(0, 0, 0), font_size=20, left=False):
    if not is_visible_on_screen(x - 50, y - 10, 100, 20, screen.get_width(), screen.get_height()):
        return
    font = pygame.font.Font(None, font_size)
    text_surface = font.render(text, True, color)
    if left:
        text_rect = text_surface.get_rect(topleft=(x, y))
    else:
        text_rect = text_surface.get_rect(center=(x, y))
    screen.blit(text_surface, text_rect)

cellArrangement = generateMergerSponge(3**3)

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

class cellEditUI:
    def __init__(self):
        self.x = -170
        self.t = 0
        self.selected_cell = None
        self.active_block = None
        self.block_value = ""
        self.font = pygame.font.Font(None, 24)
        self.scroll_y = 0
        self.max_scroll = 0

    def draw(self, screen):
        if cellEditMode:
            if self.x == -170:
                self.t = 0
            self.t += 0.3
            self.x = 170 * (1 / (1 + math.exp(-self.t + 5))) - 170
            if self.x >= -0.01:
                self.x = 0
        else:
            if self.x == 0:
                self.t = 10
            self.t -= 0.3
            self.x = 170 * (1 / (1 + math.exp(-self.t + 5))) - 171
            if self.x <= -170:
                self.x = -170
        
        pygame.draw.rect(screen, (40, 40, 40), (self.x, 0, 170, 600))
        pygame.draw.rect(screen, (10, 10, 10), (self.x, 0, 170, 600), 3)

        if cellEditMode or self.x <= -160:
            write_text(screen, "Cell Editor", self.x + 85, 30, color=(200, 200, 200))

            if self.selected_cell:
                write_text(screen, "Selected Cell:", self.x + 85, 70, color=(200, 200, 200))
                write_text(screen, f"Pos: ({self.selected_cell.x}, {self.selected_cell.y})", self.x + 85, 100, color=(180, 180, 180))
                write_text(screen, "DNA Blocks:", self.x + 85, 140, color=(200, 200, 200))

                # Draw DNA blocks
                block_height = 40
                block_width = 65
                blocks_per_row = 1
                genes = ";".join(self.selected_cell.genes).split(";")
                
                # Calculate max scroll
                total_rows = math.ceil(len(genes) / 2)
                content_height = total_rows * (block_height + 10) + 170
                self.max_scroll = max(0, content_height - 580)  # 580 is visible area height
                
                # Apply scroll clipping
                pygame.draw.rect(screen, (40, 40, 40), (self.x, 160, 170, 440))
                
                for i in range(0, len(genes), 2):
                    row = (i//2) // blocks_per_row
                    col = (i//2) % blocks_per_row
                    x = self.x + 20 + col * (block_width * 2 + 15)
                    y = 170 + row * (block_height + 10) - self.scroll_y
                    
                    # Only draw if in visible area
                    if 160 <= y <= 580:
                        for j in range(2):
                            if i + j >= len(genes):
                                break
                                
                            color = geneColors[int(str(genes[i + j])[0])]
                            
                            block_x = x + (j * (block_width + 5))
                            pygame.draw.rect(screen, color, (block_x, y, block_width, block_height))
                            pygame.draw.rect(screen, (100, 100, 100), (block_x, y, block_width, block_height), 2)
                            
                            if i + j == self.active_block and self.block_value:
                                display_text = self.block_value
                            else:
                                display_text = genes[i + j]
                            write_text(screen, display_text, block_x + block_width//2, y + block_height//2, color=(255-color[0], 255-color[1], 255-color[2]))

    def handleEvents(self, event):
        if not cellEditMode:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            
            if event.button == 4 and self.isMouseOver():  # Mouse wheel up
                self.scroll_y = max(0, self.scroll_y - 20)
            elif event.button == 5 and self.isMouseOver():  # Mouse wheel down
                self.scroll_y = min(self.max_scroll, self.scroll_y + 20)
            elif event.button == 1:  # Left click
                # Adjust mouse position for offset and zoom
                adjusted_mouse_x = (mouse_x / zoom) - offset_x
                adjusted_mouse_y = (mouse_y / zoom) - offset_y

                # Check if clicking a cell
                for cell in cells:
                    if isinstance(cell, Cell):
                        cell_rect = pygame.Rect(cell.x, cell.y, 20, 20)
                        if cell_rect.collidepoint(adjusted_mouse_x, adjusted_mouse_y):
                            self.selected_cell = cell
                            self.active_block = None
                            self.block_value = ""
                            self.scroll_y = 0  # Reset scroll when selecting new cell
                            return

                # Check if clicking DNA blocks
                if self.selected_cell:
                    block_size = 40
                    blocks_per_row = 2
                    genes = ";".join(self.selected_cell.genes).split(";")
                    for i in range(0, len(genes), 2):
                        row = (i//2) // blocks_per_row
                        col = (i//2) % blocks_per_row
                        x = self.x + 20 + col * (block_size * 2 + 15)
                        y = 170 + row * (block_size + 10) - self.scroll_y
                        
                        for j in range(2):
                            if i + j >= len(genes):
                                break
                            block_x = x + (j * (block_size + 5))
                            block_rect = pygame.Rect(block_x, y, block_size, block_size)
                            
                            if block_rect.collidepoint(mouse_x, mouse_y):
                                self.active_block = i + j
                                genes = ";".join(self.selected_cell.genes).split(";")
                                self.block_value = genes[i + j]
                                return

        elif event.type == pygame.KEYDOWN and self.active_block is not None:
            if event.key == pygame.K_RETURN:
                if self.block_value:
                    genes = ";".join(self.selected_cell.genes).split(";") # type: ignore
                    separator = ">" if random.random() > 0.5 else ")"
                    genes[self.active_block] = self.block_value
                    self.selected_cell.genes = separator.join(genes) # type: ignore
                self.active_block = None
                self.block_value = ""
            elif event.key == pygame.K_UP:
                current_value = int(self.block_value)
                self.block_value = str(min(9, current_value + 1))
            elif event.key == pygame.K_DOWN:
                current_value = int(self.block_value)
                self.block_value = str(max(0, current_value - 1))
    
    def isMouseOver(self):
        mouse_x, _ = pygame.mouse.get_pos()
        return self.x <= mouse_x <= self.x + 170

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
lasers = []
editUI = cellEditUI()

for _ in range(500):
    valid = False
    while not valid:
        x = random.randint(0, 550)
        y = random.randint(0, 550)
        particle = Particle(x, y, ternary(random.random() > 0.5, "food", "waste"), 2)
        
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
    write_text(screen, "Immune System Simulator © 2025 by Nathaniel Cole is licensed under CC BY-NC-SA 4.0.\n To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/. View more in the LICENSE file.", 400, 580, fadeInColor, 12)
    
    pygame.draw.rect(screen, (180, 180, 180), (0, 0, (passed / animationTime) * 800, 4))
    
    pygame.display.flip()

while running:
    dt = clock.tick(1000) / 1000.0
    passed += dt
    
    for event in pygame.event.get():
        editUI.handleEvents(event)
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
                if not (cellEditMode and editUI.isMouseOver()):
                    target_zoom *= 1.1
            elif event.button == 5:  # Mouse wheel down
                if not (cellEditMode and editUI.isMouseOver()):
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
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                cellEditMode = not cellEditMode
            elif event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_r:
                # Reset zoom and offset
                zoom = 1.0
                target_zoom = 1.0
                pan_velocity_x = 0
                pan_velocity_y = 0
                offset_x = 0
                offset_y = 0
    
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
    
    tick += dt

    # This is the entire draw loop.
    screen.fill((255, 255, 255))
    for cell in cells:
        cell.draw(screen, offset_x, offset_y, zoom)
        cell.update()
    
    for particle in particles:
        if type(particle) != Particle: print(f"Non-particle type found. {particle}"); continue
        particle.update(550, 550)
        particle.draw(screen, offset_x, offset_y, zoom)
    
    for laser in lasers:
        laser.draw(screen, offset_x, offset_y, zoom)
    
    foods = [particle for particle in particles if particle.type == "food"]
    wastes = [particle for particle in particles if particle.type == "waste"]
    
    foodWasteRatio = len(foods) / len(wastes)
    
    # Use the foodwaste ratio to determine how much waste to transmute to food
    if foodWasteRatio < 0.5:  # If there's too much waste compared to food
        conversion_chance = 0.3 * (1 - foodWasteRatio/0.5)  # More conversion chance when ratio is lower
        for waste in wastes[:10]:  # Convert up to 10 waste particles at a time
            if random.random() < conversion_chance:  # Weighted chance based on ratio
                waste.type = "food"
                waste.color = (255, 0, 0)  # Change color to green for food
        
    if foodWasteRatio < 0.3:
        write_text(screen, "Food: LOW", 10, 10, left=True)
    elif foodWasteRatio < 0.5:
        write_text(screen, "Food: OK", 10, 10, left=True)
    elif foodWasteRatio > 1.6:
        write_text(screen, "Food: ABUNDANT", 10, 10, left=True)
    elif foodWasteRatio > 1:
        write_text(screen, "Food: HIGH", 10, 10, left=True)
    else:
        write_text(screen, "Food: OK", 10, 10, left=True)   
    
    write_text(screen, "Food/Waste: {:.2f}".format(foodWasteRatio), 10, 30, left=True)
    write_text(screen, "Tick: {:.2f}".format(tick), 10, 50, left=True)
    
    editUI.draw(screen)
    
    write_text(screen, f"FPS: {int(clock.get_fps())}", 400, 10)
    FPSGraph()
    
    pygame.display.flip()

pygame.quit()