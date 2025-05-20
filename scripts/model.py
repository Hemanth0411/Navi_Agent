import re
import abc
import requests
import dashscope
from dashscope import MultiModalConversation
from http import HTTPStatus
from typing import List
import google.generativeai as genai # Added for Gemini
from PIL import Image # Added for Gemini image handling

from .utils import print_with_color, encode_image # Relative imports

class BaseModel(abc.ABC):
    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        pass

class OpenAIModel(BaseModel):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_tokens: int):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            base64_image = encode_image(img_path)
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        print_with_color("Sending request to OpenAI...", "yellow")
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()  # Raises an exception for HTTP error codes
            res = response.json()
            if "error" not in res:
                # Simple cost calculation (example, update with actual pricing)
                # Assuming gpt-4o pricing: $5/1M input tokens, $15/1M output tokens
                # This is a very rough estimate.
                # usage = res.get("usage", {})
                # prompt_tokens = usage.get("prompt_tokens", 0)
                # completion_tokens = usage.get("completion_tokens", 0)
                # cost = (prompt_tokens / 1000000 * 5) + (completion_tokens / 1000000 * 15)
                # print_with_color(f"OpenAI API call successful. Estimated cost: ${cost:.6f}", "green")
                return True, res["choices"][0]["message"]["content"]
            else:
                print_with_color(f"OpenAI API Error: {res['error']['message']}", "red")
                return False, res["error"]["message"]
        except requests.exceptions.RequestException as e:
            print_with_color(f"Request to OpenAI API failed: {e}", "red")
            return False, str(e)
        except Exception as e:
            print_with_color(f"An unexpected error occurred: {e}", "red")
            return False, str(e)

class QwenModel(BaseModel):
    def __init__(self, api_key: str, model: str):
        super().__init__()
        dashscope.api_key = api_key
        self.model = model

    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        content = [{'text': prompt}]
        for img_path in images:
            # DashScope SDK can handle local file paths for images
            content.append({"image": f"file://{img_path}"})
        
        messages = [{
            'role': 'user', 
            'content': content
        }]
        
        print_with_color("Sending request to Qwen (DashScope)...", "yellow")
        try:
            response = MultiModalConversation.call(model=self.model, messages=messages)
            if response.status_code == HTTPStatus.OK:
                # print_with_color("Qwen API call successful.", "green")
                return True, response.output.choices[0].message.content
            else:
                err_msg = f"Qwen API Error: Code: {response.code}, Message: {response.message}"
                print_with_color(err_msg, "red")
                return False, err_msg
        except Exception as e:
            print_with_color(f"An unexpected error occurred with Qwen API: {e}", "red")
            return False, str(e)

# Added GeminiModel class
class GeminiModel(BaseModel):
    def __init__(self, api_key: str, model_name: str):
        super().__init__()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        # Assuming model_name is something like 'gemini-pro-vision' or 'gemini-1.5-pro-latest'

    def get_model_response(self, prompt: str, image_paths: List[str]) -> tuple[bool, str]:
        print_with_color(f"Sending request to Gemini ({self.model.model_name})...", "yellow")
        try:
            model_input = [prompt] # Start with the text prompt
            for img_path in image_paths:
                try:
                    img = Image.open(img_path)
                    model_input.append(img) # Append PIL Image object
                except FileNotFoundError:
                    print_with_color(f"Image file not found: {img_path}", "red")
                    return False, f"Image file not found: {img_path}"
                except Exception as e:
                    print_with_color(f"Error loading image {img_path}: {e}", "red")
                    return False, f"Error loading image {img_path}: {e}"
            
            # Generate content
            # For gemini-pro-vision, this is direct. For newer models like 1.5 Pro, 
            # you might use generate_content with a specific schema if needed for complex prompting.
            response = self.model.generate_content(model_input)
            
            # Ensure response.text is accessed correctly
            if hasattr(response, 'text') and response.text:
                # print_with_color("Gemini API call successful.", "green")
                return True, response.text
            elif hasattr(response, 'parts') and response.parts:
                 # If the response is structured with parts, concatenate text parts.
                text_parts = [part.text for part in response.parts if hasattr(part, 'text')]
                if text_parts:
                    # print_with_color("Gemini API call successful (from parts).", "green")
                    return True, " ".join(text_parts)
                else:
                    print_with_color("Gemini API Error: No text content found in response parts.", "red")
                    return False, "Gemini API Error: No text content found in response parts."
            else:
                # Check for prompt feedback or finish reason if no direct text
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    err_msg = f"Gemini API Error: Blocked - {response.prompt_feedback.block_reason}"
                    print_with_color(err_msg, "red")
                    return False, err_msg
                print_with_color("Gemini API Error: Response format not recognized or empty text.", "red")
                return False, "Gemini API Error: Response format not recognized or empty text."

        except Exception as e:
            # Catching general exceptions from the Gemini API call
            # Specific exceptions like google.api_core.exceptions.GoogleAPIError can also be caught
            error_message = f"An unexpected error occurred with Gemini API: {e}"
            # Try to get more detailed error if available (e.g. from response object if partially formed)
            if hasattr(e, 'message'): # Some Google API errors have a message attribute
                error_message = f"An unexpected error occurred with Gemini API: {e.message}"
            print_with_color(error_message, "red")
            return False, error_message

