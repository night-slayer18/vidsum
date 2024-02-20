#!/usr/bin/env python
from __future__ import unicode_literals
import argparse
import os
import re
from itertools import starmap
import multiprocessing

import pysrt
import chardet
import nltk
from moviepy.editor import VideoFileClip, concatenate_videoclips
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from sumy.summarizers.lsa import LsaSummarizer
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi

nltk.download('punkt')

def summarize(srt_file, n_sentences, language="english"):
    parser = PlaintextParser.from_string(
        srt_to_txt(srt_file), Tokenizer(language))
    stemmer = Stemmer(language)
    summarizer = LsaSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(language)
    segment = []
    for sentence in summarizer(parser.document, n_sentences):
        index = int(re.findall("\(([0-9]+)\)", str(sentence))[0])
        item = srt_file[index]
        segment.append(srt_segment_to_range(item))
    return segment

def srt_to_txt(srt_file):
    text = ''
    for index, item in enumerate(srt_file):
        if item.text.startswith("["):
            continue
        text += "(%d) " % index
        text += item.text.replace("\n", "").strip("...").replace(
            ".", "").replace("?", "").replace("!", "")
        text += ". "
    return text

def srt_segment_to_range(item):
    start_segment = item.start.hours * 60 * 60 + item.start.minutes * \
        60 + item.start.seconds + item.start.milliseconds / 1000.0
    end_segment = item.end.hours * 60 * 60 + item.end.minutes * \
        60 + item.end.seconds + item.end.milliseconds / 1000.0
    return start_segment, end_segment

def time_regions(regions):
    return sum(starmap(lambda start, end: end - start, regions))

def find_summary_regions(srt_filename, duration=30, language="english"):
    enc = chardet.detect(open(srt_filename, "rb").read())['encoding']
    srt_file = pysrt.open(srt_filename, encoding=enc)
    
    subtitle_duration = time_regions(
        map(srt_segment_to_range, srt_file)) / len(srt_file)
    n_sentences = duration / subtitle_duration
    summary = summarize(srt_file, n_sentences, language)
    total_time = time_regions(summary)
    too_short = total_time < duration
    if too_short:
        while total_time < duration:
            n_sentences += 1
            summary = summarize(srt_file, n_sentences, language)
            total_time = time_regions(summary)
    else:
        while total_time > duration:
            n_sentences -= 1
            summary = summarize(srt_file, n_sentences, language)
            total_time = time_regions(summary)
    return summary

def create_summary(filename, regions, target_duration):
    subclips = []
    input_video = VideoFileClip(filename)
    last_end = 0
    for (start, end) in regions:
        subclip = input_video.subclip(start, end)
        subclips.append(subclip)
        last_end = end
    summary = concatenate_videoclips(subclips)
    
    # Resize the summary to be 1/4th of the original video
    summary = summary.resize(width=int(input_video.size[0]/2), height=int(input_video.size[1]/2))
    
    return summary

def get_summary(filename="1.mp4", subtitles="1.srt", original_video_duration=None):
    if original_video_duration is None:
        # If original video duration is not provided, use a default value or calculate it
        original_video = VideoFileClip(filename)
        original_video_duration = original_video.duration

    target_duration = original_video_duration / 4  # Set target duration to 1/4th of the original video duration

    regions = find_summary_regions(subtitles, target_duration, "english")
    summary = create_summary(filename, regions, target_duration)
    base, ext = os.path.splitext(filename)
    output = "{0}_summarised.mp4".format(base)
    summary.to_videofile(
        output,
        codec="libx264",
        temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac"
    )
    return True

def download_video(url, filename="1.mp4"):
    try:
        # Create a YouTube object
        yt = YouTube(url)

        # Get the highest resolution stream
        video_stream = yt.streams.get_highest_resolution()

        # Download the video to the current directory with the specified filename
        video_stream.download(filename=filename)

        print(f"Download successful! Saved as {filename}")
        return filename
    except Exception as e:
        print(f"Error: {e}")

def get_video_id(url):
    try:
        # Extract video ID from the URL
        yt = YouTube(url)
        video_id = yt.video_id
        return video_id
    except Exception as e:
        print(f"Error extracting video ID: {e}")
        return None

def download_cc_as_srt(video_url, output_filename="1.srt"):
    # Get the video ID from the URL
    video_id = get_video_id(video_url)

    if video_id:
        # Get the transcript for the YouTube video
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        if transcript:
            # Write the transcript to an SRT file
            with open(output_filename, 'w', encoding='utf-8') as srt_file:
                for i, entry in enumerate(transcript, start=1):
                    start_time = entry['start']
                    end_time = start_time + entry['duration']
                    text = entry['text']
                    
                    srt_file.write(f"{i}\n{format_time(start_time)} --> {format_time(end_time)}\n{text}\n\n")

            print(f"SRT file generated successfully: {output_filename}")
        else:
            print("No transcript available for this video.")
    else:
        print("Failed to extract video ID.")
    return output_filename

def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},000"

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Watch videos quickly")
    parser.add_argument('-i', '--video-file', help="Input video file")
    parser.add_argument('-s', '--subtitles-file', help="Input subtitle file (srt)")
    parser.add_argument('-u', '--url', help="Video url", type=str)
    parser.add_argument('-k', '--keep-original-file', help="Keep original movie & subtitle file",
                        action="store_true", default=False)

    args = parser.parse_args()

    url = args.url
    keep_original_file = args.keep_original_file

    if not url:
        # Proceed with general summarization
        get_summary(args.video_file, args.subtitles_file)

    else:
        # Download video with subtitles
        movie_filename = download_video(url)
        subtitle_filename = download_cc_as_srt(url)
        summary_retrieval_process = multiprocessing.Process(target=get_summary,
                                                            args=(movie_filename, subtitle_filename))  # Remove target_duration argument
        summary_retrieval_process.start()
        summary_retrieval_process.join()
        if not keep_original_file:
            os.remove(movie_filename)
            os.remove(subtitle_filename)
            print("[sum.py] Remove the original files")
