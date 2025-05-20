import cv2
import os
import json
import sys # For device selection
import numpy as np # Potentially needed if and_controller uses it for image fallbacks

# --- Assuming this script is in the 'scripts' directory ---
# Adjust these imports if your directory structure is different or if you copied code
try:
    from .utils import print_with_color
    from .and_controller import AndroidController, list_all_devices
    from .config import load_config # AndroidController uses configs
except ImportError:
    print("Error: Make sure this script is in the 'scripts' directory and can import other modules.")
    print("Alternatively, copy the necessary classes/functions (AndroidController, utils) into this script.")
    sys.exit(1)

# Load configuration (AndroidController depends on it for device paths)
# Create a dummy config if you don't want to rely on the full config.py for this test
try:
    configs = load_config() # Assumes config.yaml exists or env vars are set
except FileNotFoundError:
    print_with_color("Warning: config.yaml not found. Using default paths for controller.", "yellow")
    configs = {
        "ANDROID_SCREENSHOT_DIR": "/sdcard/autoagent_screenshots/",
        "ANDROID_XML_DIR": "/sdcard/autoagent_xmls/",
        "MIN_DIST": 30 # Default from original code
    }
    # You might need to manually set other configs if AndroidController uses them
    # or modify AndroidController to not require them for this test.


