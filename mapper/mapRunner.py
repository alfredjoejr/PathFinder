import cv2
import numpy as np
import heapq
import math
import json 

SCALE_PERCENT = 20
SCALE_FACTOR = 100 / SCALE_PERCENT 
clicked_points_grid = []
clicked_points_high_res = []

def get_click(event, x, y, flags, param):
    """ Captures 3 clicks: Start, Facing Direction, and End """
    global clicked_points_grid, clicked_points_high_res
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(clicked_points_grid) < 3:
            clicked_points_high_res.append((y, x))
            clicked_points_grid.append((int(y / SCALE_FACTOR), int(x / SCALE_FACTOR)))
            
            if len(clicked_points_grid) == 1: print("1. Start Position locked.")
            elif len(clicked_points_grid) == 2: print("2. Facing Direction locked.")
            elif len(clicked_points_grid) == 3: print("3. End Target locked. Press ENTER to generate commands.")

def get_walkable_grid(image_path):
    img_full = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_full is None: raise ValueError("Image not found.")
    
    width = int(img_full.shape[1] * SCALE_PERCENT / 100)
    height = int(img_full.shape[0] * SCALE_PERCENT / 100)
    resized = cv2.resize(img_full, (width, height), interpolation=cv2.INTER_AREA)

    _, thresh = cv2.threshold(resized, 120, 255, cv2.THRESH_BINARY)
    
    kernel = np.ones((3, 3), np.uint8) 
    safe_thresh = cv2.erode(thresh, kernel, iterations=1)
    
    return (safe_thresh == 255).astype(int), img_full

def heuristic(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def astar(grid, start, end):
    rows, cols = grid.shape
    g_scores = {start: 0}
    open_list = [(0, start)]
    came_from = {}
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    while open_list:
        _, current = heapq.heappop(open_list)
        if current == end:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for d in directions:
            neighbor = (current[0] + d[0], current[1] + d[1])
            if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols) or grid[neighbor[0]][neighbor[1]] == 0:
                continue
            tentative_g = g_scores[current] + heuristic(current, neighbor)
            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                came_from[neighbor] = current
                g_scores[neighbor] = tentative_g
                heapq.heappush(open_list, (tentative_g + heuristic(neighbor, end), neighbor))
    return None

def has_line_of_sight(grid, p1, p2):
    y1, x1 = p1
    y2, x2 = p2
    dy = y2 - y1
    dx = x2 - x1
    distance = int(math.hypot(dx, dy))
    
    if distance == 0: return True
    
    for i in range(1, distance):
        t = i / distance
        y = int(y1 + t * dy)
        x = int(x1 + t * dx)
        if grid[y][x] == 0: 
            return False
    return True

def smooth_path(grid, path):
    if not path: return []
    smoothed = [path[0]]
    current_idx = 0
    
    while current_idx < len(path) - 1:
        furthest_visible = current_idx + 1
        for i in range(len(path) - 1, current_idx, -1):
            if has_line_of_sight(grid, path[current_idx], path[i]):
                furthest_visible = i
                break
        smoothed.append(path[furthest_visible])
        current_idx = furthest_visible
        
    return smoothed

def main():
    image_path = "map.jpeg" 
    grid, img_full = get_walkable_grid(image_path)
    base_display = cv2.cvtColor(img_full, cv2.COLOR_GRAY2BGR)

    cv2.namedWindow("Path to Command Sequence", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Path to Command Sequence", 900, 900) 
    cv2.setMouseCallback("Path to Command Sequence", get_click)

    print("\n" + "="*50)
    print("COMMAND SEQUENCE GENERATOR")
    print("1. CLICK to place START position.")
    print("2. CLICK to define INITIAL FACING direction.")
    print("3. CLICK to place END position.")
    print("4. Press ENTER.")
    print("="*50 + "\n")

    while True:
        temp_img = base_display.copy()
        
        if len(clicked_points_high_res) > 0: 
            cv2.circle(temp_img, (clicked_points_high_res[0][1], clicked_points_high_res[0][0]), 6, (0, 255, 0), -1)
        if len(clicked_points_high_res) > 1: 
            cv2.line(temp_img, (clicked_points_high_res[0][1], clicked_points_high_res[0][0]), 
                     (clicked_points_high_res[1][1], clicked_points_high_res[1][0]), (0, 255, 255), 2)
            cv2.circle(temp_img, (clicked_points_high_res[1][1], clicked_points_high_res[1][0]), 4, (0, 255, 255), -1)
        if len(clicked_points_high_res) > 2: 
            cv2.circle(temp_img, (clicked_points_high_res[2][1], clicked_points_high_res[2][0]), 6, (255, 0, 0), -1)
            
        cv2.imshow("Path to Command Sequence", temp_img)
        if cv2.waitKey(1) == 13 and len(clicked_points_grid) == 3:
            break

    start_grid = clicked_points_grid[0]
    facing_grid = clicked_points_grid[1]
    end_grid = clicked_points_grid[2]

    init_dy = facing_grid[0] - start_grid[0]
    init_dx = facing_grid[1] - start_grid[1]
    current_facing_angle = math.degrees(math.atan2(init_dy, init_dx))

    print("\nCalculating path...")
    raw_path = astar(grid, start_grid, end_grid)

    if not raw_path:
        print("[!] No path found!")
        return

    print("Path found! Smoothing waypoints...")
    waypoints = smooth_path(grid, raw_path)

    for i in range(len(waypoints) - 1):
        pt1 = (int(waypoints[i][1] * SCALE_FACTOR), int(waypoints[i][0] * SCALE_FACTOR))
        pt2 = (int(waypoints[i+1][1] * SCALE_FACTOR), int(waypoints[i+1][0] * SCALE_FACTOR))
        cv2.line(base_display, pt1, pt2, (0, 0, 255), 3)
        cv2.circle(base_display, pt2, 5, (255, 0, 255), -1) 

    cv2.imshow("Path to Command Sequence", base_display)

    # --- HARDWARE BOT INSTRUCTION GENERATION ---
    hardware_instructions = []
    
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i+1]
        
        dy = p2[0] - p1[0]
        dx = p2[1] - p1[1]
        
        target_angle = math.degrees(math.atan2(dy, dx))
        distance = math.hypot(dx, dy) * SCALE_FACTOR
        
        turn_amount = target_angle - current_facing_angle
        turn_amount = (turn_amount + 180) % 360 - 180 
        
        instruction = {
            "step": i + 1,
            "turn_angle_degrees": round(turn_amount, 2),
            "move_forward_pixels": round(distance, 2),
            "waypoint_reached": True 
        }
        hardware_instructions.append(instruction)
        
        current_facing_angle = target_angle

    # --- FILE DUMP IMPLEMENTATION ---
    output_filename = "bot_instructions.json"
    
    try:
        with open(output_filename, "w") as json_file:
            json.dump(hardware_instructions, json_file, indent=4)
            
        print("\n" + "#"*50)
        print(f"✅ SUCCESS: Instructions dumped to '{output_filename}'")
        print("#"*50 + "\n")
    except Exception as e:
        print(f"\n[!] ERROR writing to file: {e}\n")
    
    print("Press any key on the map window to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()