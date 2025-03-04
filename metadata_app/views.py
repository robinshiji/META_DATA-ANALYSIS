from django.shortcuts import render, redirect,get_object_or_404
from .forms import FileUploadForm
from .models import UploadedFile
import os
from PIL import Image
from PIL.ExifTags import TAGS
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
import ffmpeg
import fitz 
from pdfminer.high_level import extract_text
from django.views.decorators.cache import never_cache
from docx import Document

def extract_metadata(file_path):
    metadata = {}
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension in ['.jpg', '.jpeg', '.png']:
        metadata = extract_image_metadata(file_path)
    elif file_extension in ['.pdf', '.docx', '.txt']:
        metadata = extract_document_metadata(file_path)
    elif file_extension in ['.mp3', '.wav']:
        metadata = extract_audio_metadata(file_path, file_extension)
    elif file_extension in ['.mp4', '.avi', '.mkv']:
        metadata = extract_video_metadata(file_path)

    return metadata

def extract_image_metadata(file_path):
    metadata = {}
    with Image.open(file_path) as img:
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                metadata[tag] = value
        else:
            metadata["Info"] = "No EXIF metadata found"  # Handle images without metadata

    metadata["Format"] = img.format
    metadata["Size"] = img.size  # (width, height)
    metadata["Mode"] = img.mode  # RGB, RGBA, etc.

    return metadata


def extract_document_metadata(file_path):
    metadata = {}
    _, file_extension = os.path.splitext(file_path)

    try:
        if file_extension == '.pdf':
            with fitz.open(file_path) as doc:
                pdf_metadata = doc.metadata  # Get metadata like author, title, etc.
                metadata.update(pdf_metadata)  
                metadata["Text"] = "\n".join([page.get_text() for page in doc])  # Extract text
        elif file_extension == '.docx':
            doc = Document(file_path)
            metadata["Text"] = "\n".join([para.text for para in doc.paragraphs])
        elif file_extension == '.txt':
            with open(file_path, 'rb') as file:
                metadata["Text"] = file.read().decode(errors='ignore')  # Fix encoding issues
    except Exception as e:
        metadata["Error"] = str(e)  # Handle file reading errors

    return metadata

def extract_audio_metadata(file_path, file_extension):
    metadata = {}

    try:
        if file_extension == ".mp3":
            audio = MP3(file_path)
        elif file_extension == ".wav":
            audio = WAVE(file_path)
        else:
            return {"Error": "Unsupported audio format"}

        metadata["Duration"] = round(audio.info.length, 2)  # Duration in seconds
        metadata["Bitrate"] = getattr(audio.info, "bitrate", "Unknown")  # Handle missing bitrate
    except Exception as e:
        metadata["Error"] = str(e)  # Catch errors in metadata extraction

    return metadata

def extract_video_metadata(file_path):
    metadata = {}

    try:
        probe = ffmpeg.probe(file_path)
        video_info = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

        if video_info:
            metadata["Resolution"] = f"{video_info['width']}x{video_info['height']}"
            metadata["Codec"] = video_info['codec_name']
            metadata["Duration"] = round(float(probe['format']['duration']), 2)  # Convert to float
        else:
            metadata["Error"] = "No video stream found"
    except Exception as e:
        metadata["Error"] = str(e)  # Handle missing or unreadable metadata

    return metadata

@never_cache
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save()
            file_path = uploaded_file.file.path
            metadata = extract_metadata(file_path)

            return render(request, 'upload.html', {
                'form': form,
                'metadata': metadata,
                'file_name': uploaded_file.file.name
            })
    else:
        form = FileUploadForm()

    return render(request, 'upload.html', {'form': form})

def welcome(request):
    return render(request,'welcome.html')

@never_cache
def dashboard(request):
    dash=UploadedFile.objects.all()
    return render(request,'dash.html',{'dash':dash})

def delete_file(request, file_id):
    file_obj = get_object_or_404(UploadedFile, id=file_id)

    # Ensure the file exists in storage before deleting
    if file_obj.file and os.path.exists(file_obj.file.path):
        os.remove(file_obj.file.path)  # Delete file from storage

    file_obj.delete()  # Delete record from database

    return redirect('dashboard')  # 