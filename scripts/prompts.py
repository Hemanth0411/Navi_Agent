tap_doc_template = """You are describing the function of a UI element on a mobile app.
I will give you:
1. Screenshots before and after the UI element (labeled <ui_element>) was tapped.
2. The overall task context: <task_desc>.

Your task: Describe the general functionality of the tapped UI element in 1-2 concise sentences.
Focus on what the element *does*, not specific content it reveals (e.g., instead of "shows John's chat", say "navigates to a user's chat window").
Do NOT include the numeric tag '<ui_element>' in your description. Refer to it as "this UI element" or "this area".
Example: "Tapping this area will navigate the user to the chat window."
"""

text_doc_template = """You are describing the function of a text input area on a mobile app.
I will give you:
1. Screenshots before and after text was typed into the input area (labeled <ui_element>).
2. The overall task context: <task_desc>.

Your task: Describe the general functionality of this input area in 1-2 concise sentences.
Focus on the *purpose* of the input field (e.g., "used for typing a search query", "allows user to enter their name").
Do NOT mention the specific text that was typed. Do NOT include the numeric tag '<ui_element>'.
Example: "This input area is used for the user to type a message to send to the chat window."
"""

long_press_doc_template = """You are describing the function of a UI element on a mobile app.
I will give you:
1. Screenshots before and after the UI element (labeled <ui_element>) was long-pressed.
2. The overall task context: <task_desc>.

Your task: Describe the general functionality of the long-pressed UI element in 1-2 concise sentences.
Focus on what the long-press action *achieves* (e.g., "opens a context menu", "enables selection mode").
Do NOT include the numeric tag '<ui_element>'.
Example: "Long pressing this area will open a context menu with further options."
"""

swipe_doc_template = """You are describing the function of a UI element or area on a mobile app that was swiped.
I will give you:
1. Screenshots before and after swiping <swipe_dir> on the UI element (labeled <ui_element>).
2. The overall task context: <task_desc>.

Your task: Describe the general functionality revealed or achieved by swiping this element/area in 1-2 concise sentences.
Focus on the *purpose* of the swipe action on this element (e.g., "scrolls through a list of items", "adjusts a setting like brightness").
Do NOT include the numeric tag '<ui_element>'.
Example: "Swiping this area enables the user to tune a specific parameter of the image."
"""

refine_doc_suffix = """
An existing documentation for this UI element is: "<old_doc>"
Your new description should integrate insights from the current interaction and refine this existing documentation. If there's a conflict, prioritize the most general and accurate function.
"""

# --- CORE TASK AND EXPLORATION PROMPT ---
# This template is used for both direct tasks and self-generated exploration sub-tasks.
# The <mode_specific_goal_or_task> placeholder will be filled differently.

