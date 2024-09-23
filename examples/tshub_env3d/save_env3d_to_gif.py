'''
@Author: WANG Maonan
@Date: 2024-07-21 04:40:41
@Description: 将传感器的图片保存为 gif 用于展示
@LastEditTime: 2024-07-21 04:56:19
'''
import os
import imageio
from PIL import Image
from tshub.utils.get_abs_path import get_abs_path

path_convert = get_abs_path(__file__)

def create_gif(image_dir, output_gif_path, gif_width=360, fps=10, palettesize=128):
    """
    Create a gif from a sequence of images in a directory.

    :param image_dir: Directory containing the images.
    :param output_gif_path: Path to save the output gif.
    :param gif_width: Width of the gif; height will be scaled proportionally.
    :param fps: Frames per second for the gif animation.
    :param palettesize: Number of colors in the palette.
    """
    # Retrieve a list of image file names, sorted numerically
    image_files = sorted(
        [f for f in os.listdir(image_dir) if f.endswith('.png')],
        key=lambda x: int(os.path.splitext(x)[0])
    )

    # Initialize a list to hold the image data
    images_for_gif = []

    # Iterate over the image files
    for filename in image_files:
        # Open the image
        with Image.open(os.path.join(image_dir, filename)) as img:
            # Optionally resize the image
            width_percent = (gif_width / float(img.size[0]))
            height_size = int((float(img.size[1]) * float(width_percent)))
            img_resized = img.resize((gif_width, height_size), Image.Resampling.LANCZOS)
            
            # Append the image data to the list
            images_for_gif.append(img_resized)

    # Use imageio.mimsave to save the images as a gif
    imageio.mimsave(output_gif_path, images_for_gif, fps=fps, palettesize=palettesize)

def walk_directories(root_dir) -> None:
    """
    Walk through all directories in the root directory and create GIFs from images.

    :param root_dir: Root directory to start walking through.
    """
    for subdir, dirs, files in os.walk(root_dir):
        if any(file.endswith('.png') for file in files):
            camera_type = subdir.split('/')[-1]
            element_id = subdir.split('/')[-2]

            gif_path = os.path.join(subdir, '../../gifs/', f'{element_id}_{camera_type}.gif')
            create_gif(subdir, gif_path)
            print(f'{element_id}_{camera_type}.gif 保存成功!')

# Example usage:
walk_directories(path_convert('./env3d_images/'))

