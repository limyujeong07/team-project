import pygame
import random
import math
import sys
import os
import array

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2)

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("STEALTH DETECTION")
clock = pygame.time.Clock()

# =========================================================
# 색상 정의
# =========================================================
WHITE = (240, 240, 240)
BLACK = (10, 10, 15)
GRID = (28, 32, 42)
PLAYER = (70, 255, 140)
WALL = (70, 100, 150)
WALL_BORDER = (25, 45, 85)
RED = (255, 70, 70)
GOAL = (255, 220, 70)
ITEM_FREEZE = (80, 220, 255)   
ITEM_GUN = (255, 200, 100)     
BULLET_COLOR = (255, 230, 120) 
GUARD_COLOR = (255, 170, 100)
GUARD_LIGHT_COLOR = (255, 255, 180, 40)
CCTV_COLOR = (255, 255, 200)
MINIMAP_BG = (18, 22, 30)
MINIMAP_BORDER = (80, 90, 110)
MINIMAP_GUN_COLOR = (128, 128, 128)  

# =========================================================
# 사운드 자체 생성 시스템 (외부 파일 없음도 100% 작동)
# =========================================================
def generate_laser_sound(duration=0.1, freq=800):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        current_freq = freq - (i / n_samples) * 400
        val = math.sin(2 * math.pi * current_freq * t)
        env = 1.0 - (i / n_samples)
        buf[i] = int(val * 16383 * env)
    return pygame.mixer.Sound(buffer=buf)

def generate_explosion_sound(duration=0.3, freq=150):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        noise = random.uniform(-1.0, 1.0) * 0.3
        val = math.sin(2 * math.pi * freq * t) + noise
        env = 1.0 - (i / n_samples)
        buf[i] = int(max(-1.0, min(1.0, val)) * 14000 * env)
    return pygame.mixer.Sound(buffer=buf)

def generate_clear_sound(duration=0.4):
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    notes = [440.0, 554.37, 659.25, 880.0]
    for i in range(n_samples):
        t = i / sample_rate
        note_idx = min(int((i / n_samples) * len(notes)), len(notes) - 1)
        val = math.sin(2 * math.pi * notes[note_idx] * t)
        env = 1.0 - (i / n_samples)
        buf[i] = int(val * 12000 * env)
    return pygame.mixer.Sound(buffer=buf)

sound_shoot = generate_laser_sound()
sound_death = generate_explosion_sound()
sound_clear = generate_clear_sound()

def play_sound(sound_obj):
    if sound_obj:
        sound_obj.play()

# =========================================================
# 폰트 및 월드 설정
# =========================================================
title_font = pygame.font.Font(None, 72)
menu_font = pygame.font.Font(None, 36)
main_font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 22)

WORLD_WIDTH = 3200
WORLD_HEIGHT = 2400
camera_x = 0
camera_y = 0

MINIMAP_W = 280
MINIMAP_H = 210
MINIMAP_SCALE_X = MINIMAP_W / WORLD_WIDTH
MINIMAP_SCALE_Y = MINIMAP_H / WORLD_HEIGHT
MINIMAP_MARGIN = 12  
MINIMAP_POS = (SCREEN_WIDTH - MINIMAP_W - MINIMAP_MARGIN, MINIMAP_MARGIN)

# =========================================================
# 게임 상태 및 플레이어 변수
# =========================================================
START = 0
PLAYING = 1
RESULT = 2
game_state = START
difficulty = "NORMAL"

player_size = 30
player_x = 150
player_y = 150
player_speed = 8
walk_cycle = 0

face_dx = 1.0
face_dy = 0.0

has_gun = False
bullets = []  
BULLET_SPEED = 16.0
BULLET_RADIUS = 4

best_time = 0.0
if os.path.exists("save.txt"):
    try:
        with open("save.txt", "r") as f:
            best_time = float(f.read().strip() or "0")
    except:
        best_time = 0.0

start_time = 0
survival_time = 0.0
final_time = 0.0
lives = 3
result_text = ""
freeze_timer = 0

walls = []
cctvs = []
freeze_items = []  
gun_items = []     
goal_rect = pygame.Rect(2950, 2100, 100, 100)

# =========================================================
# 충돌 및 레이캐스팅 유틸 함수
# =========================================================
def rect_collides(rect):
    for wall in walls:
        if rect.colliderect(wall):
            return True
    return False

