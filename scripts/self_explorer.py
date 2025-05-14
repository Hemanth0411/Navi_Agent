import argparse
import ast
import datetime
import json
import os
import re
import sys
import time
import warnings # Import warnings module

# Suppress all warnings
warnings.filterwarnings("ignore")

# Relative imports for modules within the same package (scripts)
from . import prompts
from .config import load_config
from .and_controller import list_all_devices, AndroidController, traverse_tree
from .model import parse_explore_rsp, parse_reflect_rsp, OpenAIModel, QwenModel, GeminiModel  # Added GeminiModel import
from .utils import draw_bbox_multi, print_with_color

configs = load_config()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app")
    parser.add_argument("--root_dir", default="./")
    args = vars(parser.parse_args())

    app_name = args["app"]
    root_dir = args["root_dir"]

    # Initialize VLM
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

    if not app_name:
        print_with_color("What is the name of the target app?", "blue")
        app_name = input()
        app_name = app_name.replace(" ", "")

    work_dir = os.path.join(root_dir, "apps")
    app_dir = os.path.join(work_dir, app_name)
    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime("self_explore_%Y-%m-%d_%H-%M-%S")
    task_dir = os.path.join(app_dir, "demos", demo_name)
    screenshot_dir = os.path.join(task_dir, "screenshots")
    xml_dir = os.path.join(task_dir, "xmls")
    log_dir = os.path.join(task_dir, "logs")
    docs_dir = os.path.join(app_dir, "auto_docs") 

    os.makedirs(screenshot_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)

    log_explore_path = os.path.join(log_dir, "explore_log.txt")
    log_reflect_path = os.path.join(log_dir, "reflect_log.txt")

    # Connect to Android device
    device_list = list_all_devices()
    if not device_list:
        print_with_color("No device found. Please connect your Android device and enable USB debugging.", "red")
        sys.exit()
    if len(device_list) == 1:
        device = device_list[0]
        print_with_color(f"Device connected: {device}", "green")
    else:
        print_with_color("Multiple devices found. Please select one:", "blue")
        for i, dev in enumerate(device_list):
            print_with_color(f"{i + 1}. {dev}", "blue")
        while True:
            try:
                choice = int(input("Enter the number of the device: "))
                if 1 <= choice <= len(device_list):
                    device = device_list[choice - 1]
                    break
                else:
                    print_with_color("Invalid choice.", "red")
            except ValueError:
                print_with_color("Invalid input. Please enter a number.", "red")
    controller = AndroidController(device)
    width, height = controller.width, controller.height
    print_with_color(f"Screen size: {width}x{height}", "green")

    print_with_color("Please enter the description of the task you want the agent to complete: ", "blue")
    task_desc = input()
    round_count = 0
    last_act = "None"
    useless_list = [] 
    doc_count = 0
    task_complete = False

    while round_count < configs["MAX_ROUNDS"]:
        round_count += 1
        print_with_color(f"Round {round_count}", "yellow")
        screenshot_before = controller.get_screenshot(f"{round_count}_before", screenshot_dir)
        xml_path = controller.get_xml(f"{round_count}", xml_dir)
        if screenshot_before == "ERROR" or xml_path == "ERROR":
            print_with_color("Failed to get screenshot or XML. Exiting.", "red")
            break

        clickable_list = []
        focusable_list = []
        traverse_tree(xml_path, clickable_list, "clickable")
        traverse_tree(xml_path, focusable_list, "focusable")
        
        elem_list = [e for e in clickable_list + focusable_list if e.uid not in useless_list]

        screenshot_before_labeled_path = os.path.join(screenshot_dir, f"{round_count}_before_labeled.png")
        # Pass elem_list to draw_bbox_multi, it will use the index + 1 as the label
        draw_bbox_multi(screenshot_before, screenshot_before_labeled_path, elem_list, dark_mode=configs["DARK_MODE"])

        # --- Prepare UI Documentation ---
        ui_documentation_str = ""
        # elem_list contains AndroidElement objects. The label given by draw_bbox_multi is index + 1
        for idx, elem_obj in enumerate(elem_list):
            doc_file_name = f"{elem_obj.uid.replace('/', '_').replace(':', '.')}.txt"
            doc_file_path = os.path.join(docs_dir, doc_file_name)
            if os.path.exists(doc_file_path):
                try:
                    with open(doc_file_path, "r", encoding="utf-8") as f_doc:
                        doc_content = f_doc.read().strip()
                        # Label in prompt is index + 1
                        ui_documentation_str += f"Element {idx + 1} (UID: {elem_obj.uid}): {doc_content}\n"
                except Exception as e:
                    print_with_color(f"Error reading doc file {doc_file_path}: {e}", "red")
        
        if not ui_documentation_str:
            ui_documentation_str = "No documentation available for elements on this screen."
        # --- End Prepare UI Documentation ---

        prompt = prompts.task_template.replace("<task_description>", task_desc)\
                                                 .replace("<last_act>", last_act)\
                                                 .replace("<ui_document>", ui_documentation_str) # Inject documentation
        
        status, rsp = mllm.get_model_response(prompt, [screenshot_before_labeled_path])
        with open(log_explore_path, "a", encoding="utf-8") as f:
            f.write(f"Round {round_count} Explore Phase:\nPrompt: {prompt}\nResponse: {rsp}\n-----------------------------\n")
        
        if not status:
            print_with_color(f"VLM call failed: {rsp}. Exiting.", "red")
            break

        action_res = parse_explore_rsp(rsp)
        if not action_res or action_res[0] == "ERROR":
            print_with_color("Failed to parse VLM response for exploration. Trying again or exiting.", "red")
            last_act = "Error in parsing VLM response."
            time.sleep(configs["REQUEST_INTERVAL"])
            continue 
        
        act_name = action_res[0]
        # Summary from VLM is the last element if action_res is not ["FINISH"] or ["grid"]
        if len(action_res) > 1 and act_name not in ["FINISH", "grid"]: 
            last_act = action_res[-1] 
        elif act_name == "FINISH":
            last_act = "Task finished."
        elif act_name == "grid":
            last_act = "Switched to grid mode." # Or whatever summary is appropriate
        else: # Should not happen if parse_explore_rsp is correct
            last_act = f"Executed {act_name}"


        if act_name == "FINISH":
            print_with_color("Task marked as FINISH by VLM.", "green")
            task_complete = True
            break
        
        interacted_element_uid = ""
        elem_idx = -1 # For reflection prompt

        if act_name == "tap":
            elem_idx = action_res[1]
            if 1 <= elem_idx <= len(elem_list):
                x, y = (elem_list[elem_idx-1].bbox[0][0] + elem_list[elem_idx-1].bbox[1][0]) // 2, \
                       (elem_list[elem_idx-1].bbox[0][1] + elem_list[elem_idx-1].bbox[1][1]) // 2
                controller.tap(x, y)
                interacted_element_uid = elem_list[elem_idx-1].uid
            else:
                print_with_color(f"Invalid element index for tap: {elem_idx}", "red")
                last_act += " (Invalid tap index)"; time.sleep(configs["REQUEST_INTERVAL"]); continue
        
        elif act_name == "type_global": # Updated from "type_text"
            controller.text(action_res[1]) 
            # For type_global, elem_idx remains -1 (or N/A), interacted_element_uid is empty.
            # Reflection will adapt.
        
        elif act_name == "long_press":
            elem_idx = action_res[1]
            if 1 <= elem_idx <= len(elem_list):
                x, y = (elem_list[elem_idx-1].bbox[0][0] + elem_list[elem_idx-1].bbox[1][0]) // 2, \
                       (elem_list[elem_idx-1].bbox[0][1] + elem_list[elem_idx-1].bbox[1][1]) // 2
                controller.long_press(x,y)
                interacted_element_uid = elem_list[elem_idx-1].uid
            else:
                print_with_color(f"Invalid element index for long_press: {elem_idx}", "red")
                last_act += " (Invalid long_press index)"; time.sleep(configs["REQUEST_INTERVAL"]); continue
        
        elif act_name == "swipe_element": 
            elem_idx, direction, distance = action_res[1], action_res[2], action_res[3]
            if 1 <= elem_idx <= len(elem_list):
                x, y = (elem_list[elem_idx-1].bbox[0][0] + elem_list[elem_idx-1].bbox[1][0]) // 2, \
                       (elem_list[elem_idx-1].bbox[0][1] + elem_list[elem_idx-1].bbox[1][1]) // 2
                controller.swipe_element(x, y, direction, distance) 
                interacted_element_uid = elem_list[elem_idx-1].uid
            else:
                print_with_color(f"Invalid element index for swipe_element: {elem_idx}", "red")
                last_act += " (Invalid swipe_element index)"; time.sleep(configs["REQUEST_INTERVAL"]); continue
        
        elif act_name == "swipe_screen":
            direction, distance_str = action_res[1], action_res[2]
            dist_map = {"short": 0.25, "medium": 0.5, "long": 0.75} # Factors for swipe_screen_direction
            distance_factor = dist_map.get(distance_str.lower(), 0.5) 
            controller.swipe_screen_direction(direction, distance_factor)

        elif act_name == "press_home":
            controller.press_home()
        elif act_name == "press_enter":
            controller.press_enter()
        elif act_name == "press_delete":
            controller.press_delete()
        elif act_name == "open_notifications":
            controller.open_notifications()
        elif act_name == "press_app_switch": # Added
            controller.press_app_switch()
        elif act_name == "press_back":
            controller.back()
        # GRID action is simple, no specific execution here beyond what parse_explore_rsp returns
        elif act_name == "grid":
            print_with_color("GRID action called. Implement grid mode logic if needed.", "magenta")
            # For now, assume it means re-evaluating screen or VLM will use grid functions next
            # No controller action, just influences next prompt or VLM state.
            # If it implies specific state change in self_explorer.py, add here.

        else:
            print_with_color(f"Unknown action to execute: {act_name}", "red")
            last_act += f" (Unknown action: {act_name})"
            time.sleep(configs["REQUEST_INTERVAL"]); continue

        time.sleep(configs["REQUEST_INTERVAL"]) 

        screenshot_after_labeled_path = ""
        
        element_details_for_reflection = "N/A"
        if elem_idx != -1 and interacted_element_uid: # Element-specific action
            element_details_for_reflection = f"Element {elem_idx} (UID: {interacted_element_uid})"
        elif act_name == "type_global":
            element_details_for_reflection = "Text input via type_global"
        else: # Global action
            element_details_for_reflection = f"Global action ({act_name})"


        # Reflection logic
        # For key presses, type_global, swipe_screen, the after screenshot is still useful for reflection
        if act_name not in ["grid"]: # Grid might not need immediate reflection or follows a different flow
            screenshot_after = controller.get_screenshot(f"{round_count}_after", screenshot_dir)
            if screenshot_after == "ERROR":
                print_with_color("Failed to get screenshot after action. Skipping reflection.", "red")
            else:
                xml_after_path = controller.get_xml(f"{round_count}_after_xml", xml_dir)
                elem_list_after = [] # Initialize to avoid UnboundLocalError if XML fails
                if xml_after_path != "ERROR":
                    clickable_list_after = []
                    focusable_list_after = []
                    traverse_tree(xml_after_path, clickable_list_after, "clickable")
                    traverse_tree(xml_after_path, focusable_list_after, "focusable")
                    elem_list_after = clickable_list_after + focusable_list_after
                
                screenshot_after_labeled_path = os.path.join(screenshot_dir, f"{round_count}_after_labeled.png")
                draw_bbox_multi(screenshot_after, screenshot_after_labeled_path, elem_list_after, dark_mode=configs["DARK_MODE"])

                reflect_prompt = prompts.self_explore_reflect_template \
                                    .replace("<task_desc>", task_desc) \
                                    .replace("<action_type>", act_name) \
                                    .replace("<element_details>", element_details_for_reflection) \
                                    .replace("<last_act_summary>", last_act) # Use the VLM's summary of its own action
                
                status_reflect, rsp_reflect = mllm.get_model_response(reflect_prompt, 
                                                                        [screenshot_before_labeled_path, screenshot_after_labeled_path])
                with open(log_reflect_path, "a", encoding="utf-8") as f:
                    f.write(f"Round {round_count} Reflect Phase:\nPrompt: {reflect_prompt}\nResponse: {rsp_reflect}\n-----------------------------\n")
                
                if not status_reflect:
                    print_with_color(f"VLM call for reflection failed: {rsp_reflect}.", "red")
                else:
                    reflect_res = parse_reflect_rsp(rsp_reflect)
                    if reflect_res and reflect_res[0] != "ERROR":
                        decision = reflect_res[0]
                        # thought_reflect = reflect_res[1] # If needed
                        documentation = reflect_res[2] 

                        if decision == "INEFFECTIVE" or decision == "BACK" or decision == "CONTINUE":
                            # Only add to useless_list if an element was directly interacted with and deemed problematic
                            if interacted_element_uid and interacted_element_uid not in useless_list:
                                useless_list.append(interacted_element_uid)
                            if decision == "BACK":
                                controller.back()
                                time.sleep(configs["REQUEST_INTERVAL"]) # Allow time for back action
                        
                        if documentation and documentation.lower() != "n/a" and decision != "INEFFECTIVE" and interacted_element_uid:
                            doc_path = os.path.join(docs_dir, f"{interacted_element_uid.replace('/', '_').replace(':', '.')}.txt")
                            
                            if os.path.exists(doc_path) and configs.get("DOC_REFINE", False): # Check DOC_REFINE in config
                                try:
                                    with open(doc_path, "r", encoding="utf-8") as f_doc:
                                        existing_doc = f_doc.read()
                                    # Simple refinement: append new doc, or could be more sophisticated
                                    final_documentation = f"{existing_doc}\n---\nRefined ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n{documentation}"
                                    print_with_color(f"Refining documentation for {interacted_element_uid}", "cyan")
                                except Exception as e:
                                    print_with_color(f"Error reading existing doc for refinement: {e}", "red")
                                    final_documentation = documentation # Fallback to new doc
                            else:
                                final_documentation = documentation
                            
                            try:
                                with open(doc_path, "w", encoding="utf-8") as f_doc:
                                    f_doc.write(final_documentation)
                                doc_count +=1
                                print_with_color(f"Documentation generated/updated for element {interacted_element_uid}: {final_documentation}", "magenta")
                            except Exception as e:
                                print_with_color(f"Error writing doc file {doc_path}: {e}", "red")
                    else:
                        print_with_color("Failed to parse reflection response.", "red")
        
        if act_name != "press_back" or decision != "BACK": # Avoid double sleep if back was pressed by reflection
             time.sleep(configs["REQUEST_INTERVAL"])


    if task_complete:
        print_with_color("Task completed successfully!", "green")
    else:
        print_with_color(f"Max rounds ({configs['MAX_ROUNDS']}) reached. Task may not be complete.", "yellow")
    print_with_color(f"Total documentations generated/updated: {doc_count}", "blue")

if __name__ == "__main__":
    main()
