import base64
import cv2
import pyshine as ps
from colorama import Fore, Style

def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    else:
        print(text)
    print(Style.RESET_ALL)

def draw_bbox_multi(img_path, output_path, elem_list, record_mode=False, dark_mode=False):
    img = cv2.imread(img_path)
    count = 0
    for elem in elem_list:
        count += 1
        tl, br = elem.bbox[0], elem.bbox[1]
        color = (0, 0, 0)
        if record_mode:
            if elem.attrib == "clickable":
                color = (255, 0, 0)
            elif elem.attrib == "focusable":
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)
        else:
            if dark_mode:
                color = [255, 255, 255]  # White for text on dark mode
                text_background_color = [80, 80, 80] # Dark gray for background
            else:
                color = [0, 0, 0] # Black for text on light mode
                text_background_color = [200, 200, 200] # Light gray for background

        # Put text with background
        try:
            img = ps.putBText(img, str(count), text_offset_x=(tl[0] + br[0]) // 2 - 5, text_offset_y=(tl[1] + br[1]) // 2 - 5,
                              vspace=5, hspace=5, font_scale=1, thickness=2, background_RGB=text_background_color,
                              text_RGB=color, font=cv2.FONT_HERSHEY_SIMPLEX)
        except Exception as e:
            print_with_color(f"Error drawing text with pyshine: {e}", "red")
            # Fallback to simple text drawing if pyshine fails
            # cv2.putText(img, str(count), ((tl[0] + br[0]) // 2 - 10, (tl[1] + br[1]) // 2 + 10), 
            #             cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    cv2.imwrite(output_path, img)
    return img

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8') 