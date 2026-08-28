

import os
from pyspark.sql import SparkSession
import sys
# Point to your newly created binary paths
os.environ["HADOOP_HOME"] = r"C:\\hadoop-3.3.6"
sys.path.append(r"C:\\hadoop-3.3.6\\bin")

spark = SparkSession.builder \
    .appName("ImageProcessing") \
    .config("spark.driver.memory", "8g") \
    .config("spark.executor.memory", "8g") \
    .getOrCreate()
# Load images from storage

import os
from pyspark.sql import SparkSession

# 1. Standard Python loop to find paths (safely avoids the Hadoop crash)
image_folder = r"D:\\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\images"
image_paths = []

for root, dirs, files in os.walk(image_folder):
    for file in files:
        if file.lower().endswith(".jpg"):
            # Format cleanly for PySpark compatibility
            full_path = os.path.join(root, file).replace("\\", "/")
            # Use the file:/// protocol and 'f' for Windows paths
            image_paths.append(f"file:///{full_path}")

# 2. Feed the list directly into the lighter binary file system 
# (Processing lists skips Hadoop's folder directory tree indexing)
if image_paths:
    # Use binaryFile or format("image")
    images_df = spark.read.format("binaryFile").load(image_paths)
    print(f"Successfully loaded {images_df.count()} images!")
else:
    print("No .jpg files found in the directory.")

# Save the processed data out to a permanent local directory
output_parquet_path = r"D:\\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\processed_images.parquet"

images_df.write.mode("overwrite").parquet(output_parquet_path)
print("Saved successfully!")

spark.stop()