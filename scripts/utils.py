import base64
import cv2
import numpy as np
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

def putBText(img,text,text_offset_x=20,text_offset_y=20,vspace=10,hspace=10, font_scale=1.0,background_RGB=(228,225,222),text_RGB=(1,1,1),font = cv2.FONT_HERSHEY_DUPLEX,thickness = 2,alpha=0.6,gamma=0):
	"""
    Inputs:
    img: cv2 image img
    text_offset_x, text_offset_x: X,Y location of text start
    vspace, hspace: Vertical and Horizontal space between text and box boundries
    font_scale: Font size
    background_RGB: Background R,G,B color
    text_RGB: Text R,G,B color
    font: Font Style e.g. cv2.FONT_HERSHEY_DUPLEX,cv2.FONT_HERSHEY_SIMPLEX,cv2.FONT_HERSHEY_PLAIN,cv2.FONT_HERSHEY_COMPLEX
          cv2.FONT_HERSHEY_TRIPLEX, etc
    thickness: Thickness of the text font
    alpha: Opacity 0~1 of the box around text
    gamma: 0 by default

    Output:
    img: CV2 image with text and background
	"""
	R,G,B = background_RGB[0],background_RGB[1],background_RGB[2]
	text_R,text_G,text_B = text_RGB[0],text_RGB[1],text_RGB[2]
	(text_width, text_height) = cv2.getTextSize(text, font, fontScale=font_scale, thickness=thickness)[0]
	x, y, w, h = text_offset_x, text_offset_y, text_width , text_height
	crop = img[y-vspace:y+h+vspace, x-hspace:x+w+hspace]
	white_rect = np.ones(crop.shape, dtype=np.uint8)
	b,g,r = cv2.split(white_rect)
	rect_changed = cv2.merge((B*b,G*g,R*r))


	res = cv2.addWeighted(crop, alpha, rect_changed, 1-alpha, gamma)
	img[y-vspace:y+vspace+h, x-hspace:x+w+hspace] = res

	cv2.putText(img, text, (x, (y+h)), font, fontScale=font_scale, color=(text_B,text_G,text_R ), thickness=thickness)
	return img

def draw_bbox_multi(img_path, output_path, elem_list, record_mode=False, dark_mode=False):
    img = cv2.imread(img_path)
    if img is None: # ADD THIS CHECK
        print_with_color(f"Error: Could not read image at {img_path}", "red") # ADD THIS
    # Decide how to handle: return or try to create a blank image, or just skip drawing
    # For now, let's just return to avoid further errors if img is None
        return None
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
        try:
            img = putBText(img, str(count), text_offset_x=(tl[0] + br[0]) // 2 - 5, text_offset_y=(tl[1] + br[1]) // 2 - 5,
                              vspace=5, hspace=5, font_scale=1, thickness=2, background_RGB=text_background_color,
                              text_RGB=color, font=cv2.FONT_HERSHEY_SIMPLEX)
        except Exception as e:
            print_with_color(f"Error drawing text with pyshine: {e}", "red")
            print_with_color("Falling back to cv2.putText", "yellow")
            # Fallback to simple text drawing
            # Simple background rectangle for cv2.putText
    # (text_size, _) = cv2.getTextSize(str(count), cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
    # cv2.rectangle(img, (label_x, label_y - text_size[1] - 5), (label_x + text_size[0] + 5, label_y + 5), text_background_color, -1)
    cv2.imwrite(output_path, img)
    return img

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8') 