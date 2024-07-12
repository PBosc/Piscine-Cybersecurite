import sys
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def get_exif_data(img):
    try:
        exif_data = img._getexif()
        if exif_data is not None:
            exif_info = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name in [
                    'Make', 'Model', 'DateTimeOriginal', 'ExposureTime',
                    'FNumber', 'ISOSpeedRatings', 'FocalLength',
                    'Orientation', 'Software', 'FileSize', 'ExifImageWidth', 'ExifImageHeight',
                    'ColorSpace', 'Compression', 'Artist', 'GPSInfo'
                ]:
                    if tag_name == 'GPSInfo':
                        gps_data = {}
                        for gps_tag, gps_value in value.items():
                            gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                            gps_data[gps_tag_name] = gps_value
                        exif_info.update(gps_data)
                    else:
                        exif_info[tag_name] = value
            return exif_info
        else:
            return None
    except Exception as e:
        print(f"Error processing EXIF data: {e}")
        return None

def get_image_metadata(image_path):
    try:
        with Image.open(image_path) as img:
            metadata = {
                "Format": img.format,
                "Mode": img.mode,
                "Size": img.size,
            }
            
            # Extract EXIF data if available
            if img.format in ["JPEG", "TIFF"]:
                exif_data = get_exif_data(img)
                if exif_data:
                    metadata.update(exif_data)
                else:
                    print(f"No EXIF data found in {image_path}.")
            # For PNG, BMP, GIF, extract basic info
            elif img.format in ["BMP", "GIF"]:
                pass
            elif img.format == "PNG":
                exif_data = get_exif_data(img)
                if exif_data:
                    metadata.update(exif_data)
                else:
                    metadata.update({"Exif Data": img._getexif()})
                pass
            else:
                print(f"Unsupported image format: {img.format}")
            
        return metadata
    except OSError as e:
        print(f"Error opening or reading {image_path}: {e}")
        return None
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return metadata

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ./scorpion.py image1.jpg image2.png ...")
        sys.exit(1)
    
    image_paths = sys.argv[1:]
    for image_path in image_paths:
        print(f"Processing {image_path}...")
        metadata = get_image_metadata(image_path)
        if metadata:
            print("Metadata:")
            for key, value in metadata.items():
                print(f"{key}: {value}")
            print()
        else:
            print(f"Failed to extract metadata from {image_path}.")
        print("-" * 50)

if __name__ == "__main__":
    main()
