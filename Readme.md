# Pavet - Python Audio Video Text Extractor (in Docker)

## Features

- Extracts audio from online video platforms like YouTube, Vimeo, and Rumble.
- Transcribes extracted audio as well as local audio and video files.
- Supports multiple audio formats including MP3, MP4, and WAV.
- Running on Python 3.9 with dependencies managed by Docker.

## Prerequisites

- Docker
- Docker Compose
- Python 3.x (if running outside Docker)

## Directory Structure

pavet/  
├── Dockerfile: Defines the Docker container and its dependencies.  
├── docker-compose.yml: Docker Compose configuration file.  
├── pavet.py: Main Python script for video downloading and transcription.  
├── data/: Directory for storing downloaded or converted audio files.  
└── README.md: This documentation.  

## Getting Started

1. **Clone the repository**:
    ```bash
    git clone https://github.com/williamblair333/pavet.git
    cd pavet
    ```

2. **Build and start the Docker container**:
    ```bash
    docker-compose up --build
    ```

## 3. **Run the script with arguments using Docker Compose**

- For online mode:
    ```bash
    docker-compose exec <container_name> python pavet.py -m online -p 'https://youtube.com/watch?v=example'
    ```
  
- For offline mode:
    ```bash
    docker-compose exec <container_name> python pavet.py -m offline -p '/path/to/local/audio.wav'
    ```

- To save text to a custom directory and suppress console output:
    ```bash
    docker-compose exec <container_name> python pavet.py -m online -p 'https://youtube.com/watch?v=example' --output '/custom/output/file.txt' --print-console false
    ```

## 4. **Output**

Transcribed text will be printed in the terminal unless the `--print-console false` argument is used.

## Command-Line Arguments

Use the following command-line arguments for flexible operation:

- `-m` or `--mode`: Mode of operation (`online` for online video URLs, `offline` for local audio or video files).
  
- `-p` or `--path`: URL for `online` mode or local file path for `offline` mode.
  
- `--output`: Custom output path for the transcribed text file. Default is 'local_files/output'.
  
- `--print-console`: Whether or not to print the transcribed text to the console. Use 'true' to print or 'false' to suppress. Default is 'true'.
  
### For example:

```bash
python pavet.py -m online -p 'https://youtube.com/watch?v=example' --output '/custom/output/file.txt' --print-console false

## TODO

- [ ] Implement error handling for unsupported video URLs or restricted content.
- [ ] Integrate with a database to store transcriptions.
- [ ] Pocketsphinx needs tweaking or something. 
- [ ] Code structure is a bit messy and needs streamlining
- [ ] Argument to allow user to specify filename
