import argparse
import ast
import datetime
import json
import os
import re
import sys
import time
import warnings # Import warnings module
from typing import List, Dict, Set, Optional

# Suppress all warnings
warnings.filterwarnings("ignore")

# Relative imports for modules within the same package (scripts)
from . import prompts
from .config import load_config
from .and_controller import list_all_devices, AndroidController, traverse_tree, launch_app_by_package
from .model import parse_explore_rsp, parse_reflect_rsp, OpenAIModel, QwenModel, GeminiModel # Added GeminiModel import
from .utils import print_with_color, draw_bbox_multi

configs = load_config()

class SelfExplorer:
    def __init__(self, app: str, root_dir: str):
        """Initialize the SelfExplorer with app name and root directory."""
        self.app = app
        self.root_dir = root_dir
        self.last_state = None
        self.last_actions = []
        
        # Initialize directories
        self.work_dir = os.path.join(root_dir, "apps")
        self.app_dir = os.path.join(self.work_dir, app)
        self.demo_timestamp = int(time.time())
        self.demo_name = datetime.datetime.fromtimestamp(self.demo_timestamp).strftime("self_explore_%Y-%m-%d_%H-%M-%S")
        self.task_dir = os.path.join(self.app_dir, "demos", self.demo_name)
        self.screenshot_dir = os.path.join(self.task_dir, "screenshots")
        self.xml_dir = os.path.join(self.task_dir, "xmls")
        self.log_dir = os.path.join(self.task_dir, "logs")
        self.docs_dir = os.path.join(self.app_dir, "auto_docs")
        
        # Create directories
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.xml_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.docs_dir, exist_ok=True)
        
        # Initialize logs
        self.log_explore_path = os.path.join(self.log_dir, "explore_log.txt")
        self.log_reflect_path = os.path.join(self.log_dir, "reflect_log.txt")
        
        # Initialize Android controller
        device_list = list_all_devices()
        if not device_list:
            raise Exception("No device found. Please connect your Android device and enable USB debugging.")
        if len(device_list) == 1:
            self.device = device_list[0]
            print_with_color(f"Device connected: {self.device}", "green")
        else:
            print_with_color("Multiple devices found. Please select one:", "blue")
            for i, dev in enumerate(device_list):
                print_with_color(f"{i + 1}. {dev}", "blue")
            while True:
                try:
                    choice = int(input("Enter the number of the device: "))
                    if 1 <= choice <= len(device_list):
                        self.device = device_list[choice - 1]
                        break
                    else:
                        print_with_color("Invalid choice.", "red")
                except ValueError:
                    print_with_color("Invalid input. Please enter a number.", "red")
        
        self.controller = AndroidController(self.device)
        self.width, self.height = self.controller.width, self.controller.height
        print_with_color(f"Screen size: {self.width}x{self.height}", "green")
        
        # Initialize VLM
        model_name = configs["MODEL"]
        if model_name == "OpenAI":
            self.mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                                  api_key=configs["OPENAI_API_KEY"],
                                  model=configs["OPENAI_API_MODEL"],
                                  temperature=configs["TEMPERATURE"],
                                  max_tokens=configs["MAX_TOKENS"])
        elif model_name == "Qwen":
            self.mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                                model=configs["QWEN_MODEL"])
        elif model_name == "Gemini":
            self.mllm = GeminiModel(api_key=configs["GEMINI_API_KEY"],
                                  model_name=configs["GEMINI_MODEL_NAME"])
        else:
            raise Exception(f"Unsupported model: {model_name}. Check MODEL in config.yaml.")
    
    def get_current_state(self) -> Dict:
        """Get the current state of the app screen."""
        screenshot_path = self.controller.get_screenshot("current", self.screenshot_dir)
        xml_path = self.controller.get_xml("current", self.xml_dir)
        
        if screenshot_path == "ERROR" or xml_path == "ERROR":
            raise Exception("Failed to get screenshot or XML")
        
        # Get clickable and focusable elements
        clickable_list = []
        focusable_list = []
        traverse_tree(xml_path, clickable_list, "clickable")
        traverse_tree(xml_path, focusable_list, "focusable")
        
        # Create labeled screenshot
        screenshot_labeled_path = os.path.join(self.screenshot_dir, "current_labeled.png")
        draw_bbox_multi(screenshot_path, screenshot_labeled_path, clickable_list + focusable_list, dark_mode=configs["DARK_MODE"])
        
        return {
            "screenshot": screenshot_path,
            "xml": xml_path,
            "clickable_elements": clickable_list,
            "focusable_elements": focusable_list,
            "labeled_screenshot": screenshot_labeled_path
        }
    
    def execute_action(self, action: str) -> bool:
        """Execute the given action and return success status."""
        try:
            # Parse the action string
            action_parts = action.split()
            if not action_parts:
                print_with_color("Empty action received", "red")
                return False
                
            action_type = action_parts[0].lower()
            
            # Validate action type
            valid_actions = ["tap", "swipe", "back", "home", "wait"]
            if action_type not in valid_actions:
                print_with_color(f"Invalid action type: {action_type}. Valid actions are: {', '.join(valid_actions)}", "red")
                return False
            
            # Execute the action with proper validation
            if action_type == "tap":
                if len(action_parts) != 3:
                    print_with_color("Invalid tap action format. Expected: tap <x> <y>", "red")
                    return False
                try:
                    x, y = int(action_parts[1]), int(action_parts[2])
                    # Validate coordinates
                    if not (0 <= x <= self.width and 0 <= y <= self.height):
                        print_with_color(f"Invalid coordinates: ({x}, {y}). Screen size: {self.width}x{self.height}", "red")
                        return False
                    ret = self.controller.tap(x, y)
                    if ret == "ERROR":
                        print_with_color("ERROR: tap execution failed", "red")
                        return False
                except ValueError:
                    print_with_color("Invalid coordinate values. Expected integers.", "red")
                    return False
                    
            elif action_type == "swipe":
                if len(action_parts) != 5:
                    print_with_color("Invalid swipe action format. Expected: swipe <start_x> <start_y> <end_x> <end_y>", "red")
                    return False
                try:
                    start_x, start_y = int(action_parts[1]), int(action_parts[2])
                    end_x, end_y = int(action_parts[3]), int(action_parts[4])
                    # Validate coordinates
                    if not (0 <= start_x <= self.width and 0 <= start_y <= self.height and 
                           0 <= end_x <= self.width and 0 <= end_y <= self.height):
                        print_with_color(f"Invalid coordinates: ({start_x}, {start_y}) -> ({end_x}, {end_y}). Screen size: {self.width}x{self.height}", "red")
                        return False
                    ret = self.controller.swipe(start_x, start_y, end_x, end_y)
                    if ret == "ERROR":
                        print_with_color("ERROR: swipe execution failed", "red")
                        return False
                except ValueError:
                    print_with_color("Invalid coordinate values. Expected integers.", "red")
                    return False
                    
            elif action_type == "back":
                ret = self.controller.back()
                if ret == "ERROR":
                    print_with_color("ERROR: back execution failed", "red")
                    return False
                    
            elif action_type == "home":
                ret = self.controller.press_home()
                if ret == "ERROR":
                    print_with_color("ERROR: home execution failed", "red")
                    return False
                    
            elif action_type == "wait":
                if len(action_parts) != 2:
                    print_with_color("Invalid wait action format. Expected: wait <seconds>", "red")
                    return False
                try:
                    seconds = int(action_parts[1])
                    if seconds <= 0:
                        print_with_color("Invalid wait duration. Expected positive integer.", "red")
                        return False
                    print_with_color(f"Waiting for {seconds} seconds...", "yellow")
                    time.sleep(seconds)
                    return True
                except ValueError:
                    print_with_color("Invalid wait duration. Expected integer.", "red")
                    return False
            
            # Record the action only if execution was successful
            self.last_actions.append(action)
            return True
            
        except Exception as e:
            print_with_color(f"Error executing action: {e}", "red")
            return False
    
    def try_alternative_navigation(self):
        """Try alternative navigation methods when stuck."""
        try:
            print_with_color("Attempting to recover from stuck state...", "yellow")
            
            # First try going back
            print_with_color("Trying back navigation...", "yellow")
            ret = self.controller.back()
            if ret == "ERROR":
                print_with_color("Back navigation failed", "red")
            time.sleep(1)
            
            # If that doesn't help, try going home and relaunching
            print_with_color("Trying home navigation...", "yellow")
            ret = self.controller.press_home()
            if ret == "ERROR":
                print_with_color("Home navigation failed", "red")
            time.sleep(1)
            
            # Relaunch the app
            print_with_color("Relaunching app...", "yellow")
            launch_app_by_package(self.package_name)
            time.sleep(2)
            
        except Exception as e:
            print_with_color(f"Error in alternative navigation: {e}", "red")
    
    def explore_unexplored_areas(self):
        """Try to explore unexplored areas of the screen."""
        try:
            # Get current state
            state = self.get_current_state()
            
            # Try swiping in different directions
            directions = [
                (self.width//2, self.height//2, self.width//2, 0),  # Up
                (self.width//2, self.height//2, self.width//2, self.height),  # Down
                (self.width//2, self.height//2, 0, self.height//2),  # Left
                (self.width//2, self.height//2, self.width, self.height//2)   # Right
            ]
            
            for start_x, start_y, end_x, end_y in directions:
                self.controller.swipe(start_x, start_y, end_x, end_y)
                time.sleep(1)
                
                # Check if we found new elements
                new_state = self.get_current_state()
                if new_state != state:
                    return True
            
            return False
            
        except Exception as e:
            print_with_color(f"Error exploring unexplored areas: {e}", "red")
            return False

    def analyze_screen_features(self, screen_state: Dict, app_description: str) -> List[str]:
        """Analyze current screen and identify visible features."""
        features = []
        try:
            # Use the screen analysis prompt
            prompt = prompts.screen_analysis_prompt.format(
                screen_state=screen_state,
                description=app_description
            )
            response = self.mllm.generate_content(prompt)
            features = [f.strip() for f in response.text.split('\n') if f.strip()]
            
            # Check if this is a main screen
            if features and "main screen" in response.text.lower():
                print_with_color("Analyzing main screen for core features", "blue")
                
        except Exception as e:
            print_with_color(f"Error analyzing screen: {e}", "red")
        return features

    def decide_next_action(
        self,
        current_state: Dict,
        remaining_features: Set[str],
        app_description: str,
        last_actions: List[str]
    ) -> Optional[str]:
        """Decide the next action based on current state and remaining features."""
        try:
            # Use the decision making prompt
            prompt = prompts.decision_making_prompt.format(
                current_state=current_state,
                remaining_features=remaining_features,
                description=app_description,
                recent_actions=last_actions[-5:] if last_actions else []
            )
            response = self.mllm.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print_with_color(f"Error deciding next action: {e}", "red")
            return None

    def extract_features_from_description(self, description: str) -> List[str]:
        """Extract features to explore from app description."""
        features = []
        try:
            # Use the feature extraction prompt
            prompt = prompts.feature_extraction_prompt.format(description=description)
            response = self.mllm.generate_content(prompt)
            
            # Check for insufficient description
            if "INSUFFICIENT_DESCRIPTION" in response.text:
                print_with_color("Description insufficient, will analyze screen for features", "yellow")
                return []
            
            # Parse features from response
            lines = response.text.split('\n')
            current_feature = None
            feature_details = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    # Save previous feature if exists
                    if current_feature and feature_details:
                        features.append(f"{current_feature}: {' '.join(feature_details)}")
                    
                    # Start new feature
                    current_feature = line.split('.', 1)[1].strip()
                    feature_details = []
                elif line.startswith(('- Expected behavior:', '- Verification method:', '- Edge cases:')):
                    feature_details.append(line)
            
            # Add last feature
            if current_feature and feature_details:
                features.append(f"{current_feature}: {' '.join(feature_details)}")
            
            # Validate features
            if not features:
                print_with_color("No features extracted from description, will analyze screen", "yellow")
                return []
                
            print_with_color(f"Extracted {len(features)} features from description", "green")
            return features
                
        except Exception as e:
            print_with_color(f"Error extracting features: {e}", "red")
            return []

    def check_exploration_completion(
        self,
        features_to_explore: Set[str],
        explored_features: Set[str],
        current_state: Dict,
        exploration_history: List[str]
    ) -> bool:
        """Check if exploration is complete and handle completion actions."""
        try:
            # Use the exploration completion prompt
            prompt = prompts.exploration_completion_prompt.format(
                features_to_explore=features_to_explore,
                explored_features=explored_features,
                current_state=current_state,
                exploration_history=exploration_history
            )
            response = self.mllm.generate_content(prompt)
            is_complete = "COMPLETE" in response.text.upper()
            
            if is_complete:
                print_with_color("Exploration complete! Returning to home screen...", "green")
                # Return to home screen
                self.controller.press_home()
                time.sleep(1)  # Wait for home screen to load
                
            return is_complete
            
        except Exception as e:
            print_with_color(f"Error checking exploration completion: {e}", "red")
            return False

    def is_same_state(self, state1: Dict, state2: Dict) -> bool:
        """Check if two states are considered the same."""
        # Implement your logic to compare two states
        # This is a placeholder and should be replaced with actual implementation
        return state1 == state2

def main(app: str, root_dir: str, package_name: str, app_description: str):
    """
    Main function to run the autonomous exploration.
    
    Args:
        app (str): Name of the application
        root_dir (str): Root directory for the agent's operation
        package_name (str): Package name of the target application
        app_description (str): Description of the app's purpose and functionality
    """
    try:
        # Initialize the explorer
        explorer = SelfExplorer(app, root_dir)
        explorer.package_name = package_name
        
        # Launch the app
        launch_app_by_package(package_name)
        time.sleep(2)  # Wait for app to launch
        
        # Get initial screen state
        current_state = explorer.get_current_state()
        
        # Extract features from description
        features_to_explore = set(explorer.extract_features_from_description(app_description))
        
        # If description was insufficient, analyze the main screen
        if not features_to_explore:
            print_with_color("Analyzing main screen for features...", "blue")
            features_to_explore = set(explorer.analyze_screen_features(current_state, app_description))
        
        print_with_color(f"Features to explore: {features_to_explore}", "blue")
        
        # Initialize exploration state
        explored_features = set()
        exploration_history = []
        consecutive_same_states = 0
        max_same_states = 3
        stuck_count = 0
        max_stuck_attempts = 3
        max_history_length = 100  # Prevent unbounded growth
        
        while True:
            # Get current screen state
            current_state = explorer.get_current_state()
            
            # Check if app is still running
            if not explorer.controller.is_app_running(package_name):
                print_with_color("App crashed or was closed. Attempting to relaunch...", "red")
                launch_app_by_package(package_name)
                time.sleep(2)
                current_state = explorer.get_current_state()

            # Analyze current screen and identify features
            current_features = explorer.analyze_screen_features(current_state, app_description)
            
            # Update explored features with validation
            for feature in current_features:
                if feature and isinstance(feature, str) and feature.strip():
                    explored_features.add(feature.strip())
            
            # Check if exploration is complete
            if explorer.check_exploration_completion(
                features_to_explore,
                explored_features,
                current_state,
                exploration_history
            ):
                print_with_color("Exploration complete!", "green")
                break
                
            # State comparison with tolerance for minor changes
            if explorer.is_same_state(current_state, explorer.last_state):
                consecutive_same_states += 1
                if consecutive_same_states >= max_same_states:
                    stuck_count += 1
                    if stuck_count >= max_stuck_attempts:
                        print_with_color("Too many stuck attempts, ending exploration", "red")
                        break
                        
                    # Try recovery sequence
                    print_with_color(f"Stuck in same state for {consecutive_same_states} times. Attempting recovery...", "yellow")
                    
                    # First try back navigation
                    print_with_color("Trying back navigation...", "yellow")
                    explorer.controller.back()
                    time.sleep(1)
                    
                    # If still stuck, try alternative navigation
                    if explorer.is_same_state(current_state, explorer.get_current_state()):
                        if not explorer.try_alternative_navigation():
                            # If alternative navigation fails, try relaunching the app
                            print_with_color("Alternative navigation failed. Relaunching app...", "yellow")
                            launch_app_by_package(package_name)
                            time.sleep(2)
                    
                    consecutive_same_states = 0
            else:
                consecutive_same_states = 0
                
            # Decide next action based on current state and remaining features
            action = explorer.decide_next_action(
                current_state,
                features_to_explore - explored_features,
                app_description,
                explorer.last_actions
            )
            
            # Execute the action
            if action:
                success = explorer.execute_action(action)
                if not success:
                    # If action failed, try back navigation first
                    print_with_color("Action failed, trying back navigation...", "yellow")
                    explorer.controller.back()
                    time.sleep(1)
                    
                    # If still having issues, try alternative navigation
                    if not explorer.execute_action(action):
                        if not explorer.try_alternative_navigation():
                            # If all recovery attempts fail, relaunch the app
                            print_with_color("All recovery attempts failed. Relaunching app...", "yellow")
                            launch_app_by_package(package_name)
                            time.sleep(2)
            else:
                # If no clear action, try to navigate to unexplored areas
                if not explorer.explore_unexplored_areas():
                    print_with_color("Could not find unexplored areas. Trying back navigation...", "yellow")
                    explorer.controller.back()
                    time.sleep(1)
            
            # Update exploration history with size limit
            exploration_history.append({
                'state': current_state,
                'action': action,
                'features': current_features
            })
            if len(exploration_history) > max_history_length:
                exploration_history = exploration_history[-max_history_length:]
            
            # Update last state
            explorer.last_state = current_state
            
            # Add a small delay between actions
            time.sleep(0.5)
            
    except Exception as e:
        print_with_color(f"Error during exploration: {e}", "red")
    finally:
        # Return to home screen
        try:
            explorer.controller.press_home()
            time.sleep(1)
        except:
            pass

if __name__ == "__main__":
    main() 