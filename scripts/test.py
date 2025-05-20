import json
import re
import abc
import os
from typing import List

# Necessary imports for GeminiModel
import google.generativeai as genai
from PIL import Image

# Necessary imports for OpenAIModel
import requests # Make sure 'requests' is installed: pip install requests
import base64   # For encoding images for OpenAI

# --- Utility Function (from your utils.py) ---
try:
    from colorama import Fore, Style
    def print_with_color(text: str, color=""):
        color_map = {
            "red": Fore.RED, "green": Fore.GREEN, "yellow": Fore.YELLOW,
            "blue": Fore.BLUE, "magenta": Fore.MAGENTA, "cyan": Fore.CYAN
        }
        if color in color_map:
            print(color_map[color] + text)
        else:
            print(text)
        print(Style.RESET_ALL)
except ImportError:
    print("Warning: colorama not found. print_with_color will be basic.")
    def print_with_color(text: str, color=""):
        if color: print(f"[{color.upper()}] {text}")
        else: print(text)

# --- Model Definitions ---
class BaseModel(abc.ABC):
    def __init__(self):
        super().__init__()
    @abc.abstractmethod
    def get_model_response(self, prompt: str, images: List[str]) -> tuple[bool, str]: # This will be used now
        pass

   
class GeminiModel(BaseModel): # (Ensure full class definition is here)
    def __init__(self, api_key: str, model_name: str):
        super().__init__()
        try: genai.configure(api_key=api_key); self.model = genai.GenerativeModel(model_name)
        except Exception as e: print_with_color(f"Gemini init failed: {e}", "red"); raise

    def get_model_response(self, prompt: str, image_paths: List[str]) -> tuple[bool, str]:
        print_with_color(f"Sending request to Gemini ({self.model.model_name})...", "yellow")
        try:
            model_input = [prompt]
            for img_path in image_paths:
                if not os.path.exists(img_path): return False, f"Image file not found: {img_path}"
                try: img = Image.open(img_path); model_input.append(img)
                except Exception as e: return False, f"Error loading image {img_path}: {e}"
            response = self.model.generate_content(model_input, request_options={"timeout": 180})
            if hasattr(response, 'text') and response.text: return True, response.text
            if hasattr(response, 'parts') and response.parts:
                text_parts = [p.text for p in response.parts if hasattr(p, 'text')]
                if text_parts: return True, " ".join(text_parts)
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return False, f"Gemini API Error: Blocked - {response.prompt_feedback.block_reason}"
            return False, "Gemini API Error: No text content or unrecognized format."
        except Exception as e: return False, f"Gemini API Error: {getattr(e, 'message', str(e))}"

class OpenAIModel(BaseModel): # (Ensure full class definition is here)
    def __init__(self, api_key: str, model_name: str, base_url: str = "https://api.openai.com/v1/chat/completions"):
        super().__init__()
        self.api_key = api_key; self.model_name = model_name; self.base_url = base_url
        self.max_tokens = 1024; self.temperature = 0.2

    def _encode_image(self, image_path):
        with open(image_path, "rb") as f: return base64.b64encode(f.read()).decode('utf-8')

    def get_model_response(self, prompt: str, image_paths: List[str]) -> tuple[bool, str]:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        content = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            if not os.path.exists(img_path): return False, f"Image file not found: {img_path}"
            try:
                base64_image = self._encode_image(img_path)
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})
            except Exception as e: return False, f"Error encoding image {img_path}: {e}"
        payload = {"model": self.model_name, "messages": [{"role": "user", "content": content}],
                   "max_tokens": self.max_tokens, "temperature": self.temperature}
        print_with_color(f"Sending request to OpenAI ({self.model_name})...", "yellow")
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=180)
            response.raise_for_status(); res = response.json()
            if "error" not in res: return True, res["choices"][0]["message"]["content"]
            return False, f"OpenAI API Error: {res['error']['message']}"
        except requests.exceptions.RequestException as e: return False, f"OpenAI API Request failed: {e}"
        except Exception as e: return False, f"OpenAI unexpected error: {e}"

def get_coordinates_from_cell_info(cell_info: dict, point_name_key: str) -> tuple[int, int] | None:
    if not cell_info: return None
    point_name_key = point_name_key.lower()
    if point_name_key == "center":
        return tuple(cell_info.get("center_px", [])) if cell_info.get("center_px") else None
    q_centers = cell_info.get("quadrant_centers_px", {})
    quadrant_map = {
        "top_left_quadrant": "top_left", "top_right_quadrant": "top_right",
        "bottom_left_quadrant": "bottom_left", "bottom_right_quadrant": "bottom_right"
    }
    if point_name_key in quadrant_map:
        return tuple(q_centers.get(quadrant_map[point_name_key], [])) if q_centers.get(quadrant_map[point_name_key]) else None
    bounds = cell_info.get("bounds_px", [])
    if len(bounds) == 4:
        x_min, y_min, x_max, y_max = bounds
        if point_name_key == "top_left_corner": return (x_min, y_min)
        if point_name_key == "top_right_corner": return (x_max, y_min) # Assuming x_max is inclusive for corner
        if point_name_key == "bottom_left_corner": return (x_min, y_max) # Assuming y_max is inclusive for corner
        if point_name_key == "bottom_right_corner": return (x_max, y_max) # Assuming x_max, y_max are inclusive
    return None


