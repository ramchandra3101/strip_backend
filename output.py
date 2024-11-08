import sys
import cv2
import numpy as np
from PIL import Image, ImageFilter
import os
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.integrate import trapezoid
from PIL import ImageEnhance

def detect_arrow_direction(image):
      image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
      hsv_image = cv2.cvtColor(image_cv, cv2.COLOR_BGR2HSV)
      lower_red1 = np.array([0, 50, 50])
      upper_red1 = np.array([10, 255, 255])
      lower_red2 = np.array([160, 50, 50])
      upper_red2 = np.array([180, 255, 255])
      mask_red1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
      mask_red2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
      mask_red = mask_red1 + mask_red2
      contours, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      largest_area = 0
      largest_contour = None
      for contour in contours:
          area = cv2.contourArea(contour)
          if area > largest_area:
              largest_area = area
              largest_contour = contour

      if largest_contour is not None:
        x, y, w, h = cv2.boundingRect(largest_contour)
        # Calculate the center x-coordinate of the bounding box
        center_x = x + w // 2

      # Flip the image if the red area is not on the left side (i.e., center_x > half the image width)
        if center_x > image_cv.shape[1] // 2:
            image_flipped = cv2.rotate(image_cv, cv2.ROTATE_180)
        else:
            image_flipped = image_cv

      return image_flipped

def straighten_and_crop_transparent(image):
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    _, _, _, alpha = cv2.split(image)
    mask = cv2.threshold(alpha, 0, 255, cv2.THRESH_BINARY)[1]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        cnt = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(cnt)
        angle = rect[2]
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        _, _, _, alpha = cv2.split(rotated)
        coords = cv2.findNonZero(alpha)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            cropped = rotated[y:y+h, x:x+w]
            if h > w:
                cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
            b, g, r, _ = cv2.split(cropped)
            cropped_rgb = cv2.merge((b, g, r))
            return cropped_rgb
        else:
            print("No non-transparent pixels found in the image.")
            return None
    else:
        print("No contours found.")
        return None
    
def process_image(image_path):
    with Image.open(image_path) as pil_img:
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
        straightened_image = straighten_and_crop_transparent(cv_img)
        straight_image = cv2.cvtColor(straightened_image, cv2.COLOR_BGR2RGB)

        
        if straight_image is not None:
            correct_image = detect_arrow_direction(straight_image)
            

            output_path = os.path.splitext(image_path)[0] + '_processed.png'
            cv2.imwrite(output_path, cv2.cvtColor(correct_image, cv2.COLOR_RGB2BGR))
            return correct_image, output_path  # Return the processed image for further use
        else:
            print("Processing failed.")
            return None

def crop_and_display(image, image_path):
    img = Image.fromarray(image)
    width, height = img.size
    mid = width // 2
    upper = 20
    left = (2*width)/4.8
    right = mid + width//4
    lower = height
    lower = img.height-30

    cropped_img = img.crop((left, upper, right, lower))
    cropped_img = ImageEnhance.Contrast(cropped_img).enhance(2)
    cropped_path = os.path.splitext(image_path)[0] + '_cropped.png'
    cropped_img.save(cropped_path)
    return cropped_img , cropped_path

def convert_to_bw_and_plot(cropped_img, output_folder):
    img = cropped_img.convert('L')
    img = img.filter(ImageFilter.GaussianBlur(1))
    threshold = 220
    bw_img = img.point(lambda x: 255 if x > threshold else 0, '1')

    bw_array = np.array(bw_img)
    signal_array = 1 - bw_array / 255
    signal = np.mean(signal_array, axis=0)
   
    
    mid_point = len( signal) // 2
    peaks, _ = find_peaks( signal, height=0.8)
    left_peak = peaks[peaks < mid_point]
    first_left_peak = left_peak[-1] if len(left_peak) > 0 else None

    # Find the first peak to the right of the mid-point
    right_peak = peaks[peaks > mid_point]
    first_right_peak = right_peak[0] if len(right_peak) > 0 else None

    # Get the intensity values at the first left and right peaks
    

    Control_line_area = trapezoid(signal[max(0, first_left_peak - 10):first_left_peak + 10]) if first_left_peak is not None else 0
    Test_line_area = trapezoid(signal[first_right_peak - 10:first_right_peak + 10]) if first_right_peak is not None else 0

    print("Control line area:", Control_line_area)
    print("Test line area:", Test_line_area)
    

    plt.figure(figsize=(10, 2))
    plt.plot( signal, label= 'intensity')
    plt.legend()
    plt.grid(True)

    #saving the plot in the same folder of input image

    plot_output_path = os.path.join(output_folder, 'intensity_plot.png')
    plt.savefig(plot_output_path)
    plt.close()

    return plot_output_path, Control_line_area, Test_line_area
    