def parse_explore_rsp(rsp):
    try:
        # (Existing robust regex for Observation, Thought, Action, Summary - assumed from previous successful edit)
        obs_match = re.search(r"Observation:\s*(.*?)\s*Thought:", rsp, re.DOTALL | re.MULTILINE)
        thought_match = re.search(r"Thought:\s*(.*?)\s*Action:", rsp, re.DOTALL | re.MULTILINE)
        act_match = re.search(r"Action:\s*(.*?)\s*Summary:", rsp, re.DOTALL | re.MULTILINE)
        summary_match = re.search(r"Summary:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)

        if not (obs_match and thought_match and act_match and summary_match):
            # Fallback logic (assumed from previous successful edit)
            print_with_color("Full response pattern not matched, attempting partial extraction.", "yellow")
            obs = re.search(r"Observation:\s*(.*?)(?:\nThought:|$)", rsp, re.DOTALL | re.MULTILINE)
            thought = re.search(r"Thought:\s*(.*?)(?:\nAction:|$)", rsp, re.DOTALL | re.MULTILINE)
            act = re.search(r"Action:\s*(.*?)(?:\nSummary:|$)", rsp, re.DOTALL | re.MULTILINE)
            summary = re.search(r"Summary:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)
            obs_text = obs.group(1).strip() if obs else "ERROR: Observation not found"
            thought_text = thought.group(1).strip() if thought else "ERROR: Thought not found"
            act_text = act.group(1).strip() if act else "ERROR: Action not found"
            summary_text = summary.group(1).strip() if summary else "ERROR: Summary not found"
            if "ERROR:" in obs_text or "ERROR:" in thought_text or "ERROR:" in act_text or "ERROR:" in summary_text:
                error_details = f"Obs: '{obs_text}', Thought: '{thought_text}', Act: '{act_text}', Sum: '{summary_text}'"
                print_with_color(f"Failed to parse essential parts of VLM response. Details: {error_details} RSP: {rsp}", "red")
                return ["ERROR"]
        else:
            obs_text = obs_match.group(1).strip()
            thought_text = thought_match.group(1).strip()
            act_text = act_match.group(1).strip()
            summary_text = summary_match.group(1).strip()

        print_with_color(f"Observation: {obs_text}", "green")
        print_with_color(f"Thought: {thought_text}", "green")
        print_with_color(f"Action: {act_text}", "green")
        print_with_color(f"Summary: {summary_text}", "green")
        last_act = summary_text

        # Handle simple actions first (no parentheses or parameters)
        simple_action_match = re.match(r"(\w+)\s*(?:\(\s*\))?$", act_text) # Matches "ACTION" or "ACTION()"
        
        parsed_simple_action_name = ""
        if simple_action_match:
            parsed_simple_action_name = simple_action_match.group(1).upper()

        if parsed_simple_action_name == "FINISH": return ["FINISH"]
        if parsed_simple_action_name == "PRESS_BACK": return ["press_back", last_act]
        if parsed_simple_action_name == "PRESS_HOME": return ["press_home", last_act]
        if parsed_simple_action_name == "PRESS_ENTER": return ["press_enter", last_act]
        if parsed_simple_action_name == "PRESS_DELETE": return ["press_delete", last_act]
        if parsed_simple_action_name == "OPEN_NOTIFICATIONS": return ["open_notifications", last_act]
        if parsed_simple_action_name == "PRESS_APP_SWITCH": return ["press_app_switch", last_act]
        if parsed_simple_action_name == "GRID": return ["grid"] 

        # Parse actions with parameters: func_name(params)
        match = re.match(r"(\w+)\s*\((.*)\)", act_text)
        if not match:
            print_with_color(f"Unknown action format (after checking simple actions): {act_text}", "red")
            return ["ERROR"]

        act_name = match.group(1).lower()
        params_str = match.group(2).strip()

        if act_name == "tap":
            try:
                param_str_cleaned = params_str
                if params_str.lower().startswith("e") and len(params_str) > 1: # Check if it starts with 'e'
                    param_str_cleaned = params_str[1:] # Remove the 'e'
                area = int(param_str_cleaned)
                return [act_name, area, last_act] # or return chosen_sub_task, [act_name, area, last_act_summary]
            except ValueError: print_with_color(f"Invalid parameter for tap: {params_str}", "red"); return ["ERROR"]
        elif act_name == "type_global": # Changed from "type_text" to "type_global"
            input_str = params_str.strip("'\"") 
            return [act_name, input_str, last_act]
        
        elif act_name == "long_press":
            try: area = int(params_str); return [act_name, area, last_act]
            except ValueError: print_with_color(f"Invalid parameter for long_press: {params_str}", "red"); return ["ERROR"]
        
        elif act_name == "swipe_element": 
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 3: # element_id (area), direction, distance
                    area = int(parts[0])
                    direction = parts[1].lower()
                    distance = parts[2].lower() 
                    return [act_name, area, direction, distance, last_act]
                else: print_with_color(f"Invalid parameters for swipe_element: {params_str}", "red"); return ["ERROR"]
            except ValueError: print_with_color(f"Error parsing swipe_element parameters: {params_str}", "red"); return ["ERROR"]
        
        elif act_name == "swipe_screen":
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 2: # direction, distance
                    direction = parts[0].lower()
                    distance = parts[1].lower() 
                    return [act_name, direction, distance, last_act]
                else: print_with_color(f"Invalid parameters for swipe_screen: {params_str}", "red"); return ["ERROR"]
            except ValueError: print_with_color(f"Error parsing swipe_screen parameters: {params_str}", "red"); return ["ERROR"]
        
        else:
            print_with_color(f"Unknown action name: {act_name} from parsed action {act_text}", "red")
            return ["ERROR"]

    except Exception as e:
        print_with_color(f"Error parsing VLM response: {e}, RSP: {rsp}", "red")
        return ["ERROR"]

def parse_reflect_rsp(rsp):
    try:
        decision_text = "ERROR: Decision not found"
        thought_text = "ERROR: Thought not found"
        doc_text = "N/A" # Default for documentation, as it might be optional or not applicable

        # Attempt to find Decision
        decision_match = re.search(r"Decision:\s*(.*?)(?:\nThought:|\nDocumentation:|$)", rsp, re.DOTALL | re.MULTILINE)
        if decision_match:
            decision_text = decision_match.group(1).strip()

        # Attempt to find Thought
        thought_match = re.search(r"Thought:\s*(.*?)(?:\nDocumentation:|$)", rsp, re.DOTALL | re.MULTILINE)
        if thought_match:
            thought_text = thought_match.group(1).strip()
        elif decision_text != "ERROR: Decision not found": 
            pass 

        # Attempt to find Documentation (it's often the last part)
        doc_match = re.search(r"Documentation:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)
        if doc_match:
            doc_text = doc_match.group(1).strip()
        
        if decision_text.startswith("ERROR:") or thought_text.startswith("ERROR:"):
            error_details = f"Parsed Decision: '{decision_text}', Parsed Thought: '{thought_text}', Parsed Doc: '{doc_text}'"
            print_with_color(f"Failed to parse essential parts of VLM reflection. Details: {error_details}. RSP: {rsp}", "red")
            return ["ERROR"]

        print_with_color(f"Decision: {decision_text}", "green")
        print_with_color(f"Thought: {thought_text}", "green")
        print_with_color(f"Documentation: {doc_text}", "green")
        
        decision_upper = decision_text.upper()
        valid_decisions = ["BACK", "CONTINUE", "SUCCESS", "INEFFECTIVE"]
        if decision_upper in valid_decisions:
            return [decision_upper, thought_text, doc_text]
        else:
            print_with_color(f"Unknown or malformed decision: '{decision_text}' (parsed as '{decision_upper}')", "red")
            return ["ERROR"]
            
    except Exception as e:
        print_with_color(f"Critical error in parse_reflect_rsp: {e}, RSP: {rsp}", "red")
        return ["ERROR"]

def parse_initial_input_analysis(rsp: str) -> tuple[str | None, str | None, list[str] | None]:
    """
    Parses the response from the initial_input_analysis_template.
    Returns: (input_type, app_context, initial_goals_list)
             Returns (None, None, None) on parsing failure.
    """
    try:
        input_type_match = re.search(r"InputType:\s*(TASK|DESCRIPTION)", rsp, re.IGNORECASE)
        app_context_match = re.search(r"IdentifiedAppContext:\s*(.*?)\s*InitialGoals:", rsp, re.DOTALL | re.MULTILINE)
        initial_goals_match = re.search(r"InitialGoals:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)

        if not (input_type_match and app_context_match and initial_goals_match):
            print_with_color("Could not parse all required fields from initial input analysis.", "red")
            return None, None, None

        input_type = input_type_match.group(1).upper()
        app_context = app_context_match.group(1).strip()
        goals_text = initial_goals_match.group(1).strip()

        initial_goals_list = []
        if input_type == "DESCRIPTION" and goals_text.lower() != "n/a":
            # Assuming goals are bulleted, e.g., "- Goal 1\n- Goal 2"
            for line in goals_text.split('\n'):
                line = line.strip()
                if line.startswith(('-', '*')):
                    initial_goals_list.append(line[1:].strip())
                elif line: # If not bulleted but not empty
                    initial_goals_list.append(line)
        
        print_with_color(f"Initial Analysis - InputType: {input_type}, AppContext: {app_context}, Goals: {initial_goals_list}", "cyan")
        return input_type, app_context, initial_goals_list
    except Exception as e:
        print_with_color(f"Error parsing initial input analysis response: {e}, RSP: {rsp}", "red")
        return None, None, None

def parse_exploration_step_rsp(rsp: str) -> tuple[str | None, list[str] | None]:
    """
    Parses the response from the app_exploration_task_template.
    Returns: (chosen_sub_task, [action_name, param1, ..., summary]) or (None, None) on error
    """
    try:
        chosen_sub_task_match = re.search(r"ChosenSubTask:\s*(.*?)\s*Observation:", rsp, re.DOTALL | re.MULTILINE)
        # The rest of the parsing is identical to parse_explore_rsp
        obs_match = re.search(r"Observation:\s*(.*?)\s*Thought:", rsp, re.DOTALL | re.MULTILINE)
        thought_match = re.search(r"Thought:\s*(.*?)\s*Action:", rsp, re.DOTALL | re.MULTILINE)
        act_match = re.search(r"Action:\s*(.*?)\s*Summary:", rsp, re.DOTALL | re.MULTILINE)
        summary_match = re.search(r"Summary:\s*(.*)", rsp, re.DOTALL | re.MULTILINE)

        if not (chosen_sub_task_match and obs_match and thought_match and act_match and summary_match):
            print_with_color("Full exploration response pattern not matched.", "yellow")
            # Add fallback if needed, or just error out
            return None, ["ERROR", "Failed to parse exploration step structure"]


        chosen_sub_task = chosen_sub_task_match.group(1).strip()
        # Re-use parse_explore_rsp's core logic for the O/T/A/S part
        # To do this cleanly, you might extract the O/T/A/S parsing part of parse_explore_rsp into a helper
        # For now, let's duplicate the action parsing logic slightly modified.
        
        act_text = act_match.group(1).strip()
        summary_text = summary_match.group(1).strip()
        last_act_summary = summary_text # For consistency with parse_explore_rsp's return

        print_with_color(f"ChosenSubTask: {chosen_sub_task}", "magenta")
        print_with_color(f"Observation: {obs_match.group(1).strip()}", "green")
        print_with_color(f"Thought: {thought_match.group(1).strip()}", "green")
        print_with_color(f"Action: {act_text}", "green")
        print_with_color(f"Summary: {summary_text}", "green")
        last_act = summary_text

        # Action parsing logic (copied and adapted from parse_explore_rsp)
        simple_action_match = re.match(r"(\w+)\s*(?:\(\s*\))?$", act_text)
        parsed_simple_action_name = ""
        parsed_simple_action_name = ""
        if simple_action_match:
            parsed_simple_action_name = simple_action_match.group(1).upper()

        if parsed_simple_action_name == "FINISH": return ["FINISH"]
        if parsed_simple_action_name == "PRESS_BACK": return ["press_back", last_act]
        if parsed_simple_action_name == "PRESS_HOME": return ["press_home", last_act]
        if parsed_simple_action_name == "PRESS_ENTER": return ["press_enter", last_act]
        if parsed_simple_action_name == "PRESS_DELETE": return ["press_delete", last_act]
        if parsed_simple_action_name == "OPEN_NOTIFICATIONS": return ["open_notifications", last_act]
        if parsed_simple_action_name == "PRESS_APP_SWITCH": return ["press_app_switch", last_act]
        if parsed_simple_action_name == "GRID": return ["grid"] 


        param_match = re.match(r"(\w+)\s*\((.*)\)", act_text)
        if not param_match:
            print_with_color(f"Unknown action format in exploration: {act_text}", "red")
            return chosen_sub_task, ["ERROR", f"Unknown action format: {act_text}"]

        act_name = param_match.group(1).lower()
        params_str = param_match.group(2).strip()

        # Parameterized action parsing (copied from parse_explore_rsp)
        if act_name == "tap":
            try:
                param_str_cleaned = params_str
                if params_str.lower().startswith("e") and len(params_str) > 1: # Check if it starts with 'e'
                    param_str_cleaned = params_str[1:] # Remove the 'e'
                area = int(param_str_cleaned)
                return [act_name, area, last_act] # or return chosen_sub_task, [act_name, area, last_act_summary]
            except ValueError: print_with_color(f"Invalid parameter for tap: {params_str}", "red"); return ["ERROR"]
        elif act_name == "type_global": # Changed from "type_text" to "type_global"
            input_str = params_str.strip("'\"") 
            return [act_name, input_str, last_act]
        
        elif act_name == "long_press":
            try: area = int(params_str); return [act_name, area, last_act]
            except ValueError: print_with_color(f"Invalid parameter for long_press: {params_str}", "red"); return ["ERROR"]
        
        elif act_name == "swipe_element": 
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 3: # element_id (area), direction, distance
                    area = int(parts[0])
                    direction = parts[1].lower()
                    distance = parts[2].lower() 
                    return [act_name, area, direction, distance, last_act]
                else: print_with_color(f"Invalid parameters for swipe_element: {params_str}", "red"); return ["ERROR"]
            except ValueError: print_with_color(f"Error parsing swipe_element parameters: {params_str}", "red"); return ["ERROR"]
        
        elif act_name == "swipe_screen":
            try:
                parts = [p.strip(" '\"") for p in params_str.split(",")]
                if len(parts) == 2: # direction, distance
                    direction = parts[0].lower()
                    distance = parts[1].lower() 
                    return [act_name, direction, distance, last_act]
                else: print_with_color(f"Invalid parameters for swipe_screen: {params_str}", "red"); return ["ERROR"]
            except ValueError: print_with_color(f"Error parsing swipe_screen parameters: {params_str}", "red"); return ["ERROR"]
        else:
            return chosen_sub_task, ["ERROR", f"Unknown parameterized action name: {act_name}"]

    except Exception as e:
        print_with_color(f"Error parsing exploration step response: {e}, RSP: {rsp}", "red")
        return None, ["ERROR", f"Exception in parsing: {str(e)}"]