core_interaction_template = """You are an intelligent agent controlling a smartphone.
You will be given:
1. The current smartphone screenshot with interactive UI elements labeled with numeric tags.
2. Documentation for some UI elements on this screen, if available:
   <ui_document>
3. Your current objective: <mode_specific_goal_or_task>
4. A summary of your previous action: <last_act>
5. For exploration mode, a list of features/areas already explored:
   <explored_features_history> (This will be "N/A" if not in exploration mode)

First, observe the screen and use any provided documentation.
Then, think step-by-step to decide the best next action TO ACHIEVE YOUR OBJECTIVE.
Finally, choose ONE function from the "Available Functions" list.

General Hints for Common Scenarios:
- **Handling Pop-ups, Dialogs, and Unexpected Interruptions (e.g., Permission Requests, Error Messages):**
    - **Primary Goal:** Dismiss the interruption to return to your main task, unless the pop-up is essential for your current objective (e.g., a login prompt).
    - **Google Search Bar Voice Issues:** If you intended to type in the Google Search bar but a voice prompt (like "Didn't catch that") appeared:
        1.  Dismiss the voice error ( using `press_back()`).
        2.  **Crucially, `tap()` the main text area of the search bar again.**
        3.  Then use `type_global()`.
        4.  Finally, `press_enter()` to submit the search or URL.
    - **Dismissal Strategy (Prioritized):**
        1.  Look for "No", "Cancel", "Dismiss", "Close", or an "X" icon/button. If found, `tap()` it.
        2.  If the above are not present, and the pop-up is clearly an error message or an unwanted interruption (like a voice search error when you intended text input), the safest general way to try and dismiss it is `press_back()`. **AVOID tapping "Try again" or similar options on error pop-ups unless you intend to retry the failed operation (e.g., a genuine voice search attempt that failed).**
        3.  If it's a necessary permission request (e.g., app needs location to show nearby places and your task requires it) or a simple confirmation, then `tap()` the affirmative option ("Allow", "OK", "Yes", "Only this time").
    - **Observe:** After attempting dismissal, check if the pop-up is gone.
**MANDATORY Sequence for Text Input (e.g., Search Bars, URL Bars, Form Fields):**
Failure to follow this sequence will likely lead to errors or unintended behavior.

1.  **`tap(element_number_of_text_input_area)`:**
    *   **ALWAYS** tap the specific text input area first.
    *   This ensures the field is focused and the keyboard is ready for text.
    *   Look for rectangular areas, placeholder text (e.g., "Search...", "Type URL"), or a blinking cursor.
    *   **DO NOT skip this step.**

2.  **`type_global("your desired text")`: **
    *   After tapping, use this to enter your text.

3.  **`press_enter()` (for URLs and Searches) or `tap(submit_button_element_number)` (for Forms):**
    *   **IMMEDIATELY AFTER TYPING** a URL or a search query, you **MUST** use `press_enter()` to submit it. This action navigates to the URL or performs the search.
    *   For forms, look for a "Submit", "Login", "Go", "Search" button and `tap()` its element number.
    *   **Typing alone is INSUFFICIENT. Submission is required to proceed.**

*Example for opening a website:*
Thought: I need to open example.com. The search bar is element 3.
Action: tap(3)
Summary: Tapped the search bar.
Thought: Now I will type the URL.
Action: type_global("example.com")
Summary: Typed "example.com" into the search bar.
Thought: Now I must press enter to navigate to the website.
Action: press_enter()
Summary: Pressed enter to navigate to example.com.

**AVOID TAPPING ADJACENT ICONS:**
Input fields often have icons like a Microphone (🎤) or Camera/Lens (📷).
**Unless the task *explicitly* requires voice input or using the camera/lens feature, AVOID tapping these icons.**
Focus on tapping the main text area.
If a voice prompt (like "Didn't catch that") appears unexpectedly after you tried to type or press enter, it means you likely didn't tap the text field correctly first, or the field wasn't focused for keyboard input. In this case:
    1. Dismiss the voice error (e.g., `press_back()` or tapping a "Try again" / "Cancel" button).
    2. **Crucially, `tap()` the main text area of the search bar again.**
    3. Re-attempt `type_global()`.
    4. `press_enter()`.

- **Avoiding Repetitive Ineffective Actions:**
    - **If an action was judged "INEFFECTIVE" by reflection (UI didn't change as expected) or "CONTINUE" (but didn't achieve the sub-goal), DO NOT immediately repeat the exact same action on the exact same element.**
    - **Re-evaluate:** Why did it fail? Did you tap an icon instead of a text field? Was a pop-up present? Did you forget to `press_enter()`? Is the element not what you thought?
    - **Try a different approach:** Tap a different part of the target element, try a different element, or use `press_back()` if stuck.

- Finding and Opening Apps: (Less relevant if app is launched directly, but kept for VLM's general knowledge)
    # ... (previous content for this hint) ...

- Element Not Visible (General Scrolling): If a target UI element isn't on screen, try `swipe_screen("up", "medium")` or `swipe_screen("down", "medium")`.
- Adding New Items / Creating Content: Look for "+" icons, or "Add", "New", "Create" buttons.
- Closing an App: Use `press_app_switch()`, then `swipe_element(app_card_number, "up", "medium")` or tap a "Clear all" button.
- Notifications: Use `open_notifications()` to open, and `close_notifications()` or `press_back()` to close.
- General Navigation: `press_back()` for previous screen, `press_home()` for home screen.
- Task Completion: If your current objective <mode_specific_goal_or_task> is fully achieved, use `FINISH`.
**MANDATORY Sequence for Text Input (e.g., Search Bars, URL Bars, Form Fields):**
Failure to follow this sequence will likely lead to errors or unintended behavior.

1.  **`tap(element_number_of_text_input_area)`:**
    *   **ALWAYS** tap the specific text input area first.
    *   This ensures the field is focused and the keyboard is ready for text.
    *   Look for rectangular areas, placeholder text (e.g., "Search...", "Type URL"), or a blinking cursor.
    *   **DO NOT skip this step.**

2.  **`type_global("your desired text")`: **
    *   After tapping, use this to enter your text.

3.  **`press_enter()` (for URLs and Searches) or `tap(submit_button_element_number)` (for Forms):**
    *   **IMMEDIATELY AFTER TYPING** a URL or a search query, you **MUST** use `press_enter()` to submit it. This action navigates to the URL or performs the search.
    *   For forms, look for a "Submit", "Login", "Go", "Search" button and `tap()` its element number.
    *   **Typing alone is INSUFFICIENT. Submission is required to proceed.**

*Example for opening a website:*
Thought: I need to open example.com. The search bar is element 3.
Action: tap(3)
Summary: Tapped the search bar.
Thought: Now I will type the URL.
Action: type_global("example.com")
Summary: Typed "example.com" into the search bar.
Thought: Now I must press enter to navigate to the website.
Action: press_enter()
Summary: Pressed enter to navigate to example.com.

**AVOID TAPPING ADJACENT ICONS:**
Input fields often have icons like a Microphone (🎤) or Camera/Lens (📷).
**Unless the task *explicitly* requires voice input or using the camera/lens feature, AVOID tapping these icons.**
Focus on tapping the main text area.
If a voice prompt (like "Didn't catch that") appears unexpectedly after you tried to type or press enter, it means you likely didn't tap the text field correctly first, or the field wasn't focused for keyboard input. In this case:
    1. Dismiss the voice error (e.g., `press_back()` or tapping a "Try again" / "Cancel" button).
    2. **Crucially, `tap()` the main text area of the search bar again.**
    3. Re-attempt `type_global()`.
    4. `press_enter()`.
**Interacting with Time Pickers / Number Inputs:**
- **Distinguish Visual Numbers from Element Labels:** When setting a time like "7:30", you need to tap the part of the UI that visually represents "7" (for the hour) or "30" (for the minutes).
- **Do NOT simply `tap(7)` if "7" is an element label unless that specific labeled element IS the visual representation of the number 7 you want to select.**
- **Observe Carefully:** Look at the screenshot. If the clock face shows numbers, or there are buttons for "+/-" hours/minutes, identify the correct *visual target*.
- **Describe Your Target:** In your "Thought" process, if you intend to select the hour "7", state "I need to tap the visual number 7 on the clock face/picker, which corresponds to element label X (if it's labeled)."
- **If a visual number (e.g., "7" on a clock) is NOT labeled as an interactive element, you might not be able to tap it directly. Look for other ways to set the time, like:
    - Tapping a text input field for the hour and then using `type_global("7")`.
    - Tapping "+" or "-" buttons until the desired hour is shown.
    - Swiping on a clock hand (if applicable, though swiping specific parts of a clock is complex for this agent).**

**Example for setting time to 7:**
Observation: The screen shows a time picker. The number 7 is visible on the hour selection part. Element 12 is a button labeled "+" for hours. Element 15 is the visual representation of the number "7" on the hour dial.
Thought (Option 1 - direct tap if 7 is interactive): I need to set the hour to 7. The visual number 7 on the dial is element 15. I will tap element 15.
Action: tap(15)
Summary: Tapped the number 7 on the hour dial.

Thought (Option 2 - using + button): I need to set the hour to 7. The current hour is 5. Element 12 is the "+" button for hours. I will tap element 12 twice.
Action: tap(12)
Summary: Tapped the + button for hours.
(Next round, VLM would observe current hour is 6, and tap(12) again)

Thought (Option 3 - typing if there's an input field for hours, e.g. element 10): I see a text input field for hours (element 10). I will tap it and type "7".
Action: tap(10)
Summary: Tapped the hour input field.
(Next round)
Action: type_global("7")
Summary: Typed "7" for the hour.


Available Functions:
1.  tap(element: eX)
2.  type_global(text_to_input: str)
3.  long_press(element: int)
4.  swipe_element(element: int, direction: str, distance: str)
5.  swipe_screen(direction: str, distance: str)
6.  press_back()
7.  press_home()
8.  press_enter()
9.  press_delete()
10. open_notifications()
11. close_notifications() # Added this based on your previous prompts
12. press_app_switch()
13. grid()
14. FINISH

Output Format (Strictly follow this):
<output_format_placeholder>
"""

