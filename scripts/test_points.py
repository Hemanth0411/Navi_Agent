import cv2
import os
import json
import sys
import numpy as np

# Assuming these are in your project structure (e.g., 'scripts' directory)
# Adjust imports if your structure is different or if copying code directly.
try:
    from .utils import print_with_color
    from .and_controller import AndroidController, list_all_devices
    from .config import load_config
except ImportError:
    # Fallback for standalone execution if not in package
    print("Warning: Running in standalone mode, imports might need adjustment "
          "or related files copied to the same directory.")
    # Define a basic print_with_color if colorama is not found or not in package
    try:
        from colorama import Fore, Style
        def print_with_color(text: str, color=""):
            color_map = {"red": Fore.RED, "green": Fore.GREEN, "yellow": Fore.YELLOW, "blue": Fore.BLUE}
            if color in color_map: print(color_map[color] + text + Style.RESET_ALL)
            else: print(text)
    except ImportError:
        def print_with_color(text: str, color=""):
            print(f"[{color.upper()}] {text}" if color else text)
    # You would need to copy AndroidController class here for true standalone
    # For now, this example will fail if AndroidController is not importable and no mock is used.


# Load configuration for AndroidController paths
try:
    configs = load_config()
except Exception: # Broad exception if config loading fails
    print_with_color("Warning: config.yaml/env not fully loaded. Using default paths for controller.", "yellow")
    configs = {
        "ANDROID_SCREENSHOT_DIR": "/sdcard/sparse_points_ss/",
        "ANDROID_XML_DIR": "/sdcard/sparse_points_xml/",
        "MIN_DIST": 30
    }


