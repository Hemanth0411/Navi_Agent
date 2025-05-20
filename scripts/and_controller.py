import os
import subprocess
import xml.etree.ElementTree as ET
import shlex
from .config import load_config
from .utils import print_with_color


configs = load_config()

def _run_adb_command_base(device_id: str | None, command_args: list):
    """Internal helper to run ADB commands."""
    base_cmd = ["adb"]
    if device_id:
        base_cmd.extend(["-s", device_id])
    full_cmd = base_cmd + command_args
    
    cmd_str_for_print = " ".join(full_cmd) # For logging
    # Special handling for text input to avoid logging sensitive info directly
    if "input" in command_args and "text" in command_args:
        try:
            text_idx = command_args.index("text") + 1
            if text_idx < len(command_args):
                # Create a redacted command string for printing if it's text input
                temp_args = command_args[:]
                temp_args[text_idx] = "<hidden_text>"
                cmd_str_for_print = " ".join(base_cmd + temp_args)
        except ValueError:
            pass # Should not happen if 'text' is present
            
    print_with_color(f"Executing: {cmd_str_for_print}", "yellow")

    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, check=False) # check=False to inspect manually
        if result.returncode != 0:
            print_with_color(f"Command failed: {' '.join(full_cmd)}", "red")
            if result.stderr:
                print_with_color(f"Stderr: {result.stderr.strip()}", "red")
            return "ERROR", result.stderr.strip() if result.stderr else "Unknown ADB error"
        if result.stdout:
             # print_with_color(f"Output: {result.stdout.strip()}", "cyan") # Optional: for debugging success output
            pass # Most commands don't need their success stdout printed by default
        return result.stdout.strip(), None # Return stdout, no error
    except FileNotFoundError:
        msg = "Error: 'adb' command not found. Make sure ADB is installed and in your system's PATH."
        print_with_color(msg, "red")
        return "ERROR", msg
    except subprocess.CalledProcessError as e:
        # This won't be hit if check=False, but good for robustness if check=True is ever used
        msg = f"Error executing command: {e}. Stderr: {e.stderr.strip() if e.stderr else 'N/A'}"
        print_with_color(msg, "red")
        return "ERROR", msg
    except Exception as e:
        msg = f"An unexpected error occurred with adb command: {e}"
        print_with_color(msg, "red")
        return "ERROR", msg

class AndroidElement:
    def __init__(self, uid, bbox, attrib):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib

def list_all_devices():
    # Uses the new _run_adb_command_base (device_id is None for global adb commands)
    stdout, err = _run_adb_command_base(None, ["devices"])
    if err:
        return []
    devices = []
    # Output format of 'adb devices' might have extra lines, be careful with parsing
    # Example: 
    # List of devices attached
    # emulator-5554	device
    # another-device	offline
    for line in stdout.splitlines():
        if "\tdevice" in line and "attached" not in line.lower(): # Filter out header and non-device lines
            devices.append(line.split("\t")[0])
    return devices

def get_id_from_element(elem):
    bounds = elem.get("bounds")
    elem_w, elem_h = 0, 0 
    if bounds:
        try:
            coord = []
            for i in bounds.replace("][", ",").replace("[", "").replace("]", "").split(","):
                coord.append(int(i))
            if len(coord) == 4:
                 elem_w, elem_h = coord[2] - coord[0], coord[3] - coord[1]
            else:
                print_with_color(f"Unexpected bounds format for element {elem.get('class')}: {bounds}", "red")
        except ValueError as e:
            print_with_color(f"Error parsing bounds for element {elem.get('class')}: {bounds}, Error: {e}", "red")

    if elem.get("resource-id"):
        elem_id = elem.get("resource-id").replace("/", "_").replace(":", ".")
    else:
        elem_id = f"{elem.get('class', 'UnknownClass')}_{elem_w}_{elem_h}" # Add default for class
    if elem.get("content-desc") and len(elem.get("content-desc")) < 20:
        elem_id += "_" + elem.get("content-desc").replace(" ", "").replace("/", "_")

    role_hint = None
    res_id = elem.get("resource-id", "").lower()
    content_desc = elem.get("content-desc", "").lower()
    text_val = elem.get("text", "").lower() # Text attribute from XML
    elem_class = elem.get("class", "").lower()

    search_keywords = ["search", "query", "find", "search_box", "search_bar", "edit_query", "search_src_text", "search_plate"]
    nav_keywords = ["nav", "navigation", "navbar", "tab", "action_bar", "bottom_nav", "toolbar"] # Added toolbar

    # Search bar identification
    if (any(keyword in res_id for keyword in search_keywords) or
       any(keyword in content_desc for keyword in search_keywords) or
       any(keyword in text_val for keyword in search_keywords) or
       ("edittext" in elem_class and any(keyword in text_val + res_id + content_desc for keyword in ["search", "query"])) or
       "searchview" in elem_class):
        role_hint = "search_bar"
    # Navigation item/bar identification
    elif (any(keyword in res_id for keyword in nav_keywords) or
         any(keyword in content_desc for keyword in nav_keywords) or
         any(keyword in text_val for keyword in nav_keywords) or
         ("tabwidget" in elem_class or "bottomnavigationview" in elem_class or "toolbar" in elem_class and "action_bar" not in res_id)):
        if elem.get("clickable") == "true" and role_hint is None: # Prioritize search if already found
             role_hint = "nav_item"
        elif role_hint is None: # If not clickable but a nav container
             role_hint = "nav_bar_container"


    return elem_id, role_hint