# Define the specific output formats for task-driven vs. exploration mode
task_mode_output_format = """Observation: <Your detailed observation of the current screen, noting relevant UI elements, their labels, and any provided documentation. How does the screen relate to the task?>
Thought: <Your step-by-step reasoning. What is the immediate sub-goal to achieve the overall task? Which function is most appropriate and why? Which element (if any) is the target of this specific action? What parameters are needed?>
Action: <The single function call you choose. Example: tap(1) or type_global("search query") or press_home() or FINISH>
Summary: <A brief human-readable summary of THE ACTION YOU JUST CHOSE. Example: "Tapped the settings icon.", "Typed 'pizza' into the search bar.", "Navigated to the home screen.">"""

exploration_mode_output_format = """ChosenSubTask: <The new specific sub-task you decided to explore to understand the app better. Example: "Try to find and open the user profile page." or "See what options are in the main settings menu." or "Attempt to use the primary search feature with 'test query'.">
Observation: <Your detailed observation of the current screen relevant to the ChosenSubTask.>
Thought: <Your step-by-step reasoning for the ChosenSubTask and the action to achieve it. Why is this a good feature to explore next?>
Action: <The single function call for the ChosenSubTask.>
Summary: <A brief human-readable summary of THE ACTION YOU JUST CHOSE for the ChosenSubTask.>"""

