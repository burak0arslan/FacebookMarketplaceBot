"""
Image Handler for Facebook Marketplace Bot
Handles image processing, validation, and optimization for listings
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image, ImageOps
import logging

from config import Config
from utils.logger import get_logger


class ImageHandler:
    """
    Handles image processing for Facebook Marketplace listings

    Features:
    - Image validation and format checking
    - Image resizing and optimization
    - Image format conversion
    - Batch processing
    - Error handling and logging
    """

    def __init__(self, images_folder: str = "data/images"):
        """
        Initialize ImageHandler

        Args:
            images_folder: Path to folder containing product images
        """
        self.images_folder = Path(images_folder)
        self.images_folder.mkdir(parents=True, exist_ok=True)

        self.processed_folder = self.images_folder / "processed"
        self.processed_folder.mkdir(exist_ok=True)

        self.logger = get_logger(__name__)

        # Image settings
        self.max_width = 1200
        self.max_height = 1200
        self.quality = 85
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

    def validate_image(self, image_path: str) -> Dict[str, Any]:
        """
        Validate an image file

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with validation results
        """
        image_path = Path(image_path)
        result = {
            'valid': False,
            'exists': False,
            'size_mb': 0,
            'dimensions': (0, 0),
            'format': None,
            'errors': []
        }

        try:
            # Check if file exists
            if not image_path.exists():
                result['errors'].append(f"File does not exist: {image_path}")
                return result

            result['exists'] = True

            # Check file size
            file_size = image_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            result['size_mb'] = round(size_mb, 2)

            if size_mb > Config.MAX_IMAGE_SIZE_MB:
                result['errors'].append(f"File too large: {size_mb:.1f}MB (max: {Config.MAX_IMAGE_SIZE_MB}MB)")

            # Check file extension
            if image_path.suffix.lower() not in Config.SUPPORTED_IMAGE_FORMATS:
                result['errors'].append(f"Unsupported format: {image_path.suffix}")

            # Try to open and validate image
            try:
                with Image.open(image_path) as img:
                    result['dimensions'] = img.size
                    result['format'] = img.format

                    # Check image dimensions
                    width, height = img.size
                    if width < 400 or height < 400:
                        result['errors'].append(f"Image too small: {width}x{height} (min: 400x400)")

                    if width > 4000 or height > 4000:
                        result['errors'].append(f"Image too large: {width}x{height} (max: 4000x4000)")

            except Exception as e:
                result['errors'].append(f"Cannot open image: {str(e)}")
                return result

            # If no errors, mark as valid
            result['valid'] = len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")

        return result

    def resize_and_optimize_image(self, input_path: str, output_path: str = None,
                                  max_width: int = None, max_height: int = None,
                                  quality: int = None) -> Optional[str]:
        """
        Resize and optimize an image for Facebook upload

        Args:
            input_path: Path to input image
            output_path: Path for output image (auto-generated if None)
            max_width: Maximum width (uses default if None)
            max_height: Maximum height (uses default if None)
            quality: JPEG quality (uses default if None)

        Returns:
            Path to optimized image, or None if failed
        """
        input_path = Path(input_path)
        max_width = max_width or self.max_width
        max_height = max_height or self.max_height
        quality = quality or self.quality

        try:
            self.logger.debug(f"Processing image: {input_path}")

            # Validate input image
            validation = self.validate_image(input_path)
            if not validation['exists']:
                self.logger.error(f"Input image not found: {input_path}")
                return None

            # Generate output path if not provided
            if output_path is None:
                output_path = self.processed_folder / f"optimized_{input_path.name}"
            else:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

            # Open and process image
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = background

                # Auto-rotate based on EXIF data
                img = ImageOps.exif_transpose(img)

                # Calculate new dimensions
                width, height = img.size
                if width > max_width or height > max_height:
                    # Calculate aspect ratio
                    ratio = min(max_width / width, max_height / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)

                    # Resize image
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self.logger.debug(f"Resized from {width}x{height} to {new_width}x{new_height}")

                # Determine output format
                output_format = 'JPEG'
                if output_path.suffix.lower() in ['.png']:
                    output_format = 'PNG'

                # Save optimized image
                save_kwargs = {'format': output_format, 'optimize': True}
                if output_format == 'JPEG':
                    save_kwargs['quality'] = quality

                img.save(output_path, **save_kwargs)

                # Log results
                original_size = input_path.stat().st_size / 1024  # KB
                new_size = output_path.stat().st_size / 1024  # KB
                compression_ratio = (1 - new_size / original_size) * 100

                self.logger.info(f"Optimized image: {input_path.name}")
                self.logger.info(f"  Size: {original_size:.0f}KB → {new_size:.0f}KB ({compression_ratio:.1f}% smaller)")

                return str(output_path)

        except Exception as e:
            self.logger.error(f"Error processing image {input_path}: {e}")
            return None

    def process_product_images(self, image_paths: List[str],
                               product_name: str = "product") -> List[str]:
        """
        Process multiple images for a product listing

        Args:
            image_paths: List of paths to product images
            product_name: Name of product (used for organizing files)

        Returns:
            List of paths to processed images
        """
        if not image_paths:
            return []

        self.logger.info(f"Processing {len(image_paths)} images for {product_name}")

        # Create product-specific folder
        product_folder = self.processed_folder / self._sanitize_filename(product_name)
        product_folder.mkdir(exist_ok=True)

        processed_images = []
        max_images = min(len(image_paths), Config.MAX_IMAGES_PER_LISTING)

        for i, image_path in enumerate(image_paths[:max_images]):
            try:
                # Generate output filename
                input_path = Path(image_path)
                output_filename = f"{i + 1:02d}_{input_path.stem}.jpg"
                output_path = product_folder / output_filename

                # Process image
                processed_path = self.resize_and_optimize_image(
                    input_path, output_path
                )

                if processed_path:
                    processed_images.append(processed_path)
                    self.logger.debug(f"Processed image {i + 1}/{max_images}")
                else:
                    self.logger.warning(f"Failed to process image: {image_path}")

            except Exception as e:
                self.logger.warning(f"Error processing image {image_path}: {e}")
                continue

        self.logger.info(f"Successfully processed {len(processed_images)}/{max_images} images")
        return processed_images

    def batch_validate_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Validate multiple images and return summary

        Args:
            image_paths: List of image paths to validate

        Returns:
            Dictionary with validation summary
        """
        results = {
            'total_images': len(image_paths),
            'valid_images': 0,
            'invalid_images': 0,
            'total_size_mb': 0,
            'errors': [],
            'details': {}
        }

        for image_path in image_paths:
            validation = self.validate_image(image_path)
            results['details'][image_path] = validation

            if validation['valid']:
                results['valid_images'] += 1
            else:
                results['invalid_images'] += 1
                results['errors'].extend([f"{image_path}: {error}" for error in validation['errors']])

            results['total_size_mb'] += validation['size_mb']

        results['total_size_mb'] = round(results['total_size_mb'], 2)
        results['average_size_mb'] = round(results['total_size_mb'] / len(image_paths), 2) if image_paths else 0

        return results

    def create_image_thumbnail(self, image_path: str, size: tuple = (200, 200)) -> Optional[str]:
        """
        Create a thumbnail for an image

        Args:
            image_path: Path to the source image
            size: Thumbnail size as (width, height)

        Returns:
            Path to thumbnail image, or None if failed
        """
        try:
            input_path = Path(image_path)
            if not input_path.exists():
                return None

            # Create thumbnails folder
            thumbnails_folder = self.images_folder / "thumbnails"
            thumbnails_folder.mkdir(exist_ok=True)

            # Generate thumbnail path
            thumb_path = thumbnails_folder / f"thumb_{input_path.stem}.jpg"

            # Create thumbnail
            with Image.open(input_path) as img:
                # Convert to RGB for JPEG
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumb_path, 'JPEG', quality=80, optimize=True)

                self.logger.debug(f"Created thumbnail: {thumb_path}")
                return str(thumb_path)

        except Exception as e:
            self.logger.error(f"Error creating thumbnail for {image_path}: {e}")
            return None

    def organize_images_by_product(self, products_images: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Organize and process images for multiple products

        Args:
            products_images: Dictionary mapping product names to image lists

        Returns:
            Dictionary mapping product names to processed image paths
        """
        organized_images = {}

        for product_name, image_paths in products_images.items():
            if not image_paths:
                organized_images[product_name] = []
                continue

            self.logger.info(f"Organizing images for product: {product_name}")
            processed_paths = self.process_product_images(image_paths, product_name)
            organized_images[product_name] = processed_paths

        return organized_images

    def cleanup_processed_images(self, older_than_days: int = 7) -> int:
        """
        Clean up old processed images

        Args:
            older_than_days: Remove files older than this many days

        Returns:
            Number of files removed
        """
        import time
        from datetime import datetime, timedelta

        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        removed_count = 0

        try:
            for file_path in self.processed_folder.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1

            self.logger.info(f"Cleaned up {removed_count} old processed images")

        except Exception as e:
            self.logger.error(f"Error cleaning up processed images: {e}")

        return removed_count

    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        Get detailed information about an image

        Args:
            image_path: Path to the image

        Returns:
            Dictionary with image information
        """
        info = {
            'path': image_path,
            'exists': False,
            'size_bytes': 0,
            'size_mb': 0,
            'dimensions': (0, 0),
            'format': None,
            'mode': None,
            'has_transparency': False
        }

        try:
            path = Path(image_path)
            if not path.exists():
                return info

            info['exists'] = True
            info['size_bytes'] = path.stat().st_size
            info['size_mb'] = round(info['size_bytes'] / (1024 * 1024), 2)

            with Image.open(path) as img:
                info['dimensions'] = img.size
                info['format'] = img.format
                info['mode'] = img.mode
                info['has_transparency'] = img.mode in ('RGBA', 'LA') or 'transparency' in img.info

        except Exception as e:
            info['error'] = str(e)

        return info

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for filesystem compatibility

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 50:
            filename = filename[:50]

        return filename.strip()


# Example usage and testing
if __name__ == "__main__":
    import tempfile
    from utils.logger import setup_logging

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing ImageHandler...")

    # Create ImageHandler instance
    with tempfile.TemporaryDirectory() as temp_dir:
        image_handler = ImageHandler(temp_dir)

        # Create a test image
        test_image_path = Path(temp_dir) / "test_image.jpg"
        test_image = Image.new('RGB', (800, 600), color='red')
        test_image.save(test_image_path, 'JPEG')

        logger.info(f"Created test image: {test_image_path}")

        # Test image validation
        validation = image_handler.validate_image(test_image_path)
        logger.info(f"Validation result: {validation}")

        # Test image processing
        processed_path = image_handler.resize_and_optimize_image(test_image_path)
        if processed_path:
            logger.info(f"✅ Image processing successful: {processed_path}")
        else:
            logger.error("❌ Image processing failed")

        # Test thumbnail creation
        thumb_path = image_handler.create_image_thumbnail(test_image_path)
        if thumb_path:
            logger.info(f"✅ Thumbnail creation successful: {thumb_path}")
        else:
            logger.error("❌ Thumbnail creation failed")

        # Test batch validation
        batch_result = image_handler.batch_validate_images([str(test_image_path)])
        logger.info(f"Batch validation: {batch_result}")

        logger.info("✅ ImageHandler tests completed!")