def get_play_store_tap_coordinates_visual_choice( # Renamed
    llm_instance: BaseModel,
    original_screenshot_path: str,
    gridded_screenshot_path: str,
    grid_info_json_path: str # We still load this locally for coordinate lookup
) -> tuple[int, int] | None:
    if not all(os.path.exists(p) for p in [original_screenshot_path, gridded_screenshot_path, grid_info_json_path]):
        print_with_color("One or more input files not found.", "red"); return None

    try:
        with open(grid_info_json_path, 'r') as f:
            grid_cells_data_list = json.load(f) # Load for local lookup
        if not grid_cells_data_list:
            print_with_color("Grid info JSON is empty.", "red"); return None
    except Exception as e:
        print_with_color(f"Error reading grid_info.json: {e}", "red"); return None

    # Describe the structure of the JSON the agent *would* use locally
    json_structure_description = """
You, the AI agent, have access to a local JSON file (not sent in this prompt) that describes each grid cell seen in 'gridded_screenshot.png'. For any `cell_id` you identify, this local JSON provides:
- `"bounds_px": [x_min, y_min, x_max, y_max]` (the cell's pixel boundaries)
- `"center_px": [x, y]` (the cell's exact center)
- `"quadrant_centers_px": { "top_left": [x,y], "top_right": [x,y], "bottom_left": [x,y], "bottom_right": [x,y] }` (centers of the cell's four quadrants)

Based on this knowledge of available local data, your task is to analyze the images.
"""

    prompt = f"""
You are an Android AI agent. Your current task is to open the Google Play Store app.
You are provided with 'original_screenshot.png' and 'gridded_screenshot.png'.
{json_structure_description}

**Instructions for your response:**

1.  **Locate Icon Cell:** From 'gridded_screenshot.png', identify the `cell_id` (the number shown on the grid) that most prominently contains the Google Play Store icon.
2.  **Analyze Icon within Cell:** For the identified `cell_id`, carefully observe the position of the Play Store icon *within that cell's boundaries*.
3.  **Score Tap Points:** For this *identified cell*, assign a "Suitability Score" (0% to 100%) to each of the following EIGHT potential tap point *types*. The score should represent your confidence that tapping a point of this type *within the identified cell* will successfully activate the Play Store icon.
    *   `center` (of the cell)
    *   `top_left_quadrant` (center of the cell's top-left quadrant)
    *   `top_right_quadrant` (center of the cell's top-right quadrant)
    *   `bottom_left_quadrant` (center of the cell's bottom-left quadrant)
    *   `bottom_right_quadrant` (center of the cell's bottom-right quadrant)
    *   `top_left_corner` (the cell's actual top-left corner pixel)
    *   `top_right_corner` (the cell's actual top-right corner pixel)
    *   `bottom_left_corner` (the cell's actual bottom-left corner pixel)
    *   `bottom_right_corner` (the cell's actual bottom-right corner pixel)
4.  **Recommend Best Point Type:** Based on your scores, state which of the eight point *type names* you recommend for tapping.
5.  **Reasoning:** Briefly explain your scoring and recommendation, referencing the icon's visual position within the cell.

Respond ONLY with a single JSON object in the following format. Do NOT include any other text before or after the JSON.

```json
{{
  "reasoning": "The Play Store icon is well-centered within its cell. Tapping the 'center' of the cell offers the highest probability.",
  "identified_cell_id": <cell_id_number_where_Play_Store_is_located>,
  "point_suitability_scores": {{
    "center": "<score%>",
    "top_left_quadrant": "<score%>",
    "top_right_quadrant": "<score%>",
    "bottom_left_quadrant": "<score%>",
    "bottom_right_quadrant": "<score%>",
    "top_left_corner": "<score%>",
    "top_right_corner": "<score%>",
    "bottom_left_corner": "<score%>",
    "bottom_right_corner": "<score%>"
  }},
  "recommended_point_name": "<one_of_the_eight_point_type_names_above>"
}}"""
    image_paths_for_llm = [original_screenshot_path, gridded_screenshot_path]
    # Use the standard get_model_response now
    status, response_text = llm_instance.get_model_response(
        prompt, image_paths_for_llm
    )

    if not status:
        print_with_color(f"LLM API call failed: {response_text}", "red"); return None

    print_with_color(f"LLM Raw Response:\n{response_text}", "cyan")

    try:
        cleaned_response_text = response_text.strip()
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[len("```json"):].strip()
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-len("```")].strip()
        
        llm_output_data = json.loads(cleaned_response_text)

        target_cell_id = llm_output_data.get("identified_cell_id")
        point_scores = llm_output_data.get("point_suitability_scores", {})
        # Normalize the recommended point name from LLM for matching our keys
        recommended_point_name_from_llm = llm_output_data.get("recommended_point_name", "").lower().replace(" ", "_")
        reasoning = llm_output_data.get("reasoning", "No reasoning provided.")

        if target_cell_id is None or not point_scores or not recommended_point_name_from_llm:
            print_with_color(f"LLM JSON output missing required fields. Output: {llm_output_data}", "red"); return None

        print_with_color(f"LLM Detected Grid Cell ID: {target_cell_id}", "green")
        print_with_color(f"LLM Reasoning: {reasoning}", "magenta")
        print_with_color("LLM Suitability Scores for points in detected cell:", "yellow")
        for point_name, score in point_scores.items(): # point_name here is as LLM provided it
            print_with_color(f"  - {point_name}: {score}", "yellow")
        print_with_color(f"LLM Recommended Point Name (normalized): '{recommended_point_name_from_llm}'", "green")

        # These are the keys our get_coordinates_from_cell_info function expects
        valid_point_name_keys_for_lookup = [
            "center", "top_left_quadrant", "top_right_quadrant",
            "bottom_left_quadrant", "bottom_right_quadrant",
            "top_left_corner", "top_right_corner",
            "bottom_left_corner", "bottom_right_corner"
        ]
        if recommended_point_name_from_llm not in valid_point_name_keys_for_lookup:
            print_with_color(f"Invalid 'recommended_point_name' from LLM after normalization: '{recommended_point_name_from_llm}'", "red")
            return None

        target_cell_info = next((cell for cell in grid_cells_data_list if cell.get("cell_id") == target_cell_id), None)
        if not target_cell_info:
            print_with_color(f"Grid cell ID {target_cell_id} (from LLM) not found in OUR JSON data.", "red"); return None
        
        # Use the new helper function to get coordinates based on the LLM's chosen point name
        final_coordinates = get_coordinates_from_cell_info(target_cell_info, recommended_point_name_from_llm)
            
        if not final_coordinates or len(final_coordinates) != 2:
            print_with_color(f"Could not retrieve valid coordinates for '{recommended_point_name_from_llm}' in cell {target_cell_id} from OUR JSON.", "red")
            print_with_color(f"Cell Info: {target_cell_info}", "yellow")
            return None

        return tuple(final_coordinates)

    except json.JSONDecodeError:
        print_with_color(f"Failed to decode LLM response as JSON. Response was:\n{response_text}", "red"); return None
    except Exception as e:
        print_with_color(f"Error processing LLM JSON output or calculating coordinates: {e.__class__.__name__}: {e}", "red"); return None