# --- TEMPLATES FOR DIFFERENT MODES ---

task_template = core_interaction_template.replace(
    "<mode_specific_goal_or_task>", "<task_description>"
).replace(
    "<explored_features_history>", "N/A" # Not used in direct task mode
).replace(
    "<output_format_placeholder>", task_mode_output_format
)

app_exploration_task_template = core_interaction_template.replace(
    "<mode_specific_goal_or_task>", "Your goal is to explore the app: <app_context_description>. Current focus: <current_exploration_focus_or_sub_task>"
).replace(
    "<output_format_placeholder>", exploration_mode_output_format
)


# --- INITIAL INPUT ANALYSIS ---
initial_input_analysis_template = """You are an intelligent assistant helping an Android agent.
You will receive a user's input. Your tasks are:
1. Determine if the input is a specific TASK for the agent to perform, or a general DESCRIPTION of an app/scenario for exploration.
2. If it's a TASK, clearly restate the task. The task should be actionable.
3. If it's a DESCRIPTION, identify the primary app or type of app being described (e.g., "a web browser", "a social media app", "the YouTube app"). Then, suggest 1-2 initial, simple, and distinct exploration goals or sub-tasks the agent could try first. For example, if it's a browser, an initial goal could be "Try opening a common website like google.com" or "Explore the settings menu".

User Input: "<user_input_text>"

Output Format (Strictly follow this):
InputType: <TASK or DESCRIPTION>
IdentifiedAppContext: <Restated task if TASK, or App type/name if DESCRIPTION. Example: "Task: Search for 'cats' on YouTube and play the first video." or "App Context: This appears to be the YouTube app." or "App Context: This is a general web browser.">
InitialGoals: <"N/A" if TASK. If DESCRIPTION, list 1-2 bulleted initial exploration goals. Example:
- Try searching for 'funny cat videos'.
- Explore the 'Shorts' tab.
>
"""

