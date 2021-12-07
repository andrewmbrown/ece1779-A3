# from wand.image import Image  # imagemagik library is called wand in python
import os 
from PIL import Image, ImageFilter
def image_transform(img_path, post_transform_path, mode):
    """
    Function to apply image transformations using imagemagik library
    3 transformations: blur, shade, spread

    input:  img_path: string specifying path to image on AWS machine
            mode: int specifying which transformation to apply
                  0 = blur, 1 = shade, 2 = spread, 3 = 50 x 50 thumbnail

    output: wand Image object with transformation applied
    """
    with Image.open(img_path) as img:  # create a wand image object
        if mode == 0: out = img.filter(filter=ImageFilter.BLUR)
        elif mode == 1: out = img.filter(filter=ImageFilter.BLUR)
        elif mode == 2: out = img.filter(filter=ImageFilter.BLUR)
        elif mode == 3: out = img.filter(filter=ImageFilter.BLUR)
        else: 
            print("incorrect input")
            return -1

        # in case image transformation does not work, throw exeception

        try:
            img.save(post_transform_path)
            return out
        except:
            print("image transform failed!")
            return -1
 