def traverse_tree(xml_path, elem_list, attrib, add_index=False):
    path = []
    try:
        for event, elem in ET.iterparse(xml_path, ('start', 'end')):
            if event == 'start':
                parent_prefix = ""
                current_parent_element = None
                if len(path) > 0:
                    current_parent_element = path[-1]
                    parent_id_raw, _ = get_id_from_element(current_parent_element) # Parent hint not used here for prefix
                    parent_prefix = parent_id_raw + "."
                
                path.append(elem)
                if elem.get(attrib) == "true":
                    try:
                        current_bounds = elem.get("bounds")
                        if not current_bounds:
                            continue
                        coord = []
                        for i in current_bounds.replace("][", ",").replace("[", "").replace("]", "").split(","):
                            coord.append(int(i))
                        if len(coord) != 4: continue

                        center = (coord[0] + coord[2]) // 2, (coord[1] + coord[3]) // 2
                        close = False
                        min_dist_val = int(configs.get("MIN_DIST", 30))
                        for e in elem_list:
                            if e.bbox and len(e.bbox) == 2 and e.bbox[0] and len(e.bbox[0]) == 2 and e.bbox[1] and len(e.bbox[1]) == 2:
                                e_center_x = (e.bbox[0][0] + e.bbox[1][0]) // 2
                                e_center_y = (e.bbox[0][1] + e.bbox[1][1]) // 2
                                if abs(e_center_x - center[0]) + abs(e_center_y - center[1]) < min_dist_val:
                                    close = True
                                    break
                        if not close:
                            elem_id_raw, role_hint = get_id_from_element(elem)
                            elem_id = parent_prefix + elem_id_raw
                            if add_index:
                                elem_id += "." + elem.get("index", "0")
                            
                            current_attrib_value = attrib # This is "clickable" or "focusable"
                            if role_hint:
                                current_attrib_value += f",{role_hint}"
                                # If a parent was a nav_bar_container, this item might be a nav_item
                                if current_parent_element is not None:
                                    _, parent_role_hint = get_id_from_element(current_parent_element)
                                    if parent_role_hint == "nav_bar_container" and "nav_item" not in current_attrib_value:
                                         current_attrib_value += ",nav_item"


                            elem_list.append(AndroidElement(elem_id, (tuple(coord[0:2]), tuple(coord[2:4])), current_attrib_value))
                    except Exception as e:
                        print_with_color(f"Error processing element: {elem.tag} attributes: {elem.attrib} with error {e}", "red")
                        continue
            elif event == 'end':
                if path and path[-1] == elem: 
                     path.pop()
    except ET.ParseError as e:
        print_with_color(f"Error parsing XML file {xml_path}: {e}", "red")

