import cv2
import numpy as np
import heapq
import math

# Global variables to handle the scale difference
SCALE_PERCENT = 20
SCALE_FACTOR = 100 / SCALE_PERCENT # e.g., 5.0
clicked_points_grid = []
clicked_points_high_res = []

def get_click(event, x, y, flags, param):
    """ Captures mouse clicks and translates them to the mini-grid """
    global clicked_points_grid, clicked_points_high_res
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(clicked_points_grid) < 2:
            # Save the exact high-res pixel for drawing circles
            clicked_points_high_res.append((y, x))
            
            # Translate that pixel down to the 20% math grid
            grid_y = int(y / SCALE_FACTOR)
            grid_x = int(x / SCALE_FACTOR)
            clicked_points_grid.append((grid_y, grid_x))
            print(f"Point locked in!")

def get_walkable_grid(image_path):
    # Load the FULL resolution original image
    img_full = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_full is None:
        raise ValueError("Image not found. Check the file path.")

    # Create the tiny grid for math
    width = int(img_full.shape[1] * SCALE_PERCENT / 100)
    height = int(img_full.shape[0] * SCALE_PERCENT / 100)
    resized = cv2.resize(img_full, (width, height), interpolation=cv2.INTER_AREA)

    _, thresh = cv2.threshold(resized, 120, 255, cv2.THRESH_BINARY)
    grid = (thresh == 255).astype(int)
    
    # Notice we now return img_full, NOT resized!
    return grid, img_full

def heuristic(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def astar_visualized(grid, start, end, display_img):
    rows, cols = grid.shape
    g_scores = {start: 0}
    open_list = [(0, start)]
    came_from = {}
    
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), 
                  (1, 1), (1, -1), (-1, 1), (-1, -1)]

    nodes_explored = 0

    while open_list:
        nodes_explored += 1
        current_f, current_pos = heapq.heappop(open_list)

        # --- VISUALIZATION LOGIC (SCALED UP) ---
        if current_pos != start and current_pos != end:
            # Map the tiny grid coordinate back to a block on the high-res image
            r_start = int(current_pos[0] * SCALE_FACTOR)
            r_end = int(r_start + SCALE_FACTOR)
            c_start = int(current_pos[1] * SCALE_FACTOR)
            c_end = int(c_start + SCALE_FACTOR)
            
            # Color that block light blue
            display_img[r_start:r_end, c_start:c_end] = [255, 170, 170] 

        if nodes_explored % 50 == 0:
            cv2.imshow("AI Pathfinding", display_img)
            if cv2.waitKey(1) == 27:
                return None
        # ---------------------------------------

        if current_pos == end:
            path = []
            while current_pos in came_from:
                path.append(current_pos)
                current_pos = came_from[current_pos]
            path.append(start)
            return path[::-1]

        for d in directions:
            neighbor = (current_pos[0] + d[0], current_pos[1] + d[1])

            if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols):
                continue
                
            if grid[neighbor[0]][neighbor[1]] == 0:
                continue

            tentative_g = g_scores[current_pos] + heuristic(current_pos, neighbor)

            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                came_from[neighbor] = current_pos
                g_scores[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, end)
                heapq.heappush(open_list, (f_score, neighbor))
                
                # Color the frontier green
                if neighbor != start and neighbor != end:
                    r1 = int(neighbor[0] * SCALE_FACTOR)
                    c1 = int(neighbor[1] * SCALE_FACTOR)
                    display_img[r1:r1+int(SCALE_FACTOR), c1:c1+int(SCALE_FACTOR)] = [170, 255, 170]

    return None

def main():
    # Make sure this points to your map image!
    image_path = "map.jpeg" 
    
    print("Loading high-resolution image...")
    grid, img_full = get_walkable_grid(image_path)
    display_img = cv2.cvtColor(img_full, cv2.COLOR_GRAY2BGR)

    # Setup the window (This will now scale cleanly!)
    cv2.namedWindow("AI Pathfinding", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("AI Pathfinding", 900, 900) 
    cv2.setMouseCallback("AI Pathfinding", get_click)

    print("\nINTERACTIVE MODE:")
    print("1. CLICK on the map window to set the START point.")
    print("2. CLICK to set the END point.")
    print("3. Press 'ENTER' to watch the AI search.")

    while True:
        temp_img = display_img.copy()
        
        # Draw clicks using the High-Res coordinates
        if len(clicked_points_high_res) > 0:
            cv2.circle(temp_img, (clicked_points_high_res[0][1], clicked_points_high_res[0][0]), 8, (0, 255, 0), -1)
        if len(clicked_points_high_res) > 1:
            cv2.circle(temp_img, (clicked_points_high_res[1][1], clicked_points_high_res[1][0]), 8, (255, 0, 0), -1)
            
        cv2.imshow("AI Pathfinding", temp_img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and len(clicked_points_grid) == 2:
            break
        elif key == 27:
            return

    start_grid = clicked_points_grid[0]
    end_grid = clicked_points_grid[1]

    if grid[start_grid[0]][start_grid[1]] == 0 or grid[end_grid[0]][end_grid[1]] == 0:
        print("\n[!] ERROR: One of your points is inside a wall.")
        cv2.destroyAllWindows()
        return

    print("\nSearching for path... Watch the map window!")
    path = astar_visualized(grid, start_grid, end_grid, display_img)

    if path:
        print("Path found! Drawing routing...")
        # Draw the final path, mapped back to High-Res coordinates
        for i in range(len(path) - 1):
            # Center the line inside the block by adding half the scale factor
            pt1 = (int(path[i][1] * SCALE_FACTOR + SCALE_FACTOR/2), int(path[i][0] * SCALE_FACTOR + SCALE_FACTOR/2))
            pt2 = (int(path[i+1][1] * SCALE_FACTOR + SCALE_FACTOR/2), int(path[i+1][0] * SCALE_FACTOR + SCALE_FACTOR/2))
            cv2.line(display_img, pt1, pt2, (0, 0, 255), 4)
    else:
        print("\n[!] NO PATH FOUND.")

    cv2.imshow("AI Pathfinding", display_img)
    print("Press any key on the image window to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()