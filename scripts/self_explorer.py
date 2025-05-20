import argparse
import datetime
import os
import sys
import time
import re
import json

import argparse

from . import prompts
from .config import load_config
from .and_controller import list_all_devices, AndroidController, traverse_tree 
from .model import (parse_explore_rsp, parse_reflect_rsp, OpenAIModel, QwenModel, GeminiModel,
                    parse_initial_input_analysis, parse_exploration_step_rsp)
from .utils import print_with_color, draw_bbox_multi

configs = load_config()

# --- MAIN FUNCTION MODIFIED ---
def main(package_name_arg: str | None = None,
        user_input_arg: str | None = None,
        root_dir_arg: str | None = None,
        app_name_for_dir_arg: str | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", help="Package name of the target app.")
    parser.add_argument("--input", help="Task description or general app description for exploration.")
    parser.add_argument("--root_dir", default="./", help="Root directory for outputs.")
    parser.add_argument("--app_name_for_dir", help="Optional: Name for the app directory (defaults to package name).")


    if package_name_arg is None or user_input_arg is None:
        args_parsed = parser.parse_args()
        package_name = args_parsed.package
        user_input = args_parsed.input
        root_dir = args_parsed.root_dir if root_dir_arg is None else root_dir_arg
        app_name_for_output_dir = args_parsed.app_name_for_dir if app_name_for_dir_arg is None else app_name_for_dir_arg    
    else:
        package_name = package_name_arg
        user_input = user_input_arg
        root_dir = "./" if root_dir_arg is None else root_dir_arg
        app_name_for_output_dir = package_name if app_name_for_dir_arg is None else app_name_for_dir_arg # Default behavio

    if not package_name or not user_input:
        print_with_color("Error: Package name and user input (task/description) are required.", "red")
        parser.print_help()
        sys.exit(1)

    # ... (VLM initialization code) ...
    model_name = configs["MODEL"]
    if model_name == "OpenAI":
        mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                             api_key=configs["OPENAI_API_KEY"],
                             model=configs["OPENAI_API_MODEL"],
                             temperature=configs["TEMPERATURE"],
                             max_tokens=configs["MAX_TOKENS"])
    elif model_name == "Qwen":
        mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                           model=configs["QWEN_MODEL"])
    elif model_name == "Gemini":
        mllm = GeminiModel(api_key=configs["GEMINI_API_KEY"],
                           model_name=configs["GEMINI_MODEL_NAME"])
    else:
        print_with_color(f"Unsupported model: {model_name}. Check MODEL in config.yaml.", "red")
        sys.exit()


    # --- Directory Setup ---
    # Use app_name_for_output_dir for creating directories
    work_dir = os.path.join(root_dir, "apps")
    # Ensure app_name_for_output_dir is filesystem-safe
    safe_app_name = app_name_for_output_dir.replace('.', '_').replace(':', '_')
    app_dir = os.path.join(work_dir, safe_app_name)
    # ... (rest of directory setup: demo_timestamp, demo_name, task_dir, etc.) ...
    demo_timestamp = int(time.time())
    demo_name_prefix = "task" # Will be updated after input analysis
    # Actual demo_name will be set after input analysis
    # task_dir, screenshot_dir, etc. will be set later

    # --- Connect to Android Device (same as before) ---
    # ... (device connection logic) ...
    device_list = list_all_devices()
    if not device_list: # ... (handle no device)
        sys.exit()
    # ... (select device if multiple)
    device = device_list[0] # Assuming one for simplicity here
    controller = AndroidController(device)
    width, height = controller.width, controller.height
    if width == 0 or height == 0: # Check for valid dimensions
        print_with_color("Could not get device screen dimensions. Exiting.", "red")
        sys.exit(1)
    print_with_color(f"Screen size: {width}x{height}", "green")


    # --- Step 1 (New): Analyze User Input ---
    print_with_color("\n--- Analyzing User Input ---", "blue")
    initial_analysis_prompt = prompts.initial_input_analysis_template.replace("<user_input_text>", user_input)
    # For this initial analysis, no image is typically needed, but your mllm.get_model_response expects it.
    # You might need to adapt mllm or pass a dummy/blank image path if the VLM can handle text-only.
    # For now, let's assume we can pass an empty list of images or the VLM handles it.
    # If an image is *required* by get_model_response, take an initial screenshot.
    initial_screenshot_path = controller.get_screenshot("0_initial_analysis", os.path.join(app_dir, "temp_initial_shots")) # Temp dir
    if initial_screenshot_path == "ERROR":
        print_with_color("Failed to get initial screenshot for analysis. Trying without.", "yellow")
        initial_screenshot_path = [] # Or a path to a blank image
    else:
        initial_screenshot_path = [initial_screenshot_path]


    status_analysis, rsp_analysis = mllm.get_model_response(initial_analysis_prompt, initial_screenshot_path) # Pass empty list if no image
    
    agent_mode = None # "TASK" or "EXPLORATION"
    current_task_description_for_vlm = "" # For task_template or app_exploration_task_template
    app_context_for_exploration = ""
    exploration_goals_queue = [] # For EXPLORATION mode

    if not status_analysis:
        print_with_color(f"VLM call for initial input analysis failed: {rsp_analysis}. Exiting.", "red")
        sys.exit(1)

    input_type, identified_context, initial_goals = parse_initial_input_analysis(rsp_analysis)

    if not input_type:
        print_with_color("Failed to parse initial input analysis from VLM. Exiting.", "red")
        sys.exit(1)

    if input_type == "TASK":
        agent_mode = "TASK"
        current_task_description_for_vlm = identified_context
        print_with_color(f"Mode: TASK. Goal: {current_task_description_for_vlm}", "magenta")
        demo_name_prefix = "task_driven"
    elif input_type == "DESCRIPTION":
        agent_mode = "EXPLORATION"
        app_context_for_exploration = identified_context
        exploration_goals_queue = initial_goals if initial_goals else []
        print_with_color(f"Mode: EXPLORATION. App Context: {app_context_for_exploration}", "magenta")
        if exploration_goals_queue:
            print_with_color(f"Initial exploration goals: {exploration_goals_queue}", "cyan")
        else:
            print_with_color("No specific initial goals from VLM, will explore generally.", "cyan")
        demo_name_prefix = "exploration_driven"
    else:
        print_with_color(f"Unknown input type from VLM: {input_type}. Exiting.", "red")
        sys.exit(1)

    # Now set up the specific demo directories
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"{demo_name_prefix}_%Y-%m-%d_%H-%M-%S")
    task_dir = os.path.join(app_dir, "demos", demo_name)
    screenshot_dir = os.path.join(task_dir, "screenshots")
    xml_dir = os.path.join(task_dir, "xmls")
    log_dir = os.path.join(task_dir, "logs")
    # docs_dir is app-level, not demo-level
    docs_dir = os.path.join(app_dir, "auto_docs")

    os.makedirs(screenshot_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True) # Ensure auto_docs exists at app level

    log_main_path = os.path.join(log_dir, "main_log.txt") # Unified log
    log_reflect_path = os.path.join(log_dir, "reflect_log.txt")


    # --- Step 2 (New): Launch App Directly ---
    print_with_color(f"\n--- Launching App: {package_name} ---", "blue")
    controller.launch_app(package_name)
    time.sleep(configs.get("APP_LAUNCH_WAIT_TIME", 5)) # Wait for app to load

    # --- Main Loop ---
    round_count = 0
    last_act = "App launched." # Initial last_act
    useless_list = []
    doc_count = 0
    task_complete = False
    explored_features_history = [] # For EXPLORATION mode

    while round_count < configs.get("MAX_ROUNDS", 20): # Use .get for MAX_ROUNDS
        round_count += 1
        print_with_color(f"\n--- Round {round_count} ({agent_mode} Mode) ---", "yellow")

        # Get screen state (screenshot, XML, elements) - same as before
        screenshot_before = controller.get_screenshot(f"{round_count}_before", screenshot_dir)
        xml_path = controller.get_xml(f"{round_count}", xml_dir)
        if screenshot_before == "ERROR" or xml_path == "ERROR":
            print_with_color("Failed to get screenshot or XML. Ending current round.", "red")
            time.sleep(configs["REQUEST_INTERVAL"]); continue


        clickable_list = []
        focusable_list = []
        traverse_tree(xml_path, clickable_list, "clickable")
        traverse_tree(xml_path, focusable_list, "focusable")
        elem_list = [e for e in clickable_list + focusable_list if e.uid not in useless_list]
        screenshot_before_labeled_path = os.path.join(screenshot_dir, f"{round_count}_before_labeled.png")
        # Handle case where draw_bbox_multi might return None if img is None
        img_drawn = draw_bbox_multi(screenshot_before, screenshot_before_labeled_path, elem_list, dark_mode=configs.get("DARK_MODE", False))
        if img_drawn is None:
            print_with_color("Failed to label screenshot. Using unlabeled for VLM.", "yellow")
            # If draw_bbox_multi can fail, use original screenshot_before if labeling fails
            # This assumes get_model_response can handle unlabeled images too, or adapt.
            # For now, we proceed, but VLM might be less effective. Consider this path.
            # A simple fix: if labeling fails, just use the original screenshot path.
            # However, the VLM prompt expects labeled elements.
            # A better fix in draw_bbox_multi would be to return the original image path if labeling fails.
            # Or, for now, if labeling fails, we might have to skip the round or error.
            # Let's assume labeling will succeed for now or that the VLM can cope if it's sometimes unlabeled (less ideal).


        # --- Prepare UI Documentation (same as before) ---
        ui_documentation_str = ""
        # ... (code to load documentation for elem_list) ...
        for idx, elem_obj in enumerate(elem_list):
            doc_file_name = f"{elem_obj.uid.replace('/', '_').replace(':', '.')}.txt"
            doc_file_path = os.path.join(docs_dir, doc_file_name)
            if os.path.exists(doc_file_path):
                try:
                    with open(doc_file_path, "r", encoding="utf-8") as f_doc:
                        doc_content = f_doc.read().strip()
                        ui_documentation_str += f"Element {idx + 1} (UID: {elem_obj.uid}): {doc_content}\n"
                except Exception as e:
                    print_with_color(f"Error reading doc file {doc_file_path}: {e}", "red")
        if not ui_documentation_str:
            ui_documentation_str = "No documentation available for elements on this screen."


        # --- VLM Call (Mode Dependent) ---
        prompt = ""
        action_res = None
        chosen_sub_task_for_log = "N/A"

        if agent_mode == "TASK":
            prompt = prompts.task_template.replace("<task_description>", current_task_description_for_vlm)\
                                         .replace("<last_act>", last_act)\
                                         .replace("<ui_document>", ui_documentation_str)
            status, rsp = mllm.get_model_response(prompt, [screenshot_before_labeled_path])
            if not status: # ... (handle VLM failure) ...
                print_with_color(f"VLM call failed for TASK mode: {rsp}. Skipping round.", "red"); time.sleep(configs["REQUEST_INTERVAL"]); continue
            action_res = parse_explore_rsp(rsp) # Use existing parser for task mode

        elif agent_mode == "EXPLORATION":
            # For exploration, we might feed the current goal from exploration_goals_queue
            # or let the VLM decide the next sub-task entirely.
            # The app_exploration_task_template asks VLM to choose a sub-task.
            explored_history_str = "\n".join(f"- {feat}" for feat in explored_features_history) if explored_features_history else "Nothing explored yet."
            prompt = prompts.app_exploration_task_template.replace("<app_context_description>", app_context_for_exploration)\
                                                          .replace("<explored_features_history>", explored_history_str)\
                                                          .replace("<last_act>", last_act)\
                                                          .replace("<ui_document>", ui_documentation_str)
            status, rsp = mllm.get_model_response(prompt, [screenshot_before_labeled_path])
            if not status: # ... (handle VLM failure) ...
                print_with_color(f"VLM call failed for EXPLORATION mode: {rsp}. Skipping round.", "red"); time.sleep(configs["REQUEST_INTERVAL"]); continue
            
            chosen_sub_task, action_list_from_vlm = parse_exploration_step_rsp(rsp)
            if chosen_sub_task and action_list_from_vlm and action_list_from_vlm[0] != "ERROR":
                action_res = action_list_from_vlm # This is [action_name, params..., summary]
                chosen_sub_task_for_log = chosen_sub_task
                if chosen_sub_task not in explored_features_history:
                     explored_features_history.append(chosen_sub_task) # Add to history
            else:
                action_res = ["ERROR", "Failed to parse exploration step or VLM error in action list"]


        # --- Log VLM Interaction ---
        with open(log_main_path, "a", encoding="utf-8") as f:
            f.write(f"--- Round {round_count} ({agent_mode} Mode) ---\n")
            if agent_mode == "EXPLORATION":
                f.write(f"Chosen Sub-Task by VLM: {chosen_sub_task_for_log}\n")
            f.write(f"Prompt:\n{prompt}\nResponse:\n{rsp}\n-----------------------------\n")

        # --- Process Action ---
        if not action_res or action_res[0] == "ERROR":
            print_with_color(f"Failed to parse VLM response or VLM returned error. Details: {action_res[1] if len(action_res) > 1 else 'No details'}", "red")
            last_act = "Error in parsing VLM response or VLM error."
            time.sleep(configs["REQUEST_INTERVAL"]); continue
        
        act_name = action_res[0]
        # Update last_act (summary from VLM)
        if len(action_res) > 1 and act_name not in ["FINISH", "grid"]:
             last_act = action_res[-1]
        elif act_name == "FINISH":
            last_act = "Task/Exploration finished by VLM."
            task_complete = True # Set task_complete for both modes if VLM says FINISH
        # ... (handle other simple action summaries if needed) ...

        if task_complete: # If FINISH action was chosen
            print_with_color(f"VLM chose FINISH. Ending {agent_mode} mode.", "green")
            break
        
        # --- Execute Action (same core logic as before) ---
        interacted_element_uid = ""
        elem_idx_for_reflect = -1 # For reflection prompt, element index if applicable
        # Example for tap, ensure others are similar:
        if act_name == "tap":
            if len(action_res) < 2:
                print_with_color(f"Error: 'tap' action missing element index parameter.", "red")
                last_act += " (Missing tap parameter)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
            try:
                elem_idx_for_reflect = int(action_res[1])
                if 1 <= elem_idx_for_reflect <= len(elem_list):
                    target_element = elem_list[elem_idx_for_reflect - 1]
                    x = (target_element.bbox[0][0] + target_element.bbox[1][0]) // 2
                    y = (target_element.bbox[0][1] + target_element.bbox[1][1]) // 2
                    print_with_color(f"Executing tap on element {elem_idx_for_reflect} (UID: {target_element.uid}) at ({x},{y})", "blue")
                    controller.tap(x, y)
                    interacted_element_uid = target_element.uid
                else:
                    print_with_color(f"Invalid element index for tap: {elem_idx_for_reflect}. Max elements: {len(elem_list)}", "red")
                    last_act += " (Invalid tap index)"
                    time.sleep(configs["REQUEST_INTERVAL"]); continue
            except ValueError:
                print_with_color(f"Error: Invalid element index for tap (not an int): {action_res[1]}", "red")
                last_act += " (Invalid tap parameter type)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue

        elif act_name == "type_global":
            if len(action_res) < 2:
                print_with_color(f"Error: 'type_global' action missing text parameter.", "red")
                last_act += " (Missing type_global parameter)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
            text_to_type = str(action_res[1])
            print_with_color(f"Executing type_global with text: '{text_to_type}'", "blue")
            controller.text(text_to_type)
            # interacted_element_uid and elem_idx_for_reflect remain "" and -1

        elif act_name == "long_press":
            if len(action_res) < 2:
                print_with_color(f"Error: 'long_press' action missing element index parameter.", "red")
                last_act += " (Missing long_press parameter)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
            try:
                elem_idx_for_reflect = int(action_res[1])
                if 1 <= elem_idx_for_reflect <= len(elem_list):
                    target_element = elem_list[elem_idx_for_reflect - 1]
                    x = (target_element.bbox[0][0] + target_element.bbox[1][0]) // 2
                    y = (target_element.bbox[0][1] + target_element.bbox[1][1]) // 2
                    print_with_color(f"Executing long_press on element {elem_idx_for_reflect} (UID: {target_element.uid}) at ({x},{y})", "blue")
                    controller.long_press(x, y) # Assuming default duration from controller
                    interacted_element_uid = target_element.uid
                else:
                    print_with_color(f"Invalid element index for long_press: {elem_idx_for_reflect}. Max elements: {len(elem_list)}", "red")
                    last_act += " (Invalid long_press index)"
                    time.sleep(configs["REQUEST_INTERVAL"]); continue
            except ValueError:
                print_with_color(f"Error: Invalid element index for long_press (not an int): {action_res[1]}", "red")
                last_act += " (Invalid long_press parameter type)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
        
        elif act_name == "swipe_element":
            if len(action_res) < 4: # Expecting act_name, elem_idx, direction, distance, summary
                print_with_color(f"Error: 'swipe_element' action missing parameters.", "red")
                last_act += " (Missing swipe_element parameters)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
            try:
                elem_idx_for_reflect = int(action_res[1])
                direction = str(action_res[2]).lower()
                distance_str = str(action_res[3]).lower()
                if 1 <= elem_idx_for_reflect <= len(elem_list):
                    target_element = elem_list[elem_idx_for_reflect - 1]
                    x = (target_element.bbox[0][0] + target_element.bbox[1][0]) // 2
                    y = (target_element.bbox[0][1] + target_element.bbox[1][1]) // 2
                    print_with_color(f"Executing swipe_element on element {elem_idx_for_reflect} (UID: {target_element.uid}) at ({x},{y}), dir: {direction}, dist: {distance_str}", "blue")
                    controller.swipe_element(x, y, direction, distance_str)
                    interacted_element_uid = target_element.uid
                else:
                    print_with_color(f"Invalid element index for swipe_element: {elem_idx_for_reflect}. Max: {len(elem_list)}", "red")
                    last_act += " (Invalid swipe_element index)"
                    time.sleep(configs["REQUEST_INTERVAL"]); continue
            except ValueError:
                print_with_color(f"Error: Invalid element index for swipe_element (not an int): {action_res[1]}", "red")
                last_act += " (Invalid swipe_element parameter type)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
            except IndexError:
                 print_with_color(f"Error: Not enough parameters for swipe_element in action_res: {action_res}", "red")
                 last_act += " (Malformed swipe_element parameters)"
                 time.sleep(configs["REQUEST_INTERVAL"]); continue


        elif act_name == "swipe_screen":
            if len(action_res) < 3: # Expecting act_name, direction, distance, summary
                print_with_color(f"Error: 'swipe_screen' action missing parameters.", "red")
                last_act += " (Missing swipe_screen parameters)"
                time.sleep(configs["REQUEST_INTERVAL"]); continue
            try:
                direction = str(action_res[1]).lower()
                distance_str = str(action_res[2]).lower()
                dist_map = {"short": 0.25, "medium": 0.5, "long": 0.75}
                distance_factor = dist_map.get(distance_str, 0.5) # Default to medium
                print_with_color(f"Executing swipe_screen, dir: {direction}, dist_factor: {distance_factor}", "blue")
                controller.swipe_screen_direction(direction, distance_factor)
            except IndexError:
                 print_with_color(f"Error: Not enough parameters for swipe_screen in action_res: {action_res}", "red")
                 last_act += " (Malformed swipe_screen parameters)"
                 time.sleep(configs["REQUEST_INTERVAL"]); continue


        elif act_name == "press_back":
            print_with_color("Executing press_back", "blue")
            controller.back()
        elif act_name == "press_home":
            print_with_color("Executing press_home", "blue")
            controller.press_home()
        elif act_name == "press_enter":
            print_with_color("Executing press_enter", "blue")
            controller.press_enter()
        elif act_name == "press_delete":
            print_with_color("Executing press_delete", "blue")
            controller.press_delete()
        elif act_name == "open_notifications":
            print_with_color("Executing open_notifications", "blue")
            controller.open_notifications()
        elif act_name == "press_app_switch":
            print_with_color("Executing press_app_switch", "blue")
            controller.press_app_switch()
        elif act_name == "grid":
            print_with_color("GRID action called by VLM. No controller action taken in this loop. VLM should use grid functions next.", "magenta")
            # No specific controller action for "grid" itself, it's a mode switch for the VLM.
            # We might want to skip reflection for "grid" or handle it specially.
        else:
            print_with_color(f"Unknown action to execute: {act_name}", "red")
            last_act += f" (Unknown action: {act_name})"
            time.sleep(configs["REQUEST_INTERVAL"]); continue

        time.sleep(configs["REQUEST_INTERVAL"]) # Wait for action to complete on device

        # --- Reflection ---
        task_context_for_reflection = ""
        if agent_mode == "TASK":
            task_context_for_reflection = current_task_description_for_vlm
        elif agent_mode == "EXPLORATION":
            task_context_for_reflection = f"Exploration of '{app_context_for_exploration}', current sub-task: '{chosen_sub_task_for_log}'"
        
        element_details_for_reflection = "N/A"
        # Build element_details_for_reflection based on if an element was targeted
        if elem_idx_for_reflect != -1 and interacted_element_uid: # Check if an element was indeed interacted with
             element_details_for_reflection = f"Element {elem_idx_for_reflect} (UID: {interacted_element_uid})"
        elif act_name == "type_global":
            element_details_for_reflection = "Text input via type_global (no specific target element ID)"
        elif act_name in ["swipe_screen", "press_back", "press_home", "press_enter", "press_delete", "open_notifications", "press_app_switch"]:
            element_details_for_reflection = f"Global action ({act_name}) performed"
        # else: element_details_for_reflection remains "N/A" for actions like "grid" or if no element was targeted

        # Only proceed with reflection if an action was taken that warrants it
        if act_name not in ["grid", "FINISH"]: # GRID action doesn't change state for reflection in the same way
            screenshot_after = controller.get_screenshot(f"{round_count}_after", screenshot_dir)
            if screenshot_after == "ERROR":
                print_with_color("Failed to get screenshot after action. Skipping reflection for this round.", "red")
            else:
                xml_after_path = controller.get_xml(f"{round_count}_after_xml", xml_dir)
                elem_list_after = []
                if xml_after_path != "ERROR":
                    clickable_list_after_reflect = [] # Use different names to avoid confusion
                    focusable_list_after_reflect = []
                    traverse_tree(xml_after_path, clickable_list_after_reflect, "clickable")
                    traverse_tree(xml_after_path, focusable_list_after_reflect, "focusable")
                    elem_list_after = clickable_list_after_reflect + focusable_list_after_reflect
                
                screenshot_after_labeled_path = os.path.join(screenshot_dir, f"{round_count}_after_labeled.png")
                img_drawn_after = draw_bbox_multi(screenshot_after, screenshot_after_labeled_path, elem_list_after, dark_mode=configs.get("DARK_MODE", False))
                if img_drawn_after is None:
                    print_with_color("Failed to label screenshot_after. Reflection might be impaired.", "yellow")
                    # Potentially use unlabeled screenshot_after if labeling fails
                    # screenshot_after_labeled_path = screenshot_after # if VLM can handle unlabeled

                reflect_prompt = prompts.self_explore_reflect_template \
                                    .replace("<task_desc>", task_context_for_reflection) \
                                    .replace("<action_type>", act_name) \
                                    .replace("<element_details>", element_details_for_reflection) \
                                    .replace("<last_act_summary>", last_act) # 'last_act' is the VLM's summary of its own chosen action
                
                # Ensure paths for VLM are valid, even if labeling failed
                images_for_reflection = []
                if os.path.exists(screenshot_before_labeled_path): images_for_reflection.append(screenshot_before_labeled_path)
                else: images_for_reflection.append(screenshot_before) # Fallback to unlabeled if labeled doesn't exist

                if os.path.exists(screenshot_after_labeled_path): images_for_reflection.append(screenshot_after_labeled_path)
                elif screenshot_after != "ERROR": images_for_reflection.append(screenshot_after) # Fallback

                if not images_for_reflection or len(images_for_reflection) < 2 : # Ensure we have images
                    print_with_color("Not enough valid images for reflection. Skipping reflection.", "red")
                else:
                    status_reflect, rsp_reflect = mllm.get_model_response(reflect_prompt, images_for_reflection)
                    
                    with open(log_reflect_path, "a", encoding="utf-8") as f:
                        f.write(f"--- Round {round_count} Reflect Phase ---\n")
                        f.write(f"Action Taken: {act_name}, Element Details: {element_details_for_reflection}\n")
                        f.write(f"Prompt:\n{reflect_prompt}\nResponse:\n{rsp_reflect}\n-----------------------------\n")
                    
                    if not status_reflect:
                        print_with_color(f"VLM call for reflection failed: {rsp_reflect}.", "red")
                    else:
                        reflect_res = parse_reflect_rsp(rsp_reflect)
                        if reflect_res and reflect_res[0] != "ERROR":
                            decision = reflect_res[0]
                            # thought_reflect = reflect_res[1] # If needed
                            documentation_text = reflect_res[2] 

                            if decision == "INEFFECTIVE" or decision == "BACK" or decision == "CONTINUE":
                                if interacted_element_uid and interacted_element_uid not in useless_list:
                                    useless_list.append(interacted_element_uid)
                                    print_with_color(f"Element UID {interacted_element_uid} added to useless_list due to reflection: {decision}", "yellow")
                                if decision == "BACK":
                                    print_with_color("Reflection decision: BACK. Executing controller.back()", "yellow")
                                    controller.back()
                                    time.sleep(configs["REQUEST_INTERVAL"]) # Allow time for back action
                            
                            if documentation_text and documentation_text.lower() != "n/a" and decision != "INEFFECTIVE" and interacted_element_uid : # Only save doc if element was targeted and action wasn't useless
                                doc_filename = f"{interacted_element_uid.replace('/', '_').replace(':', '.')}.txt"
                                doc_path = os.path.join(docs_dir, doc_filename)
                                
                                final_documentation_to_write = documentation_text
                                if os.path.exists(doc_path) and configs.get("DOC_REFINE", False):
                                    try:
                                        with open(doc_path, "r", encoding="utf-8") as f_doc:
                                            existing_doc = f_doc.read()
                                        final_documentation_to_write = f"{existing_doc}\n---\nRefined ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n{documentation_text}"
                                        print_with_color(f"Refining documentation for {interacted_element_uid}", "cyan")
                                    except Exception as e:
                                        print_with_color(f"Error reading existing doc for refinement: {e}", "red")
                                else:
                                    print_with_color(f"Generating new documentation for {interacted_element_uid}", "cyan")
                                
                                try:
                                    with open(doc_path, "w", encoding="utf-8") as f_doc:
                                        f_doc.write(final_documentation_to_write)
                                    doc_count +=1
                                    print_with_color(f"Documentation generated/updated for element {interacted_element_uid}", "magenta")
                                except Exception as e:
                                    print_with_color(f"Error writing doc file {doc_path}: {e}", "red")
                        else:
                            print_with_color("Failed to parse reflection response.", "red")

        time.sleep(configs["REQUEST_INTERVAL"]) # End of round wait

    # --- End of Loop ---
    if task_complete:
        print_with_color(f"Agent finished: {agent_mode} completed.", "green")
    else:
        print_with_color(f"Max rounds ({configs.get('MAX_ROUNDS', 20)}) reached. {agent_mode} may not be complete.", "yellow")
    print_with_color(f"Total documentations generated/updated: {doc_count}", "blue")


if __name__ == "__main__":
    # This allows running self_explorer.py directly with CLI args for testing
    # The main() function is now designed to also be callable from other scripts
    # by passing arguments directly.
    main() # It will use argparse if package_name_arg and user_input_arg are None