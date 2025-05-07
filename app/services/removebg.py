
import os
from PIL import Image
from carvekit.api.interface import Interface
from carvekit.ml.wrap.fba_matting import FBAMatting
from carvekit.ml.wrap.tracer_b7 import TracerUniversalB7
from carvekit.pipelines.postprocessing import MattingMethod
from carvekit.pipelines.preprocessing import PreprocessingStub
from carvekit.trimap.generator import TrimapGenerator

# Initialize the CarveKit model
def initialize_carvekit():
    seg_net = TracerUniversalB7(device='cpu', batch_size=1)
    fba = FBAMatting(device='cpu', input_tensor_size=2048, batch_size=1)
    trimap = TrimapGenerator()
    preprocessing = PreprocessingStub()
    postprocessing = MattingMethod(matting_module=fba, trimap_generator=trimap, device='cpu')
    
    interface = Interface(pre_pipe=preprocessing, post_pipe=postprocessing, seg_pipe=seg_net)
    return interface

# Process the image to remove background
def process_image(input_image_path):
    interface = initialize_carvekit()
    
    image = Image.open(input_image_path)
    processed_image = interface([image])[0]

    outputPath= os.path.splitext(input_image_path)[0]+'_no_bg.png'
    processed_image.save(outputPath)
    #print(f"Saved processed image to {outputPath}")
    return outputPath

    # processed_image.save(output_image_path)
    # print(f"Saved processed image to {output_image_path}")

# # Main function to download, process, and upload image
def handle_image_processing(inputPath):
    outputPath = process_image(inputPath)
    return outputPath
