import cv2
import numpy as np
import heapq
import math

# Global variables for interactive clicking
clicked_points = []

def get_click(event, x, y, flags, param):
    """ Captures mouse clicks to set start and end points """
    global clicked_points
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(clicked_points) < 2:
            clicked_points.append((y, x))
            print(f"Point recorded at: {(y, x)}")

def get_walkable_grid(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image not found. Check the file path.")

    scale_percent = 20 
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

    _, thresh = cv2.threshold(resized, 120, 255, cv2.THRESH_BINARY)
    grid = (thresh == 255).astype(int)
    
    return grid, resized, thresh

def heuristic(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def astar_visualized(grid, start, end, display_img):
    """ A* algorithm with built-in OpenCV visualization """
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

        # --- VISUALIZATION LOGIC ---
        # Color the explored node light blue (BGR format)
        if current_pos != start and current_pos != end:
            display_img[current_pos[0], current_pos[1]] = [255, 170, 170] 

        # Update the OpenCV window every 50 nodes to animate it
        # (Lower number = smoother animation but slower calculation)
        if nodes_explored % 50 == 0:
            cv2.imshow("AI Pathfinding", display_img)
            # waitKey(1) is required to force OpenCV to draw the frame
            if cv2.waitKey(1) == 27: # Press ESC to cancel early
                print("Search cancelled by user.")
                return None
        # ---------------------------

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
                
                # Color nodes added to the "frontier" light green
                if neighbor != start and neighbor != end:
                    display_img[neighbor[0], neighbor[1]] = [170, 255, 170]

    return None

def main():
    image_path = "map.jpeg" 
    
    print("Loading image...")
    grid, original_img, thresh_img = get_walkable_grid(image_path)
    display_img = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)

    cv2.namedWindow("AI Pathfinding")
    cv2.setMouseCallback("AI Pathfinding", get_click)

    print("\nINTERACTIVE MODE:")
    print("1. CLICK on the map window to set the START point.")
    print("2. CLICK to set the END point.")
    print("3. Press 'ENTER' to watch the AI search.")

    while True:
        temp_img = display_img.copy()
        
        if len(clicked_points) > 0:
            cv2.circle(temp_img, (clicked_points[0][1], clicked_points[0][0]), 4, (0, 255, 0), -1)
        if len(clicked_points) > 1:
            cv2.circle(temp_img, (clicked_points[1][1], clicked_points[1][0]), 4, (255, 0, 0), -1)
            
        cv2.imshow("AI Pathfinding", temp_img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and len(clicked_points) == 2: # Enter key
            break
        elif key == 27: # ESC key
            return

    start = clicked_points[0]
    end = clicked_points[1]

    if grid[start[0]][start[1]] == 0 or grid[end[0]][end[1]] == 0:
        print("\n[!] ERROR: One of your points is inside a wall.")
        cv2.destroyAllWindows()
        return

    print("\nSearching for path... Watch the map window!")
    
    # We now pass display_img into the function so it can draw on it
    path = astar_visualized(grid, start, end, display_img)

    if path:
        print("Path found! Drawing routing...")
        # Draw the final path in thick red
        for i in range(len(path) - 1):
            pt1 = (path[i][1], path[i][0])
            pt2 = (path[i+1][1], path[i+1][0])
            cv2.line(display_img, pt1, pt2, (0, 0, 255), 2)
    else:
        print("\n[!] NO PATH FOUND.")

    # Show final result and wait for user to close
    cv2.imshow("AI Pathfinding", display_img)
    print("Press any key on the image window to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()