# app/services/image_utils.py
import sys
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import os
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from scipy.signal import find_peaks
from scipy.integrate import trapezoid
from core.exceptions import ImageProcessingError
import logging

logger = logging.getLogger(__name__)

class ImageUtils:
    @staticmethod
    def straighten_and_crop_transparent(image):
        try:
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
                rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, 
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
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
                logger.error("No non-transparent pixels found in the image.")
                return None
            logger.error("No contours found.")
            return None
        except Exception as e:
            logger.error(f"Error in straightening image: {str(e)}")
            raise ImageProcessingError(str(e))

    @staticmethod
    def detect_arrow_direction(image):
        try:
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
                center_x = x + w // 2
                if center_x > image_cv.shape[1] // 2:
                    return cv2.rotate(image_cv, cv2.ROTATE_180)
            return image_cv
        except Exception as e:
            logger.error(f"Error in arrow detection: {str(e)}")
            raise ImageProcessingError(str(e))

    @staticmethod
    def process_image(image_path):
        try:
            with Image.open(image_path) as pil_img:
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
                straightened_image = ImageUtils.straighten_and_crop_transparent(cv_img)
                if straightened_image is not None:
                    straight_image = cv2.cvtColor(straightened_image, cv2.COLOR_BGR2RGB)
                    correct_image = ImageUtils.detect_arrow_direction(straight_image)
                    output_path = os.path.splitext(image_path)[0] + '_processed.png'
                    cv2.imwrite(output_path, cv2.cvtColor(correct_image, cv2.COLOR_RGB2BGR))
                    return correct_image, output_path
                logger.error("Processing failed.")
                return None, None
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise ImageProcessingError(str(e))

    @staticmethod
    def crop_and_display(image, image_path):
        try:
            img = Image.fromarray(image)
            width, height = img.size
            mid = width // 2
            upper = 20
            left = (2*width)/4.7
            right = mid + width//4
            lower = img.height-30

            cropped_img = img.crop((left, upper, right, lower))
            cropped_img = ImageEnhance.Contrast(cropped_img).enhance(2)
            cropped_path = os.path.splitext(image_path)[0] + '_cropped.png'
            cropped_img.save(cropped_path)
            return cropped_img, cropped_path
        except Exception as e:
            logger.error(f"Error cropping image: {str(e)}")
            raise ImageProcessingError(str(e))

    @staticmethod
    def convert_to_bw_and_plot(cropped_img, output_folder):
        try:
            img = cropped_img.convert('L')
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = img.filter(ImageFilter.GaussianBlur(1))
            img_array = np.array(img)
            img_normalized = cv2.normalize(img_array, None, 0, 255, cv2.NORM_MINMAX)
            block_size = 11
            C = 2
            img_threshold = cv2.adaptiveThreshold(img_normalized, 
                                                    255,
                                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                    cv2.THRESH_BINARY,
                                                    block_size,
                                                    C)
            signal_array = 1 - img_normalized / 255  # Use normalized image instead of binary
            signal = np.mean(signal_array, axis=0)
            window_size = 5
            smoothed_signal = np.convolve(signal, np.ones(window_size)/window_size, mode='valid')
            mid_point = len(smoothed_signal) // 2
            peaks, properties = find_peaks(smoothed_signal,
                                        height=0.3,
                                        distance=20,
                                        width=5,
                                        prominence=0.2)
            left_peak = peaks[peaks < mid_point]
            first_left_peak = left_peak[-1] if len(left_peak) > 0 else None
            right_peak = peaks[peaks > mid_point]
            first_right_peak = right_peak[0] if len(right_peak) > 0 else None

            window = 10  # Adjust window size for area calculation
            Control_line_area = trapezoid(smoothed_signal[max(0, first_left_peak - window):first_left_peak + window]) if first_left_peak is not None else 0
            Test_line_area = trapezoid(smoothed_signal[first_right_peak - window:first_right_peak + window]) if first_right_peak is not None else 0
            plt.figure(figsize=(10, 2))
            plt.plot(smoothed_signal)
            if first_left_peak is not None:
                plt.plot(first_left_peak, smoothed_signal[first_left_peak])
            if first_right_peak is not None:
                plt.plot(first_right_peak, smoothed_signal[first_right_peak])
            plt.legend()
            plt.grid(True)
            plot_output_path = os.path.join(output_folder, 'intensity_plot.png')
            plt.savefig(plot_output_path)
            plt.close()
            return plot_output_path, Control_line_area, Test_line_area
        except Exception as e:
            logger.error(f"Error in BW conversion and plotting: {str(e)}")
            raise ImageProcessingError(str(e))