class AndroidController:
    def __init__(self, device):
        self.device = device
        self.device_screenshot_dir = configs.get("ANDROID_SCREENSHOT_DIR", "/sdcard/").replace("\\\\", "/")
        self.device_xml_dir = configs.get("ANDROID_XML_DIR", "/sdcard/").replace("\\\\", "/")
        
        _run_adb_command_base(self.device, ["shell", "mkdir", "-p", self.device_screenshot_dir])
        _run_adb_command_base(self.device, ["shell", "mkdir", "-p", self.device_xml_dir])

        self.width, self.height = self.get_screen_resolution()
        if self.width == 0 and self.height == 0:
            print_with_color("Failed to get device size. Ensure the device is connected and accessible.", "red")

    def _execute_command(self, command_args: list):
        """Helper to execute commands for this specific device."""
        return _run_adb_command_base(self.device, command_args)

    def get_screen_resolution(self):
        stdout, err = self._execute_command(["shell", "wm", "size"])
        if err or not stdout or "Physical size:" not in stdout:
            print_with_color(f"Could not determine screen resolution. Error: {err if err else 'No output'}", "red")
            return 0, 0
        try:
            resolution_str = stdout.split("Physical size:")[1].strip()
            width, height = map(int, resolution_str.split('x'))
            print_with_color(f"Detected screen resolution: {width}x{height}", "green")
            return width, height
        except Exception as e:
            print_with_color(f"Error parsing screen resolution from output '{stdout}': {e}", "red")
            return 0, 0

    def get_screenshot(self, prefix, local_save_dir):
        # Ensure local_save_dir exists
        os.makedirs(local_save_dir, exist_ok=True)
        device_file_name = prefix + '.png'
        device_file_path = os.path.join(self.device_screenshot_dir, device_file_name).replace("\\", "/")
        local_file_path = os.path.join(local_save_dir, device_file_name)
        
        _, err_cap = self._execute_command(["shell", "screencap", "-p", device_file_path])
        if err_cap:
            # Attempt to provide more info if screencap fails
            self._execute_command(["shell", "ls", "-ld", self.device_screenshot_dir])
            return "ERROR"
        
        _, err_pull = self._execute_command(["pull", device_file_path, local_file_path])
        if err_pull:
            return "ERROR"
        return local_file_path

    def get_xml(self, prefix, local_save_dir):
        os.makedirs(local_save_dir, exist_ok=True)
        device_file_name = prefix + '.xml'
        device_file_path = os.path.join(self.device_xml_dir, device_file_name).replace("\\", "/")
        local_file_path = os.path.join(local_save_dir, device_file_name)

        _, err_dump = self._execute_command(["shell", "uiautomator", "dump", device_file_path])
        if err_dump:
            self._execute_command(["shell", "ls", "-ld", self.device_xml_dir])
            return "ERROR"
            
        _, err_pull = self._execute_command(["pull", device_file_path, local_file_path])
        if err_pull:
            return "ERROR"
        return local_file_path

    def tap(self, x, y):
        return self._execute_command(["shell", "input", "tap", str(x), str(y)])[0]

    def text(self, input_str):
        escaped_str = input_str.replace(' ', '%s')
        escaped_str = escaped_str.replace("'", "'\\''") 
        return self._execute_command(["shell", "input", "text", escaped_str])[0]

    def long_press(self, x, y, duration=1000):
        return self._execute_command(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)])[0]

    def swipe_element(self, x, y, direction, distance_str="medium"):
        if self.height == 0: 
            print_with_color("Screen height is 0, cannot perform element swipe. Check device connection.","red")
            return "ERROR"
        
        unit_dist_base = self.height // 20 # Base unit distance (e.g., 5% of screen height)
        
        distance_str_lower = distance_str.lower()
        if distance_str_lower == "short":
            unit_dist = unit_dist_base # e.g., 5%
            duration = 200 
        elif distance_str_lower == "medium":
            unit_dist = unit_dist_base * 2 # e.g., 10%
            duration = 400
        elif distance_str_lower == "long":
            unit_dist = unit_dist_base * 4 # e.g., 20%
            duration = 800
        else:
            print_with_color(f"Invalid swipe_element distance: {distance_str}, defaulting to medium", "yellow")
            unit_dist = unit_dist_base * 2 
            duration = 400
            
        offset_x, offset_y = 0, 0
        direction_lower = direction.lower()
        if direction_lower == "up": offset_y = -unit_dist
        elif direction_lower == "down": offset_y = unit_dist
        elif direction_lower == "left": offset_x = -unit_dist
        elif direction_lower == "right": offset_x = unit_dist
        else:
            print_with_color(f"Invalid swipe direction: {direction}", "red")
            return "ERROR"
            
        end_x, end_y = x + offset_x, y + offset_y
        # Ensure swipe coordinates are within bounds
        end_x = max(0, min(self.width - 1, end_x))
        end_y = max(0, min(self.height - 1, end_y))
        start_x_clamped = max(0, min(self.width - 1, x))
        start_y_clamped = max(0, min(self.height - 1, y))

        return self._execute_command(["shell", "input", "swipe", 
                                    str(start_x_clamped), str(start_y_clamped), 
                                    str(end_x), str(end_y), str(duration)])[0]

    def swipe_precise(self, start_coords, end_coords, duration=400):
        start_x, start_y = start_coords
        end_x, end_y = end_coords
        return self._execute_command(["shell", "input", "swipe", 
                                    str(start_x), str(start_y), 
                                    str(end_x), str(end_y), str(duration)])[0]

    def swipe_screen_direction(self, direction: str, distance_factor=0.5, duration_ms=300):
        if not self.width or not self.height:
            print_with_color("Cannot perform swipe_screen_direction without screen resolution.", "red")
            return "ERROR"

        center_x, center_y = self.width // 2, self.height // 2
        swipe_dist_y = int(self.height * distance_factor / 2)
        swipe_dist_x = int(self.width * distance_factor / 2)

        start_x, start_y, end_x, end_y = 0, 0, 0, 0
        direction_lower = direction.lower()

        if direction_lower == "up":
            start_x, start_y = center_x, center_y + swipe_dist_y
            end_x, end_y = center_x, center_y - swipe_dist_y
        elif direction_lower == "down":
            start_x, start_y = center_x, center_y - swipe_dist_y
            end_x, end_y = center_x, center_y + swipe_dist_y
        elif direction_lower == "left":
            start_x, start_y = center_x + swipe_dist_x, center_y
            end_x, end_y = center_x - swipe_dist_x, center_y
        elif direction_lower == "right":
            start_x, start_y = center_x - swipe_dist_x, center_y
            end_x, end_y = center_x + swipe_dist_x, center_y
        else:
            print_with_color(f"Invalid swipe direction: {direction}", "red")
            return "ERROR"

        # Ensure coordinates are within bounds
        start_x = max(0, min(self.width - 1, start_x))
        start_y = max(0, min(self.height - 1, start_y))
        end_x = max(0, min(self.width - 1, end_x))
        end_y = max(0, min(self.height - 1, end_y))
        
        return self.swipe_precise((start_x, start_y), (end_x, end_y), duration_ms)

    def press_keyevent(self, keycode):
        return self._execute_command(["shell", "input", "keyevent", str(keycode)])[0]

    def back(self): 
        return self.press_keyevent(4)

    def press_home(self):
        return self.press_keyevent(3)

    def press_enter(self):
        return self.press_keyevent(66)

    def press_delete(self):
        return self.press_keyevent(67) 

    def press_tab(self):
        return self.press_keyevent(61)

    def press_power(self):
        return self.press_keyevent(26)

    def volume_up(self):
        return self.press_keyevent(24)

    def volume_down(self):
        return self.press_keyevent(25)

    def press_mute(self):
        return self.press_keyevent(164) 
        
    def press_app_switch(self): # Already Exists
        return self.press_keyevent(187) 

    def press_media_play_pause(self):
        return self.press_keyevent(85)

    def press_media_next(self):
        return self.press_keyevent(87)

    def press_media_previous(self): 
        return self.press_keyevent(88)

    def open_notifications(self):
        return self._execute_command(["shell", "cmd", "statusbar", "expand-notifications"])[0]

    def close_notifications(self):
        return self._execute_command(["shell", "cmd", "statusbar", "collapse"])[0]
    
    def launch_app(self, package_name: str):
        """
        Launches an application using its package name.
        """
        print_with_color(f"Attempting to launch app: {package_name}", "blue")
        # This command simulates a launcher tap.
        # It brings the app to the foreground if already running or starts its main activity.
        stdout, err = self._execute_command(["shell", "monkey", "-p", package_name,
                                             "-c", "android.intent.category.LAUNCHER", "1"])
        if err:
            print_with_color(f"Error launching app {package_name}: {err}", "red")
            # Fallback: Try am start (might be less reliable for bringing to front if already open in a specific state)
            print_with_color(f"Trying fallback launch for {package_name} with 'am start'", "yellow")
            stdout_am, err_am = self._execute_command(["shell", "am", "start", "-n", f"{package_name}/$(cmd package resolve-activity -c android.intent.category.LAUNCHER {package_name} | sed -n 's/.*name=\(.*\/.[^ ]*\).*/\\1/p')"])
            if err_am:
                 print_with_color(f"Fallback launch also failed for {package_name}: {err_am}", "red")
                 return "ERROR", err_am
            # Check if am start actually worked (it often returns 0 even if the activity isn't found)
            # A more robust check would be to see if the foreground app changed, but that's more complex here.
            # For now, assume it might have worked if no direct error.
            print_with_color(f"Fallback launch command executed for {package_name}. Check device.", "green")
            return stdout_am, None

        print_with_color(f"App {package_name} launch command sent.", "green")
        return stdout, None
    
    def close_app(self, package_name: str):
        """
        Closes an application using its package name.
        """
        print_with_color(f"Attempting to close app: {package_name}", "blue")
        stdout, err = self._execute_command(["shell", "am", "force-stop", package_name])
        if err:
            print_with_color(f"Error closing app {package_name}: {err}", "red")
            return "ERROR", err
        print_with_color(f"App {package_name} close command sent.", "green")
        return stdout, None