def draw_sparse_points_custom_labels( # Renamed function
    controller: AndroidController,
    output_dir: str,
    prefix: str,
    num_cols: int = 9,
    num_rows: int = 16,
    # 0-indexed rows that get the primary numeric sequence
    primary_numeric_label_rows_indices: list = [0, 4, 8, 12],
    point_size: int = 10,
    label_font_scale: float = 0.7,
    label_thickness: int = 2
):
    if not controller:
        print_with_color("AndroidController instance is required.", "red")
        return None, None

    os.makedirs(output_dir, exist_ok=True)
    screenshot_path = controller.get_screenshot(f"{prefix}_sparse_orig", output_dir)

    if screenshot_path == "ERROR" or not os.path.exists(screenshot_path):
        print_with_color(f"Failed to get/find screenshot: {screenshot_path}", "red")
        return None, None

    img = cv2.imread(screenshot_path)
    if img is None:
        print_with_color(f"Error: Could not read image at {screenshot_path}", "red")
        return None, None

    img_height, img_width = img.shape[:2]
    if img_height == 0 or img_width == 0:
        print_with_color("Image has zero dimensions.", "red")
        return screenshot_path, None

    col_spacing = img_width / (num_cols + 1)
    row_spacing = img_height / (num_rows + 1)

    all_points_info = []
    point_color = (0, 255, 0)
    label_color = (255, 255, 0)
    label_bg_color_rgb = (50, 50, 50) # Background for text, no alpha for cv2.rectangle

    # Counter for primary numeric labels (1,2,3... then 10,11,12...)
    primary_label_counter = 1

    for r_idx in range(num_rows):  # 0 to 15
        is_primary_numeric_row = r_idx in primary_numeric_label_rows_indices
        
        # Determine which primary row this sub-row falls under (if it's a sub-row)
        # And what its sub-row index is (0 for 'a', 1 for 'b', 2 for 'c')
        sub_row_index_in_block = -1
        if not is_primary_numeric_row:
            # Find the immediately preceding primary numeric row
            preceding_primary_row_idx = -1
            for primary_idx in reversed(primary_numeric_label_rows_indices):
                if r_idx > primary_idx:
                    preceding_primary_row_idx = primary_idx
                    break
            if preceding_primary_row_idx != -1:
                sub_row_index_in_block = r_idx - (preceding_primary_row_idx + 1)


        for c_idx in range(num_cols):  # 0 to 8
            center_x = int(round(col_spacing * (c_idx + 1)))
            center_y = int(round(row_spacing * (r_idx + 1)))

            half_size = point_size // 2
            pt1 = (center_x - half_size, center_y - half_size)
            pt2 = (center_x + half_size, center_y + half_size)
            cv2.rectangle(img, pt1, pt2, point_color, -1)

            point_label = ""
            if is_primary_numeric_row:
                point_label = str(primary_label_counter)
                primary_label_counter += 1
            elif sub_row_index_in_block >= 0 and sub_row_index_in_block < 3: # Max 'a', 'b', 'c'
                # Sub-rows: 1a, 2a, ..., 9a then 1b, 2b, ..., 9b
                column_part = str(c_idx + 1) # 1 to 9
                sub_char = chr(ord('a') + sub_row_index_in_block)
                point_label = f"{column_part}{sub_char}"
            else:
                point_label = f"r{r_idx+1}c{c_idx+1}" # Fallback generic label if logic fails

            all_points_info.append({
                "label": point_label,
                "coords_px": [center_x, center_y]
            })

            # Only draw labels for the primary numeric rows on the image
            if is_primary_numeric_row:
                text_to_draw = point_label
                (text_w, text_h), baseline = cv2.getTextSize(text_to_draw, cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, label_thickness)
                
                label_x = center_x - half_size - text_w - 5 
                label_y = center_y 
                label_x = max(label_x, 0)
                label_y = max(label_y + text_h // 2, text_h) 
                
                # Simple background rectangle (no transparency for simplicity here)
                bg_pt1 = (label_x - 2, label_y - text_h - baseline - 2)
                bg_pt2 = (label_x + text_w + 2, label_y + baseline + 2)
                cv2.rectangle(img, bg_pt1, bg_pt2, label_bg_color_rgb, -1)
                cv2.putText(img, text_to_draw, (label_x, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, label_color, label_thickness, cv2.LINE_AA)

    annotated_image_filename = f"{prefix}_sparse_points_custom.png"
    annotated_image_path = os.path.join(output_dir, annotated_image_filename)
    cv2.imwrite(annotated_image_path, img)
    print_with_color(f"Annotated image saved: {annotated_image_path}", "green")

    json_filename = f"{prefix}_sparse_points_info_custom.json"
    json_path = os.path.join(output_dir, json_filename)
    try:
        with open(json_path, 'w') as f_json: json.dump(all_points_info, f_json, indent=4)
        print_with_color(f"Points info JSON saved: {json_path}", "green")
    except Exception as e:
        print_with_color(f"Error saving JSON: {e}", "red"); json_path = None
    return annotated_image_path, json_path

# --- Main Execution Block ---
if __name__ == '__main__':
    output_base_dir = "./sparse_points_output_custom" # New output dir
    os.makedirs(output_base_dir, exist_ok=True)

    # --- Device Selection (same as before) ---
    device_list = list_all_devices()
    if not device_list: print_with_color("No device/emulator. Exiting.", "red"); sys.exit(1)
    selected_device = None
    if len(device_list) == 1: selected_device = device_list[0]
    else:
        print_with_color("Multiple devices:", "blue")
        for i, dev in enumerate(device_list): print_with_color(f"{i+1}. {dev}", "blue")
        try:
            choice = int(input("Select device: ")) - 1
            if 0 <= choice < len(device_list): selected_device = device_list[choice]
        except ValueError: pass
    if not selected_device: print_with_color("No device selected. Exiting.", "red"); sys.exit(1)
    print_with_color(f"Using device: {selected_device}", "green")
    
    # Attempt to initialize controller
    try:
        controller = AndroidController(selected_device) # Uses global 'configs'
        if controller.width == 0 or controller.height == 0:
            print_with_color("Failed to get device screen dimensions. Exiting.", "red"); sys.exit(1)
    except NameError: # If AndroidController wasn't properly available from imports
        print_with_color("ERROR: AndroidController class not found. Ensure imports are correct or define a mock for testing.", "red")
        sys.exit(1)
    except Exception as e:
        print_with_color(f"ERROR initializing AndroidController: {e}", "red")
        sys.exit(1)


    timestamp_prefix = f"test_{str(int(os.times().elapsed))[-6:]}"
    primary_rows_indices = [0, 4, 8, 12] # 1st, 5th, 9th, 13th

    annotated_img_p, points_json_p = draw_sparse_points_custom_labels(
        controller=controller,
        output_dir=output_base_dir,
        prefix=timestamp_prefix,
        num_cols=9,
        num_rows=16,
        primary_numeric_label_rows_indices=primary_rows_indices,
        point_size=12,
        label_font_scale=0.6, # Adjust for desired size
        label_thickness=1     # Adjust for desired boldness
    )

    if annotated_img_p and points_json_p:
        print_with_color(f"\nOriginal screenshot: {os.path.join(output_base_dir, f'{timestamp_prefix}_sparse_orig.png')}", "blue")
        print_with_color(f"Annotated image: {annotated_img_p}", "blue")
        print_with_color(f"Points JSON data: {points_json_p}", "blue")
        # You can add code here to print parts of the JSON for verification
        # with open(points_json_p, 'r') as f:
        #     data = json.load(f)
        #     print("\nSample points from JSON:")
        #     for i, item in enumerate(data):
        #         if i < 5 or (i >=9 and i<14) or (i >= 9*4 and i < 9*4+5) : # Show some variety
        #             print(item)
    else:
        print_with_color("Failed to generate image or JSON.", "red")