def line_rect_collision(x1, y1, x2, y2, rect):
    steps = 90
    for i in range(steps):
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if rect.collidepoint(x, y):
            return True
    return False

def raycast_distance(x, y, angle_deg, max_dist):
    rad = math.radians(angle_deg)
    step = 10
    for d in range(0, int(max_dist) + 1, step):
        px = x + d * math.cos(rad)
        py = y + d * math.sin(rad)
        for w in walls:
            if w.collidepoint(px, py):
                return d
    return max_dist

def rect_line_intersection(rect, x1, y1, x2, y2):
    return line_rect_collision(x1, y1, x2, y2, rect)

# =========================================================
# 그래픽 드로잉 함수
# =========================================================
def draw_player(x, y, moving):
    global walk_cycle
    cx = int(x + player_size / 2)
    cy = int(y + player_size / 2)
    if moving:
        walk_cycle += 0.25
    else:
        walk_cycle = 0
    leg = math.sin(walk_cycle) * 5
    pygame.draw.ellipse(screen, (0, 0, 0), (cx - 18, cy + 24, 36, 12))
    pygame.draw.circle(screen, (20, 90, 50), (cx, cy + 5), 18)
    pygame.draw.circle(screen, PLAYER, (cx, cy), 18)
    pygame.draw.circle(screen, (255, 220, 180), (cx, cy - 20), 11)
    pygame.draw.circle(screen, BLACK, (cx - 4, cy - 22), 2)
    pygame.draw.circle(screen, BLACK, (cx + 4, cy - 22), 2)
    pygame.draw.line(screen, PLAYER, (cx, cy + 16), (cx - 8, cy + 30 + leg), 4)
    pygame.draw.line(screen, PLAYER, (cx, cy + 16), (cx + 8, cy + 30 - leg), 4)

def draw_treasure(x, y):
    glow = pygame.Surface((180, 180), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 220, 80, 40), (90, 90), 90)
    screen.blit(glow, (x - 45, y - 45))
    pygame.draw.rect(screen, (160, 100, 40), (x, y + 25, 90, 55), border_radius=10)
    pygame.draw.rect(screen, (210, 150, 60), (x, y, 90, 35), border_radius=10)
    pygame.draw.rect(screen, (255, 240, 120), (x + 38, y, 14, 80))

def draw_freeze_item(rect):
    rx = rect.x - camera_x
    ry = rect.y - camera_y
    r = pygame.Rect(rx, ry, rect.width, rect.height)
    pygame.draw.rect(screen, ITEM_FREEZE, r, border_radius=6)
    pygame.draw.rect(screen, (200, 250, 255), r, 2, border_radius=6)

def draw_gun_item(rect):
    rx = rect.x - camera_x
    ry = rect.y - camera_y
    r = pygame.Rect(rx, ry, rect.width, rect.height)
    pygame.draw.rect(screen, ITEM_GUN, r, border_radius=6)
    pygame.draw.rect(screen, (120, 90, 60), (r.x + 6, r.y + 10, r.width - 12, 8))
    pygame.draw.rect(screen, (90, 70, 50), (r.x + 20, r.y + 18, 10, 12))

# =========================================================
# 감시 오브젝트 클래스 (CCTV & 경비원)
# =========================================================
class CCTV:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.base_angle = angle
        self.angle = angle
        self.rotate_dir = 1
        self.rotate_speed = 1.0
        self.rotate_range = 70
        self.fov = 70
        self.distance = 620
    def update(self):
        if freeze_timer > 0:
            return
        self.angle += self.rotate_speed * self.rotate_dir
        if self.angle > self.base_angle + self.rotate_range:
            self.rotate_dir = -1
        if self.angle < self.base_angle - self.rotate_range:
            self.rotate_dir = 1
    def draw(self):
        sx = self.x - camera_x
        sy = self.y - camera_y
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        points = [(sx, sy)]
        start_angle = self.angle - self.fov / 2
        end_angle = self.angle + self.fov / 2
        for angle in range(int(start_angle), int(end_angle) + 1, 3):
            rad = math.radians(angle)
            final_dist = self.distance
            for d in range(20, self.distance, 12):
                px = self.x + d * math.cos(rad)
                py = self.y + d * math.sin(rad)
                hit = False
                for wall in walls:
                    if wall.collidepoint(px, py):
                        final_dist = d
                        hit = True
                        break
                if hit:
                    break
            end_x = sx + final_dist * math.cos(rad)
            end_y = sy + final_dist * math.sin(rad)
            points.append((end_x, end_y))
        if len(points) >= 3:
            alpha = 20 if freeze_timer > 0 else 35
            pygame.draw.polygon(surf, (255, 255, 120, alpha), points)
        screen.blit(surf, (0, 0))
        pygame.draw.circle(screen, (120, 120, 120), (int(sx), int(sy)), 20)
        pygame.draw.circle(screen, WHITE, (int(sx), int(sy)), 15)
    def detect(self, px, py):
        if freeze_timer > 0:
            return False
        dx = px - self.x
        dy = py - self.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist > self.distance:
            return False
        target_angle = math.degrees(math.atan2(dy, dx))
        diff = target_angle - self.angle
        while diff > 180: diff -= 360
        while diff < -180: diff += 360
        if abs(diff) > self.fov / 2:
            return False
        for wall in walls:
            if line_rect_collision(self.x, self.y, px, py, wall):
                return False
        return True

