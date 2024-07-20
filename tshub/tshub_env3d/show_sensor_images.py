'''
@Author: WANG Maonan
@Date: 2024-07-09 01:43:43
@Description: 展示 sensor 的结果
@LastEditTime: 2024-07-21 02:04:01
'''
import cv2
import numpy as np

def convert_rgb_to_bgr(image):
    # Convert an RGB image to BGR
    return image[:, :, ::-1]

def show_sensor_images(images, scale=1.0, images_per_row=3, window_name='Image window', delay=1):
    # Initialize an empty list to hold processed images
    processed_images = []
    
    # Process images or create blank ones if None
    for image in images:
        if image is None:
            # Create a blank image if None is encountered
            height, width = 240, 360
            if scale != 1.0:
                height = int(height * scale)
                width = int(width * scale)
            processed_images.append(np.zeros((height, width, 3), dtype=np.uint8))
        else:
            # Assuming image is already in the correct format (800x600x3)
            if scale != 1.0:
                # Resize the image if a scaling factor is provided
                image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            bgr_image = convert_rgb_to_bgr(image)
            processed_images.append(bgr_image.copy())
    
    # Split the processed images into rows
    rows = [processed_images[i:i + images_per_row] for i in range(0, len(processed_images), images_per_row)]
    
    # Concatenate images horizontally within each row
    concatenated_rows = [np.concatenate(row, axis=1) for row in rows if row]
    
    # Make all rows the same width by padding with black images if necessary
    max_width = max(row.shape[1] for row in concatenated_rows)
    for i, row in enumerate(concatenated_rows):
        if row.shape[1] < max_width:
            padding = np.zeros((row.shape[0], max_width - row.shape[1], 3), dtype=np.uint8)
            concatenated_rows[i] = np.concatenate((row, padding), axis=1)
    
    # Concatenate rows vertically to get the final image
    final_image = np.concatenate(concatenated_rows, axis=0)
    
    # Display the final image
    cv2.imshow(window_name, final_image)
    key = cv2.waitKey(delay) & 255
    
    # Check for 'ESC' or 'q' key press
    if key == 27 or key == ord('q'):
        print("Pressed ESC or q, exiting")
        return True
    
    return False