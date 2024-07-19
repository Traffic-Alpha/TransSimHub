'''
@Author: WANG Maonan
@Date: 2024-07-09 01:43:43
@Description: 展示 sensor 的结果
@LastEditTime: 2024-07-09 02:02:58
'''
import cv2
import numpy as np

def show_sensor_images(images, window_name='Image window', delay=1):
    # Initialize an empty list to hold processed images
    processed_images = []
    
    # Process images or create blank ones if None
    for image in images:
        if image is None:
            # Create a blank image if None is encountered
            processed_images.append(np.zeros((600, 800, 3), dtype=np.uint8))
        else:
            # Assuming image is already in the correct format (800x600x3)
            processed_images.append(image)
    
    # Concatenate images horizontally
    concatenated_image = np.concatenate(processed_images, axis=1)
    
    # Display the concatenated image
    cv2.imshow(window_name, concatenated_image)
    key = cv2.waitKey(delay) & 255
    
    # Check for 'ESC' or 'q' key press
    if key == 27 or key == ord('q'):
        print("Pressed ESC or q, exiting")
        return True
    
    return False