class Guard:
    def __init__(self, x, y, waypoints, speed=2.2):
        self.x = float(x)
        self.y = float(y)
        self.radius = 16
        self.waypoints = waypoints[:] if waypoints else [(x, y)]
        self.wp_index = 0
        self.speed = speed
        self.angle = random.uniform(0, 360)
        self.fov = 60
        self.max_view = 620 / 3  
        self.alive = True
    def update(self, dt):
        if not self.alive or freeze_timer > 0:
            return
        if self.waypoints:
            tx, ty = self.waypoints[self.wp_index]
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 0.05:
                step = self.speed
                if step > dist:
                    step = dist
                nx = self.x + (dx / dist) * step
                ny = self.y + (dy / dist) * step
                guard_rect = pygame.Rect(int(nx - self.radius), int(ny - self.radius), self.radius * 2, self.radius * 2)
                if rect_collides(guard_rect):
                    self.wp_index = (self.wp_index + 1) % len(self.waypoints)
                else:
                    self.x = nx
                    self.y = ny
                    if dist > 0.1:
                        self.angle = math.degrees(math.atan2(dy, dx))
            else:
                self.wp_index = (self.wp_index + 1) % len(self.waypoints)
    def can_see(self, px, py):
        if not self.alive or freeze_timer > 0:
            return False
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy)
        if dist > self.max_view:
            return False
        angle_to_tgt = math.degrees(math.atan2(dy, dx))
        diff = angle_to_tgt - self.angle
        while diff > 180: diff -= 360
        while diff < -180: diff += 360
        if abs(diff) > self.fov / 2:
            return False
        for w in walls:
            if line_rect_collision(self.x, self.y, px, py, w):
                return False
        return True
    def draw(self):
        if not self.alive:
            return
        sx = self.x - camera_x
        sy = self.y - camera_y
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        points = [(sx, sy)]
        start_angle = int(self.angle - self.fov / 2)
        end_angle = int(self.angle + self.fov / 2)
        for ang in range(start_angle, end_angle + 1, 3):
            d = raycast_distance(self.x, self.y, ang, self.max_view)
            ex = sx + d * math.cos(math.radians(ang))
            ey = sy + d * math.sin(math.radians(ang))
            points.append((ex, ey))
        if len(points) >= 3:
            pygame.draw.polygon(surf, GUARD_LIGHT_COLOR, points)
        screen.blit(surf, (0, 0))
        pygame.draw.circle(screen, (60, 40, 20), (int(sx), int(sy) + 3), self.radius)  
        pygame.draw.circle(screen, GUARD_COLOR, (int(sx), int(sy)), self.radius)
        
    def hit_by_bullet(self, bx, by, br):
        if not self.alive:
            return False
        # 사정거리는 그대로 두고, 피격 판정 범위만 2배 상향 (br * 2)
        return math.hypot(self.x - bx, self.y - by) <= (self.radius + (br * 2))

guards = []