if __name__ == "__main__":
    # --- IMPORTANT: Set your API Keys ---
    # For security, prefer environment variables or a config file in real applications
    GEMINI_API_KEY = ""
    OPENAI_API_KEY = ""


    original_screenshot_path = r"C:\Users\lonel\Desktop\Study\AI Agent for android\14th\Navi_Agent_1\grid_test_output\test_0_grid_orig.png"
    gridded_screenshot_path = r"C:\Users\lonel\Desktop\Study\AI Agent for android\14th\Navi_Agent_1\grid_test_output\test_0_gridded.png"
    grid_info_json_path = r"C:\Users\lonel\Desktop\Study\AI Agent for android\14th\Navi_Agent_1\grid_test_output\test_0_grid_info.json"

    if "YOUR_GEMINI_API_KEY_HERE" in GEMINI_API_KEY and "YOUR_OPENAI_API_KEY_HERE" in OPENAI_API_KEY:
        print_with_color("Please set your API keys.", "red"); exit(1)
        print("Choose LLM:\n1. Gemini (gemini-1.5-flash)\n2. OpenAI (gpt-4o)")
        choice = input("Enter choice (1 or 2): ")
        llm_instance = None

        print("Choose LLM:\n1. Gemini (gemini-1.5-flash)\n2. OpenAI (gpt-4o)")
    choice = input("Enter choice (1 or 2): ")
    llm_instance = None

    if choice == '1':
        try: llm_instance = GeminiModel(api_key=GEMINI_API_KEY, model_name="gemini-1.5-flash"); print_with_color("Using Gemini.", "green")
        except Exception as e: print_with_color(f"Gemini init failed: {e}", "red"); exit()
    elif choice == '2':
        try: llm_instance = OpenAIModel(api_key=OPENAI_API_KEY, model_name="gpt-4o"); print_with_color("Using OpenAI (gpt-4o).", "green")
        except Exception as e: print_with_color(f"OpenAI init failed: {e}", "red"); exit()
    else:
        print_with_color("Invalid choice.", "red"); exit()

    if llm_instance:
        coordinates = get_play_store_tap_coordinates_visual_choice( # Called the new function
            llm_instance,
            original_screenshot_path,
            gridded_screenshot_path,
            grid_info_json_path
        )
        if coordinates:
            print_with_color(f"\n>>> Final Recommended Tap Coordinates for Play Store: {coordinates}", "green")
        else:
            print_with_color("\nFailed to determine Play Store tap coordinates.", "red")