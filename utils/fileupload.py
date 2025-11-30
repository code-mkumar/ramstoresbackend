
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image
import json

class FileUpload:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in FileUpload.ALLOWED_EXTENSIONS

    @staticmethod
    def save_file(file, folder, custom_name=None):
        """Save uploaded file to specified folder, optionally using a custom filename"""
        if file and FileUpload.allowed_file(file.filename):
            # Check file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            if file_size > FileUpload.MAX_FILE_SIZE:
                raise ValueError("File size too large. Maximum 5MB allowed.")

            # Get extension
            ext = file.filename.rsplit('.', 1)[1].lower()

            # Generate filename: use custom_name or fallback to unique uuid
            if custom_name:
                safe_name = secure_filename(custom_name)
                filename = f"{safe_name}.{ext}"
            else:
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

            # Create folder if not exists
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
            os.makedirs(upload_folder, exist_ok=True)

            # Save file
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            # Optimize image
            FileUpload.optimize_image(file_path)

            return filename
        return None


    @staticmethod
    def optimize_image(file_path):
        """Optimize image size and quality"""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large (max width 1200px)
                if img.width > 1200:
                    ratio = 1200 / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((1200, new_height), Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(file_path, 'JPEG', quality=85, optimize=True)
        except Exception as e:
            print(f"Image optimization failed: {e}")

    @staticmethod
    def delete_file(filename, folder):
        """Delete file from storage"""
        if filename:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
            if os.path.exists(file_path):
                os.remove(file_path)

    @staticmethod
    def get_file_url(filename, folder):
        """Get URL for stored file"""
        if filename:
            return f"/uploads/{folder}/{filename}"
        return None

    @staticmethod
    def save_multiple_files(files, folder):
        """Save multiple files and return list of filenames"""
        filenames = []
        for file in files:
            if file and file.filename:  # Check if file is not empty
                filename = FileUpload.save_file(file, folder)
                if filename:
                    filenames.append(filename)
        return filenames
    
    @staticmethod
    def save_file_in_subfolder(file, base_folder, subfolder):
        """Save file inside nested folder → uploads/base_folder/subfolder/"""
        if file and FileUpload.allowed_file(file.filename):

            # Check file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            if file_size > FileUpload.MAX_FILE_SIZE:
                raise ValueError("File size too large. Maximum 5MB allowed.")

            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"

            # FULL PATH
            upload_folder = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                base_folder,
                secure_filename(subfolder)
            )

            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, unique_name)
            file.save(file_path)

            # Optimize
            FileUpload.optimize_image(file_path)

            # Return relative URL
            return f"/uploads/{base_folder}/{secure_filename(subfolder)}/{unique_name}"

        return None