# --- The Grid Drawing Function (Copied from previous response) ---
def draw_grid_and_get_info(controller, output_dir, prefix, grid_rows=10, grid_cols=4, dark_mode=False):
    """
    Takes a screenshot, draws a grid, labels grid cells, and saves info
    including cell center and quadrant centers.
    """
    if not controller:
        print_with_color("AndroidController instance is required.", "red")
        return None, None, None

    screenshot_path = controller.get_screenshot(f"{prefix}_grid_orig", output_dir)
    xml_path = controller.get_xml(f"{prefix}_grid", output_dir) # Assuming you still want the XML

    if screenshot_path == "ERROR" or not os.path.exists(screenshot_path):
        print_with_color(f"Failed to get or find screenshot at {screenshot_path}", "red")
        return None, xml_path, None
    # if xml_path == "ERROR": # Decide how to handle XML failure if needed
    #     print_with_color("Failed to get XML dump.", "red")

    img = cv2.imread(screenshot_path)
    if img is None:
        print_with_color(f"Error: Could not read image at {screenshot_path}", "red")
        return None, xml_path, None

    img_height, img_width = img.shape[:2]
    if img_height == 0 or img_width == 0:
        print_with_color("Image has zero dimensions, cannot draw grid.", "red")
        return screenshot_path, xml_path, None

    if dark_mode:
        line_color, text_color, text_bg_color = (200, 200, 200), (255, 255, 255), (50, 50, 50)
    else:
        line_color, text_color, text_bg_color = (50, 50, 50), (0, 0, 0), (220, 220, 220)

    cell_height_exact = img_height / grid_rows # Use float for precise quadrant calc later
    cell_width_exact = img_width / grid_cols  # Use float for precise quadrant calc later

    # For drawing lines, use integer division as before
    cell_draw_height = img_height // grid_rows
    cell_draw_width = img_width // grid_cols

    for i in range(1, grid_rows):
        y = i * cell_draw_height
        cv2.line(img, (0, y), (img_width, y), line_color, 1)
    for i in range(1, grid_cols):
        x = i * cell_draw_width
        cv2.line(img, (x, 0), (x, img_height), line_color, 1)

    grid_cell_info_list = []
    cell_number = 1

    # 3. Get coordinates and 4. Label grids
    for r in range(grid_rows):
        for c in range(grid_cols):
            # Use exact float values for boundary calculations for higher precision of quadrant centers
            x1_exact = c * cell_width_exact
            y1_exact = r * cell_height_exact
            x2_exact = (c + 1) * cell_width_exact
            y2_exact = (r + 1) * cell_height_exact

            # For cell bounds in JSON and center, integer rounding is fine
            x1_int = int(round(x1_exact))
            y1_int = int(round(y1_exact))
            # Ensure x2/y2 are at least x1/y1 + 1 if they round to the same due to small cells
            x2_int = max(x1_int + 1, int(round(x2_exact)))
            y2_int = max(y1_int + 1, int(round(y2_exact)))


            current_cell_width = x2_exact - x1_exact
            current_cell_height = y2_exact - y1_exact

            center_x = x1_exact + current_cell_width / 2
            center_y = y1_exact + current_cell_height / 2

            # --- START OF MODIFICATION ---
            # Calculate quadrant centers using the exact float boundaries and dimensions
            q_centers = {
                "top_left": [
                    int(round(x1_exact + current_cell_width * 0.25)),
                    int(round(y1_exact + current_cell_height * 0.25))
                ],
                "top_right": [
                    int(round(x1_exact + current_cell_width * 0.75)),
                    int(round(y1_exact + current_cell_height * 0.25))
                ],
                "bottom_left": [
                    int(round(x1_exact + current_cell_width * 0.25)),
                    int(round(y1_exact + current_cell_height * 0.75))
                ],
                "bottom_right": [
                    int(round(x1_exact + current_cell_width * 0.75)),
                    int(round(y1_exact + current_cell_height * 0.75))
                ]
            }
            # --- END OF MODIFICATION ---

            label_pos_x, label_pos_y = x1_int + 5, y1_int + 20
            label_text = str(cell_number)
            (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            if label_pos_y - text_h - 2 > 0 and label_pos_x + text_w + 2 < img_width:
                cv2.rectangle(img, (label_pos_x - 2, label_pos_y - text_h - 2),
                              (label_pos_x + text_w + 2, label_pos_y + 2), text_bg_color, -1)
            cv2.putText(img, label_text, (label_pos_x, label_pos_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2, cv2.LINE_AA)

            grid_cell_info_list.append({
                "cell_id": cell_number,
                "bounds_px": [x1_int, y1_int, x2_int, y2_int],
                "center_px": [int(round(center_x)), int(round(center_y))],
                "quadrant_centers_px": q_centers # --- MODIFICATION: Add quadrant centers ---
            })
            cell_number += 1

    annotated_image_filename = f"{prefix}_gridded.png"
    annotated_image_path = os.path.join(output_dir, annotated_image_filename)
    cv2.imwrite(annotated_image_path, img)
    print_with_color(f"Annotated grid image saved to: {annotated_image_path}", "green")

    grid_info_filename = f"{prefix}_grid_info.json"
    grid_info_path = os.path.join(output_dir, grid_info_filename)
    try:
        with open(grid_info_path, 'w') as f_json:
            json.dump(grid_cell_info_list, f_json, indent=4)
        print_with_color(f"Grid cell info (with quadrant centers) saved to: {grid_info_path}", "green")
    except Exception as e:
        print_with_color(f"Error saving grid info JSON: {e}", "red")

    return annotated_image_path, xml_path, grid_cell_info_list

# --- Main execution logic ---
if __name__ == '__main__':
    output_base_dir = "./grid_test_output"
    os.makedirs(output_base_dir, exist_ok=True)

    # --- Connect to Android Device/Emulator ---
    device_list = list_all_devices()
    if not device_list:
        print_with_color("No device/emulator found. Please connect one and ensure USB debugging is enabled.", "red")
        sys.exit(1)

    selected_device = None
    if len(device_list) == 1:
        selected_device = device_list[0]
        print_with_color(f"Automatically selected device: {selected_device}", "green")
    else:
        print_with_color("Multiple devices/emulators found. Please select one:", "blue")
        for i, dev in enumerate(device_list):
            print_with_color(f"{i + 1}. {dev}", "blue")
        while True:
            try:
                choice = int(input("Enter the number of the device: "))
                if 1 <= choice <= len(device_list):
                    selected_device = device_list[choice - 1]
                    break
                else:
                    print_with_color("Invalid choice.", "red")
            except ValueError:
                print_with_color("Invalid input. Please enter a number.", "red")

    if not selected_device:
        print_with_color("No device selected. Exiting.", "red")
        sys.exit(1)

    print_with_color(f"Using device: {selected_device}", "green")
    
    # Initialize Android Controller
    # Pass the global `configs` dictionary to the controller
    controller = AndroidController(selected_device)
    if controller.width == 0 or controller.height == 0:
         print_with_color("Failed to initialize controller or get screen dimensions. Exiting.", "red")
         sys.exit(1)

    # --- Parameters for the grid ---
    timestamp = str(int(os.times().elapsed)) # Simple unique prefix
    num_rows = 10 # You can change this
    num_cols = 5  # You can change this
    use_dark_mode_text = False # Change if your emulator UI is dark

    print_with_color(f"\nGenerating grid ({num_rows}x{num_cols}) for current screen...", "yellow")

    annotated_img_path, xml_dump_path, grid_cell_data = draw_grid_and_get_info(
        controller=controller,
        output_dir=output_base_dir,
        prefix=f"test_{timestamp}",
        grid_rows=num_rows,
        grid_cols=num_cols,
        dark_mode=use_dark_mode_text
    )

    if annotated_img_path:
        print(f"\n--- Outputs ---")
        print(f"Original Screenshot (used for drawing grid): {os.path.join(output_base_dir, f'test_{timestamp}_grid_orig.png')}")
        print(f"Annotated Image with Grid: {annotated_img_path}")
        if xml_dump_path and xml_dump_path != "ERROR":
            print(f"XML Dump: {xml_dump_path}")
        else:
            print_with_color(f"XML Dump: Failed or not available.", "yellow")
        
        json_output_path = os.path.join(output_base_dir, f"test_{timestamp}_grid_info.json")
        if os.path.exists(json_output_path):
            print(f"Grid Cell Info (JSON): {json_output_path}")
            # Optionally print some of the JSON data
            # if grid_cell_data:
            #     print("\nSample Grid Cell Data:")
            #     for i, cell_info in enumerate(grid_cell_data[:3]): # Print first 3 cells
            #         print(f"  Cell ID: {cell_info['cell_id']}, Center (px): {cell_info['center_px']}, Bounds (px): {cell_info['bounds_px']}")
            #     if len(grid_cell_data) > 3:
            #         print("  ...")
        else:
            print_with_color("Grid Cell Info (JSON): Failed to save.", "yellow")

    else:
        print_with_color("Failed to generate gridded image and coordinates.", "red")

    print_with_color("\nTest finished. Check the 'grid_test_output' directory.", "blue")