# =========================================================
# 오픈형 파티션 맵 생성 (공간을 낭비하는 닫힌 방 완전 제거)
# =========================================================
def create_map():
    global walls, cctvs, freeze_items, gun_items, guards, has_gun, bullets
    walls = []
    cctvs = []
    freeze_items = []
    gun_items = []
    guards = []
    bullets = []
    has_gun = False
    
    # 1. 외곽 경계벽 생성
    walls.append(pygame.Rect(0, 0, WORLD_WIDTH, 80))
    walls.append(pygame.Rect(0, WORLD_HEIGHT - 80, WORLD_WIDTH, 80))
    walls.append(pygame.Rect(0, 0, 80, WORLD_HEIGHT))
    walls.append(pygame.Rect(WORLD_WIDTH - 80, 0, 80, WORLD_HEIGHT))
    
    # 2. 닫힌 'ㅁ'자 가두리 방을 완전히 없애고 탁 트인 단일 방향성 파티션 벽 배치
    structures = [
        # 세로형 우회로 벽 (통행이 완전히 불가능한 밀폐 구역 없음)
        (600, 80, 80, 700),
        (600, 1100, 80, 800),
        (1200, 400, 80, 900),
        (1200, 1600, 80, 700),
        (1800, 80, 80, 800),
        (1800, 1200, 80, 800),
        (2400, 400, 80, 1000),
        (2400, 1700, 80, 620),
        
        # 가로형 시야 차단 벽
        (200, 600, 400, 80),
        (800, 1200, 400, 80),
        (1400, 800, 400, 80),
        (2000, 1500, 400, 80),
    ]
    for s in structures:
        walls.append(pygame.Rect(s[0], s[1], s[2], s[3]))
        
    # 난이도 설정
    if difficulty == "EASY":
        cam_count, cam_speed, guard_count = 5, 0.7, 3
    elif difficulty == "NORMAL":
        cam_count, cam_speed, guard_count = 8, 1.0, 5
    else:
        cam_count, cam_speed, guard_count = 11, 1.4, 8
        
    # CCTV 배치
    while len(cctvs) < cam_count:
        x = random.randint(300, 2900)
        y = random.randint(300, 2100)
        if any(wall.collidepoint(x, y) for wall in walls):
            continue
        if any(math.dist((x, y), (cam.x, cam.y)) < 400 for cam in cctvs):
            continue
        cam = CCTV(x, y, random.randint(0, 360))
        cam.rotate_speed = cam_speed
        cctvs.append(cam)
        
    # 경비원 순찰 경로
    def random_patrol_path():
        pts = []
        tries = 0
        while len(pts) < 3 and tries < 300:
            tries += 1
            px = random.randint(200, WORLD_WIDTH - 200)
            py = random.randint(200, WORLD_HEIGHT - 200)
            if any(w.collidepoint(px, py) for w in walls):
                continue
            pts.append((px, py))
        return pts if pts else [(400, 400), (800, 800)]
        
    for _ in range(guard_count):
        path = random_patrol_path()
        g = Guard(path[0][0], path[0][1], path, speed=2.0)
        guards.append(g)
        
    # 아이템 랜덤 생성
    while len(freeze_items) < 4:
        rx = random.randint(200, WORLD_WIDTH - 250)
        ry = random.randint(200, WORLD_HEIGHT - 250)
        rect = pygame.Rect(rx, ry, 35, 35)
        if any(rect.colliderect(w) for w in walls): continue
        if rect.colliderect(goal_rect): continue
        freeze_items.append(rect)
        
    while len(gun_items) < 2:
        rx = random.randint(200, WORLD_WIDTH - 250)
        ry = random.randint(200, WORLD_HEIGHT - 250)
        rect = pygame.Rect(rx, ry, 35, 35)
        if any(rect.colliderect(w) for w in walls): continue
        if rect.colliderect(goal_rect): continue
        if any(rect.colliderect(it) for it in freeze_items): continue
        gun_items.append(rect)

create_map()

