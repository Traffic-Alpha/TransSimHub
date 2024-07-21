'''
@Author: WANG Maonan
@Date: 2024-07-21 05:40:41
@Description: 合并 gif, 用于文档的书写
@LastEditTime: 2024-07-22 01:07:42
'''
import imageio
from PIL import Image

def merge_gifs_in_grid(gif_paths, output_path, gifs_per_row, spacing=10) -> None:
    """
    可以将多个 gif 文件合并。
    Merge multiple GIF files into a grid with white spacing between them.

    :param gif_paths: List of file paths to the GIFs.
    :param output_path: File path to save the merged GIF.
    :param gifs_per_row: Number of GIFs to place in each row.
    :param spacing: The white space between GIFs in pixels.
    """
    # Read in all the GIFs and store as a list of frames
    gifs = [imageio.mimread(gif) for gif in gif_paths]
    
    # Assuming all GIFs are the same size, get the dimensions
    gif_width, gif_height = gifs[0][0].shape[1], gifs[0][0].shape[0]
    
    # Calculate the dimensions of the full grid
    num_rows = (len(gifs) + gifs_per_row - 1) // gifs_per_row
    full_width = gif_width * gifs_per_row + spacing * (gifs_per_row - 1)
    full_height = gif_height * num_rows + spacing * (num_rows - 1)
    
    # Create a new list to hold the merged frames
    merged_frames = []
    
    # For each frame index
    for frame_index in range(len(gifs[0])):
        # Create a new image with the full dimensions and white background
        new_frame = Image.new('RGBA', (full_width, full_height), 'WHITE')
        
        # Paste each frame into the correct position
        for i, gif in enumerate(gifs):
            row, col = divmod(i, gifs_per_row)
            x = col * (gif_width + spacing)
            y = row * (gif_height + spacing)
            frame = gif[frame_index] if frame_index < len(gif) else gif[-1]  # Loop last frame if shorter
            pil_frame = Image.fromarray(frame)
            new_frame.paste(pil_frame, (x, y))
        
        # Append the new frame to the list
        merged_frames.append(new_frame)
    
    # Save the frames as a new GIF
    merged_frames[0].save(output_path, save_all=True, append_images=merged_frames[1:], loop=0, duration=gifs[0][0].meta['duration'])

# Example usage:
# merge_gifs_in_grid([
#         path_convert('./vehicle/29257863#2__0__ego.0_front_left_vehicle.gif'), 
#         path_convert('./vehicle/29257863#2__0__ego.0_front_vehicle.gif'), 
#         path_convert('./vehicle/29257863#2__0__ego.0_front_right_vehicle.gif'), 

#         path_convert('./vehicle/29257863#2__0__ego.0_back_left_vehicle.gif'), 
#         path_convert('./vehicle/29257863#2__0__ego.0_back_vehicle.gif'), 
#         path_convert('./vehicle/29257863#2__0__ego.0_back_right_vehicle.gif'), 
#     ], 
#     path_convert('./vehicle_ego2_vehicle.gif'), 
#     gifs_per_row=3, 
#     spacing=3
# )
