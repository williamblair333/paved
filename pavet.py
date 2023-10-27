import yt_dlp
import speech_recognition as sr
import argparse
import time
import pocketsphinx

# Download audio from a video URL
def download_audio(video_url, output_folder):
    audio_path = f"{output_folder}/audio"
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': f"{audio_path}.%(ext)s"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    return f"{audio_path}.wav"

# Transcribe audio to text
import speech_recognition as sr

def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    text = ""
    
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
        
    try:
        text = recognizer.recognize_sphinx(audio_data)
    except sr.UnknownValueError:
        text = "Sphinx could not understand the audio"
    except sr.RequestError as e:
        text = f"Sphinx error: {e}"
    
    return text


def main():
    parser = argparse.ArgumentParser(description='Transcribe video/audio to text.')
    parser.add_argument('-m', '--mode', choices=['online', 'offline'], required=True, help='Mode: online or offline')
    parser.add_argument('-p', '--path', required=True, help='URL for online mode or local file path for offline mode')
    parser.add_argument('--input-folder', default='/data', help='Input folder, default is /data')
    parser.add_argument('--output-folder', default='/data/output', help='Output folder, default is /data/output')
    args = parser.parse_args()

    audio_path = ''
    if args.mode == 'online':
        audio_path = download_audio(args.path, args.output_folder)
    elif args.mode == 'offline':
        audio_path = args.path

    text = transcribe_audio(audio_path)
    print(text)

if __name__ == "__main__":
    main()
