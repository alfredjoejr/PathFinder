import cv2
import numpy as np
import time
import json

def nothing(x):
    pass

def get_edge_density(roi, canny_min, canny_max):
    """ Calculates how cluttered the region is based on live Canny Edge thresholds. """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Use the live sliders to determine what counts as a 'sharp edge'
    edges = cv2.Canny(blurred, canny_min, canny_max)
    
    white_pixels = cv2.countNonZero(edges)
    total_pixels = edges.shape[0] * edges.shape[1]
    
    # Prevent division by zero if the ROI is completely empty
    if total_pixels == 0:
        return 0.0, edges
        
    density = (white_pixels / total_pixels) * 100
    return density, edges

def main():
    cap = cv2.VideoCapture(1) 
    
    if not cap.isOpened():
        print("[!] Error: Could not open Camera.")
        return

    # --- CREATE THE TUNING SLIDERS ---
    cv2.namedWindow("Brain Tuner")
    cv2.resizeWindow("Brain Tuner", 450, 200)
    
    # 1. Turn Threshold (Default 50 = 5.0%). Controls WHEN the bot decides to turn.
    cv2.createTrackbar("Turn Threshold", "Brain Tuner", 50, 200, nothing)
    # 2. Cutoff HUD (Default 75%). Crops the bottom of the screen to ignore text.
    cv2.createTrackbar("Crop HUD %", "Brain Tuner", 75, 100, nothing)
    # 3. Edge Detectors. Controls WHAT the bot considers a wall.
    cv2.createTrackbar("Edge Min", "Brain Tuner", 30, 255, nothing)
    cv2.createTrackbar("Edge Max", "Brain Tuner", 100, 255, nothing)

    print("\n" + "="*50)
    print("🚗 AUTONOMOUS DRIVING - LIVE CALIBRATION")
    print("-> Tune the sliders to ignore the HUD and highlight walls.")
    print("-> Press 'Q' to Quit.")
    print("="*50 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        h, w = frame.shape[:2]
        
        # --- 1. Read Live Calibration Variables ---
        # Divide by 10 to get a float (e.g., slider at 65 becomes 6.5%)
        obstacle_threshold = cv2.getTrackbarPos("Turn Threshold", "Brain Tuner") / 10.0
        
        # Convert the percentage slider to an actual pixel coordinate
        hud_crop_percent = cv2.getTrackbarPos("Crop HUD %", "Brain Tuner") / 100.0
        
        canny_min = cv2.getTrackbarPos("Edge Min", "Brain Tuner")
        canny_max = cv2.getTrackbarPos("Edge Max", "Brain Tuner")

        # --- 2. Isolate the Floor (Region of Interest) ---
        roi_top = int(h * 0.4) # Start slightly below the crosshair
        roi_bottom = int(h * hud_crop_percent) # Cut off exactly where the slider says
        roi = frame[roi_top:roi_bottom, :]
        
        # --- 3. Slice and Analyze ---
        third_w = int(w / 3)
        left_slice = roi[:, :third_w]
        center_slice = roi[:, third_w:third_w*2]
        right_slice = roi[:, third_w*2:]
        
        left_density, left_edges = get_edge_density(left_slice, canny_min, canny_max)
        center_density, center_edges = get_edge_density(center_slice, canny_min, canny_max)
        right_density, right_edges = get_edge_density(right_slice, canny_min, canny_max)
        
        # --- 4. Hardware Decision Logic ---
        action = "IDLE"
        
        # If the center wall is less dense than our threshold, keep walking forward
        if center_density < obstacle_threshold:
            action = "MOVE_FORWARD (Hold W)"
            color = (0, 255, 0) # Green
        else:
            color = (0, 0, 255) # Red
            # The center is blocked! Compare the left and right to see which is more open.
            if left_density < right_density:
                action = "TURN_LEFT (Mouse -X)"
            else:
                action = "TURN_RIGHT (Mouse +X)"

        # 5. Output to JSON for hardware reading
        instruction = {
            "timestamp": time.time(),
            "detected_state": {
                "left_blocked": round(left_density, 2),
                "center_blocked": round(center_density, 2),
                "right_blocked": round(right_density, 2)
            },
            "hardware_command": action
        }
        
        try:
            with open("immediate_command.json", "w") as f:
                json.dump(instruction, f, indent=4)
        except Exception:
            pass # Ignore temporary write locks

        # --- 6. Visual Debugging Feedback ---
        debug_edges = np.hstack((left_edges, center_edges, right_edges))
        debug_edges_bgr = cv2.cvtColor(debug_edges, cv2.COLOR_GRAY2BGR)
        
        cv2.line(debug_edges_bgr, (third_w, 0), (third_w, roi_bottom - roi_top), (255, 0, 0), 2)
        cv2.line(debug_edges_bgr, (third_w*2, 0), (third_w*2, roi_bottom - roi_top), (255, 0, 0), 2)
        
        cv2.putText(debug_edges_bgr, f"L: {left_density:.1f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(debug_edges_bgr, f"C: {center_density:.1f}%", (third_w + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(debug_edges_bgr, f"R: {right_density:.1f}%", (third_w*2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Display the current threshold on screen so you can see why it's making a decision
        cv2.putText(debug_edges_bgr, f"Threshold: {obstacle_threshold:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(debug_edges_bgr, f"CMD: {action}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Draw a rectangle on the main frame to show you exactly what part of the screen it's looking at
        cv2.rectangle(frame, (0, roi_top), (w, roi_bottom), (255, 0, 255), 2)

        cv2.imshow("Raw First-Person View", frame)
        cv2.imshow("Robot Brain (Edge Density)", debug_edges_bgr)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()