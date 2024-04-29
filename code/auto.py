# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# import subprocess

# class MyHandler(FileSystemEventHandler):
#     def on_created(self, event):
#         if event.is_directory:
#             return
#         # Execute your command when a file is created
#         subprocess.run(['python', 'sum.py', '-i', '1.mp4', '-s', '1.srt'])

# def start_watcher(folder_path):
#     event_handler = MyHandler()
#     observer = Observer()
#     observer.schedule(event_handler, path=folder_path, recursive=False)
#     observer.start()
#     try:
#         while True:
#             pass
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()

# if __name__ == "__main__":
#     folder_path = "C:/Users/acer/vidsum/code/"
#     start_watcher(folder_path)

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os

class MyHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()

    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith(".mp4"):
            video_file_name = os.path.splitext(os.path.basename(event.src_path))[0]
            
            srt_file_name = f"{video_file_name}.srt"

            subprocess.run(['python', 'sum.py', '-i', event.src_path, '-s', srt_file_name,'-st',"00:00:00",'-et',"00:05:00"])

def start_watcher(folder_path):
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path=folder_path, recursive=False)
    observer.start()
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    folder_path = "C:/Users/acer/vidsum/code/"
    start_watcher(folder_path)

