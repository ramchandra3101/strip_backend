
import os
from PIL import Image
from carvekit.api.interface import Interface
from carvekit.ml.wrap.fba_matting import FBAMatting
from carvekit.ml.wrap.tracer_b7 import TracerUniversalB7
from carvekit.pipelines.postprocessing import MattingMethod
from carvekit.pipelines.preprocessing import PreprocessingStub
from carvekit.trimap.generator import TrimapGenerator

# # Initialize AWS S3 client
# s3_client = boto3.client('s3')

# # Function to download image from S3
# def download_image_from_s3(bucket_name, object_key, download_path):
#     s3_client.download_file(bucket_name, object_key, download_path)
#     print(f"Downloaded {object_key} from bucket {bucket_name} to {download_path}")

# # Function to upload image to S3
# def upload_image_to_s3(bucket_name, object_key, file_path):
#     s3_client.upload_file(file_path, bucket_name, object_key)
#     print(f"Uploaded {file_path} to bucket {bucket_name} as {object_key}")

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


#     # Set file paths
#     input_image_path = "/tmp/input_image.jpg"  # Download location
#     processed_image_path = "/tmp/processed_image_no_bg.png"  # Processed image location
    
#     # Step 1: Download the image from S3
#     download_image_from_s3(bucket_name, object_key, input_image_path)
    
#     # Step 2: Process the image (remove background)
#     process_image(input_image_path, processed_image_path)
    
#     # Step 3: Define new S3 object key for the processed image
#     object_key_no_bg = object_key.replace(".jpg", "_no_bg.png")  # Modify the object key
    
#     # Step 4: Upload the processed image back to S3
#     upload_image_to_s3(bucket_name, object_key_no_bg, processed_image_path)

# Usage
# if __name__ == "__main__":
#     bucket_name = 'striplens'
#     object_key = '20240929_144041.jpg'  # S3 object key (path to image in S3)
    
#     handle_image_processing(bucket_name, object_key)