# =========================================================
# 메인 게임 루프 실행
# =========================================================
running = True
while running:
    dt = clock.tick(60)
    if freeze_timer > 0:
        freeze_timer -= dt
        if freeze_timer < 0:
            freeze_timer = 0
            
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if game_state == START:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: difficulty = "EASY"
                elif event.key == pygame.K_2: difficulty = "NORMAL"
                elif event.key == pygame.K_3: difficulty = "HARD"
                elif event.key == pygame.K_SPACE:
                    create_map()
                    player_x, player_y = 150, 150
                    lives = 3
                    start_time = pygame.time.get_ticks()
                    game_state = PLAYING
                    
        elif game_state == RESULT:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game_state = START
                
        if game_state == PLAYING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and has_gun:
                mag = math.hypot(face_dx, face_dy)
                dirx, diry = (face_dx / mag, face_dy / mag) if mag != 0 else (1.0, 0.0)
                sx = player_x + player_size / 2
                sy = player_y + player_size / 2
                bullets.append({
                    "x": sx, "y": sy,
                    "vx": dirx * BULLET_SPEED, "vy": diry * BULLET_SPEED,
                    "dist_left": (620 / 3) * 2.0, 
                    "radius": BULLET_RADIUS
                })
                has_gun = False  
                play_sound(sound_shoot)

    if game_state == PLAYING:
        survival_time = (pygame.time.get_ticks() - start_time) / 1000.0
        keys = pygame.key.get_pressed()
        move_x, move_y = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: move_x -= player_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: move_x += player_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]: move_y -= player_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: move_y += player_speed
            
        moving = (move_x != 0 or move_y != 0)
        if moving:
            mag = math.hypot(move_x, move_y)
            face_dx, face_dy = move_x / mag, move_y / mag
                
        next_rect = pygame.Rect(player_x + move_x, player_y + move_y, player_size, player_size)
        if not rect_collides(next_rect):
            player_x += move_x
            player_y += move_y
            
        player_rect = pygame.Rect(player_x, player_y, player_size, player_size)
        
        # 아이템 체크
        for it in [item for item in freeze_items if player_rect.colliderect(item)]:
            freeze_items.remove(it)
            freeze_timer += 3000  
            
        for g in [g for g in gun_items if player_rect.colliderect(g)]:
            gun_items.remove(g)
            has_gun = True
            
        if player_rect.colliderect(goal_rect):
            final_time = survival_time
            result_text = "MISSION CLEAR"
            play_sound(sound_clear)
            if best_time == 0 or final_time < best_time:
                best_time = final_time
                try:
                    with open("save.txt", "w") as f: f.write(f"{best_time}")
                except: pass
            game_state = RESULT
            
        camera_x = max(0, min(WORLD_WIDTH - SCREEN_WIDTH, player_x - SCREEN_WIDTH // 2))
        camera_y = max(0, min(WORLD_HEIGHT - SCREEN_HEIGHT, player_y - SCREEN_HEIGHT // 2))
        
        player_died = False
        for cam in cctvs:
            cam.update()
            if cam.detect(player_x + player_size / 2, player_y + player_size / 2):
                player_died = True
                break
                
        if not player_died:
            for g in guards: g.update(dt)
            for g in guards:
                if g.alive and g.can_see(player_x + player_size / 2, player_y + player_size / 2):
                    player_died = True
                    break
                    
        if player_died:
            lives -= 1
            play_sound(sound_death)
            player_x, player_y = 150, 150
            pygame.time.delay(250)
            if lives <= 0:
                final_time = survival_time
                result_text = "MISSION FAILED"
                game_state = RESULT
                
        # 총알 이동 및 범위 2배 상향 판정
        updated_bullets = []
        for b in bullets:
            if b["dist_left"] <= 0: continue
            prev_x, prev_y = b["x"], b["y"]
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["dist_left"] -= math.hypot(b["vx"], b["vy"])
            
            if any(rect_line_intersection(w, prev_x, prev_y, b["x"], b["y"]) for w in walls):
                continue
                
            hit_guard = None
            for g in guards:
                if g.alive and g.hit_by_bullet(b["x"], b["y"], b["radius"]):
                    hit_guard = g
                    break
            if hit_guard:
                hit_guard.alive = False
                continue
            updated_bullets.append(b)
        bullets = updated_bullets

    # ===================== 그래픽 렌더링 =====================
    screen.fill(BLACK)
    for x in range(int(-camera_x % 50), SCREEN_WIDTH, 50):
        pygame.draw.line(screen, GRID, (x, 0), (x, SCREEN_HEIGHT))
    for y in range(int(-camera_y % 50), SCREEN_HEIGHT, 50):
        pygame.draw.line(screen, GRID, (0, y), (SCREEN_WIDTH, y))
        
    if game_state == PLAYING:
        draw_treasure(goal_rect.x - camera_x, goal_rect.y - camera_y)
        for wall in walls:
            rect = pygame.Rect(wall.x - camera_x, wall.y - camera_y, wall.width, wall.height)
            pygame.draw.rect(screen, WALL, rect, border_radius=8)
            pygame.draw.rect(screen, WALL_BORDER, rect, 4, border_radius=8)
            
        for item in freeze_items: draw_freeze_item(item)
        for item in gun_items: draw_gun_item(item)
        for cam in cctvs: cam.draw()
        for g in guards: g.draw()
        for b in bullets:
            pygame.draw.circle(screen, BULLET_COLOR, (int(b["x"] - camera_x), int(b["y"] - camera_y)), b["radius"])
            
        draw_player(player_x - camera_x, player_y - camera_y, moving)
        
        if freeze_timer > 0:
            screen.blit(small_font.render(f"FREEZE: {freeze_timer / 1000.0:.1f}s", True, ITEM_FREEZE), (16, 16))
        if has_gun:
            screen.blit(small_font.render("GUN: 1 SHOT READY (LMB)", True, ITEM_GUN), (16, 40))
            
        # 미니맵 컴포넌트
        mmx, mmy = MINIMAP_POS
        pygame.draw.rect(screen, MINIMAP_BG, (mmx, mmy, MINIMAP_W, MINIMAP_H), border_radius=8)
        pygame.draw.rect(screen, MINIMAP_BORDER, (mmx, mmy, MINIMAP_W, MINIMAP_H), 2, border_radius=8)
        
        for w in walls:
            rx = mmx + int(w.x * MINIMAP_SCALE_X)
            ry = mmy + int(w.y * MINIMAP_SCALE_Y)
            rw = max(1, int(w.width * MINIMAP_SCALE_X))
            rh = max(1, int(w.height * MINIMAP_SCALE_Y))
            pygame.draw.rect(screen, (60, 75, 100), (rx, ry, rw, rh))
            
        gx = mmx + int(goal_rect.x * MINIMAP_SCALE_X)
        gy = mmy + int(goal_rect.y * MINIMAP_SCALE_Y)
        pygame.draw.rect(screen, GOAL, (gx, gy, max(1, int(goal_rect.width * MINIMAP_SCALE_X)), max(1, int(goal_rect.height * MINIMAP_SCALE_Y))))
        
        for cam in cctvs:
            pygame.draw.circle(screen, CCTV_COLOR, (mmx + int(cam.x * MINIMAP_SCALE_X), mmy + int(cam.y * MINIMAP_SCALE_Y)), 3)
        for g in guards:
            if g.alive:
                pygame.draw.circle(screen, GUARD_COLOR, (mmx + int(g.x * MINIMAP_SCALE_X), mmy + int(g.y * MINIMAP_SCALE_Y)), 3)
        for it in freeze_items:
            pygame.draw.rect(screen, ITEM_FREEZE, (mmx + int(it.x * MINIMAP_SCALE_X), mmy + int(it.y * MINIMAP_SCALE_Y), 4, 4))
        for it in gun_items:
            pygame.draw.rect(screen, MINIMAP_GUN_COLOR, (mmx + int(it.x * MINIMAP_SCALE_X), mmy + int(it.y * MINIMAP_SCALE_Y), 4, 4))
            
        pygame.draw.circle(screen, PLAYER, (mmx + int((player_x + player_size / 2) * MINIMAP_SCALE_X), mmy + int((player_y + player_size / 2) * MINIMAP_SCALE_Y)), 4)
        
    elif game_state == START:
        screen.blit(title_font.render("STEALTH DETECTION", True, WHITE), (210, 120))
        screen.blit(menu_font.render(f"CURRENT : {difficulty}", True, GOAL), (470, 280))
        screen.blit(main_font.render("1 : EASY", True, (120, 255, 120)), (540, 370))
        screen.blit(main_font.render("2 : NORMAL", True, (255, 255, 120)), (540, 430))
        screen.blit(main_font.render("3 : HARD", True, (255, 120, 120)), (540, 490))
        screen.blit(menu_font.render("PRESS SPACE TO START", True, WHITE), (390, 620))
        
    elif game_state == RESULT:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        color = PLAYER if result_text == "MISSION CLEAR" else RED
        screen.blit(title_font.render(result_text, True, color), (250, 150))
        screen.blit(menu_font.render(f"YOUR TIME : {final_time:.1f}", True, WHITE), (430, 350))
        screen.blit(menu_font.render(f"BEST TIME : {best_time:.1f}", True, GOAL), (430, 430))
        screen.blit(menu_font.render("PRESS R TO RETURN MENU", True, WHITE), (300, 620))
        
    pygame.display.update()

pygame.quit()
sys.exit()