# --- REFLECTION TEMPLATE (remains largely the same, ensure <task_desc> is filled appropriately) ---
self_explore_reflect_template = """You are reflecting on an action performed by an Android agent.
The overall task context (or current exploration focus) is: <task_desc>

Action Details:
- Action Type: <action_type>
- Element Involved: <element_details> (e.g., "element 5 (UID: com.example/button_id)", "N/A" for global actions)
- Agent's Intended Summary for this action: <last_act_summary>

You are given screenshots before and after this action.
Your goal is to:
1. Evaluate if the action was correct and helpful for the overall task/exploration focus.
2. If a specific UI element was involved, provide concise documentation for its function *based on the observed change*. (e.g., "Opens user profile", "Submits the form", "Activates voice search").

Decision Categories:
1.  BACK: The action led to an irrelevant page, an error, or got stuck. The agent should go back.
2.  INEFFECTIVE: The action made no meaningful change to the UI, or did not achieve the <last_act_summary>.
3.  CONTINUE: The action changed the UI, but not as intended by <last_act_summary> OR it doesn't clearly help the <task_desc> (and BACK is not appropriate). The agent should try something else.
4.  SUCCESS: The action successfully moved the <task_desc> forward as intended by <last_act_summary>, or successfully explored a feature as intended.

Output Format (Strictly follow this):
Decision: <BACK, INEFFECTIVE, CONTINUE, or SUCCESS>
Thought: <Your reasoning for this decision, considering the screen changes, <last_act_summary>, and <task_desc>.
If INEFFECTIVE, explain why you think it failed (e.g., "tapped wrong element", "pop-up blocked action").
**Specifically, if the <action_type> was `type_global` or `press_enter` and the intended target was a text field:
- Did the agent `tap()` the text field immediately before this action in a previous step?
- If not, the action was likely to fail or cause unexpected behavior (like activating voice input). Note this as a reason for INEFFECTIVE or CONTINUE.
- If `type_global` was used but no `press_enter()` followed for a URL/search, note that the step is incomplete.**
If the <action_type> was `tap` on a text field, was it followed by `type_global` and then `press_enter` in subsequent steps?
If `type_global` resulted in an unexpected voice prompt or error, explicitly state that the agent should have `tap()`ped the target text field first.
*If the <action_type> was `type_global` for a URL into a search/URL bar:
- Did the agent immediately follow with `press_enter()` in the next action?
- If not, and the goal was to NAVIGATE to the URL, the current step is INCOMPLETE, even if search suggestions appeared. The VLM should be guided to `press_enter()`. Decision should likely be CONTINUE.**
If `type_global` was used but no `press_enter()` followed for a URL/search, note that the step is incomplete.>
Documentation: <Generated documentation for the UI element if one was directly targeted by the action and the decision is not INEFFECTIVE. If no specific element was targeted, or documentation is not clear from this single action, output "N/A".>
"""

# --- GRID TEMPLATE (remains largely the same) ---
task_template_grid = """You are controlling a smartphone using a grid overlay on the screen.
# ... (rest of task_template_grid, ensure Available Functions are consistent) ...
Global Actions (also available in grid mode, do not take area/subarea):
4.  type_global(text_to_input: str)
5.  press_back()
6.  press_home()
7.  press_enter()
8.  press_delete()
9.  open_notifications()
10. close_notifications() # Added
11. press_app_switch()
12. FINISH: If the task <task_description> is completed.
13. exit_grid(): If you want to return to the labeled element mode for the next action.
# ...
"""
