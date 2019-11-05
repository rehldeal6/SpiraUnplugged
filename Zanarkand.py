#!/usr/bin/env python
from __future__ import unicode_literals
#TODO: - Check to see if ffmpeg can start a video on a specific timestamp
#      - Add in bot to send messages to YT stream chat
#      - Add ability to auto-update

import os
import sys
import random
import logging
from argparse import ArgumentParser
from multiprocessing import Process

import ffmpeg
import youtube_dl
from youtube_dl.utils import ytdl_is_updateable as yt_needs_updating
from yaml import safe_load, YAMLError, safe_dump
from psutil import Process as p_process
from discord_webhook import DiscordWebhook

class Media:
    def __init__(self, config, name):
        self.name = name
        try:
            self.type = config["type"]
            self.id = config["id"]
        except KeyError as kerr:
            logging.error("Required values not specified for %s: %s", name, kerr)
        self.loops = config.get("loops", 1)
        self.exclude = config.get("exclude", [])
        self.audioid = config.get("audioformatid", "bestaudio")
        self.videoid = config.get("videoformatid", "bestvideo")
        if self.type == "playlist":
            self.beginning = config.get("beginning", 1)
            ydl = youtube_dl.YoutubeDL({'extract_flat': True, 'quiet': True})
            playlist_information = ydl.extract_info("https://www.youtube.com/playlist?list={}".format(self.id), download=False)
            self.ending = config.get("ending", len(playlist_information['entries']))
        elif self.type == "video":
            self.beginning = 1
            self.ending = 1
        return

    def download_episode(self, media_directory, episode, webhook_url):
        for extension in ["v", "a"]:
            filename = "{}{}-E{}.{}".format(media_directory, self.name, episode, extension)
            if os.path.exists("{}.part".format(filename)): 
                logging.debug("%s is partially downloaded. Removing", filename)
                try:
                    os.remove("{}.part".format(filename))
                except OSError as err:
                    logging.error("Could not remove %s.part: %s", filename, err)
            if not os.path.exists(filename): 
                logging.info("Downloading %s", filename)
                ytdl_options_video = {"quiet": True,
                                      "outtmpl": filename}
                if self.type == "playlist":
                    ytdl_options_video["playlist_items"] = str(episode)
                    download_url = "https://www.youtube.com/playlist?list={}".format(self.id)
                elif self.type == "video":
                    download_url = "https://www.youtube.com/watch?v={}".format(self.id)
                if extension == "v":
                    ytdl_options_video["format"] = self.videoid
                elif extension == "a":
                    ytdl_options_video["format"] = self.audioid
                ytdl_v = youtube_dl.YoutubeDL(ytdl_options_video)
                ytdl_v.download([download_url])
        return

class Stream:
    def __init__(self, order, media_dictionary, position, episode, loop):
        self.media = media_dictionary[order[position - 1]]
        self.episode = episode
        self.position = position

        self.loop = loop
        self.order = order
        self.media_dictionary = media_dictionary


    def next(self):
        if self.episode < self.media.ending:
            self.episode += 1
            while self.episode in self.media.exclude and self.episode < self.media.ending:
                self.episode += 1
        else:
            if self.loop < self.media.loops:
                self.loop += 1
            else:
                self.loop = 1
                if self.position == len(self.order):
                    self.position = 1
                else:
                    self.position += 1
                self.media = self.media_dictionary[self.order[self.position-1]]
            self.episode = self.media.beginning
        return

    def download_next_n_episodes(self, number, media_directory, webhook_url):
        download_episode = self.episode
        download_media = self.media
        download_loop = self.loop
        download_position = self.position
        for _ in xrange(1, number + 1):
            if download_episode < download_media.ending:
                download_episode += 1
                while download_episode in download_media.exclude and download_episode < download_media.ending:
                    download_episode += 1
            else:
                if download_loop < download_media.loops:
                    download_loop += 1
                else:
                    download_loop = 1
                    if download_position == len(self.order):
                        download_position = 1
                    else:
                        download_position += 1
                    download_media = self.media_dictionary[self.order[download_position-1]]
                download_episode = download_media.beginning
            Process(target=download_media.download_episode, args=(media_directory, download_episode, webhook_url,)).start().join()

    
    def stream_video(self, media_directory, overlay, ffmpeg_opts):
        overlay_input = ffmpeg.input(overlay)
        video = ffmpeg.input("{}{}-E{}.v".format(media_directory, self.media.name, self.episode), re=None).video.filter("scale", 1760, 990).filter("pad", 1920, 1080, 0, 90) .overlay(overlay_input)
        audio = ffmpeg.input("{}{}-E{}.a".format(media_directory, self.media.name, self.episode), re=None)
        try:
            logging.info("Starting episode %s-E%s", self.media.name, self.episode)
            ffmpeg.output(video,
                          audio,
                          ffmpeg_opts['filename'],
                          format=ffmpeg_opts['format'],
                          vcodec=ffmpeg_opts['videocodec'],
                          acodec=ffmpeg_opts['audiocodec'],
                          minrate=ffmpeg_opts['minbitrate'],
                          maxrate=ffmpeg_opts['maxbitrate'],
                          bufsize=ffmpeg_opts['bufsize'],
                          crf=ffmpeg_opts['crf'],
                          preset=ffmpeg_opts['preset'],
                          audio_bitrate=ffmpeg_opts['audiobitrate'],
                          ar=ffmpeg_opts['audiofrequeny'],
                          g=ffmpeg_opts['groupofpictures'])\
                  .run(quiet=True)
        except ffmpeg.Error as err:
            logging.error("Error while streaming %s-E%s: %s", self.media.name, self.episode, err)
        return

def stream_standby(standby_directory, ffmpeg_opts):
    video = random.choice(os.listdir(standby_directory))
    while True:
        try:
            logging.info("Starting standby video %s", video)
            ffmpeg.input(standby_directory + video, re=None).output(ffmpeg_opts['filename'],
                                                                    format=ffmpeg_opts['format'],
                                                                    vcodec=ffmpeg_opts['videocodec'],
                                                                    acodec=ffmpeg_opts['audiocodec'],
                                                                    minrate=ffmpeg_opts['minbitrate'],
                                                                    maxrate=ffmpeg_opts['maxbitrate'],
                                                                    bufsize=ffmpeg_opts['bufsize'],
                                                                    crf=ffmpeg_opts['crf'],
                                                                    preset=ffmpeg_opts['preset'],
                                                                    audio_bitrate=ffmpeg_opts['audiobitrate'],
                                                                    ar=ffmpeg_opts['audiofrequeny'],
                                                                    g=ffmpeg_opts['groupofpictures']).run(quiet=True)
        except ffmpeg.Error as err:
            logging.error("Error while streaming %s: %s", video, err)
    return



def media_files_exist(media_directory, media, episode):
        if not os.path.exists("{}{}-E{}.v".format(media_directory, media, episode)) or not os.path.exists("{}{}-E{}.a".format(media_directory, media, episode)):
            return False
        return True

def kill_process(parent_pid):
    logging.info("Stopping standby video")
    parent = p_process(parent_pid)
    for child in parent.children(recursive=True):
        child.kill()
    parent.kill()
    return

def main():
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="Main configuration file location", default="/opt/Zanarkand/config.conf")
    parser.add_argument("-d", "--debug", help="Enabled debug mode", action="store_true")
    args = parser.parse_args()

    with open(args.config, 'r') as input_config:
        try:
            config = safe_load(input_config)
        except YAMLError as yerr:
            logging.error("Couldn't read the yaml config file: %s", yerr)
            sys.exit(1)

    #Check mandatory options:
    for mandatory in ["youtube_key", "mediadirectory", "defaultdirectory", "logdirectory", "order", "sections", "discordwebhook"]:
        if mandatory not in config:
            print("Mandatory option %s is not in the config file %s", mandatory, args.config)
            sys.exit(1)

    # Check folders
    for check_dir in ["defaultdirectory", "logdirectory", "mediadirectory"]:
        if check_dir in config:
            config[check_dir] = config[check_dir] + "/" if not config[check_dir].endswith('/') else config[check_dir]
            if not os.path.exists(config[check_dir]):
                print("Directory %s specified in the configuration does not exist")
                sys.exit(1)
    default_directory = config.get("defaultdirectory", "/opt/Zanarkand/defaults/")
    log_directory = config.get("logdirectory", "/opt/Zanarkand/logs/")
    media_directory = config.get("mediadirectory", "/opt/Zanarkand/media/")

    # Set up logging
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level,
                        filemode='a',
                        filename="{}Zanarkand.log".format(log_directory),
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    logging.info("Starting Stream...")

    #Other settings
    webhook = config.get("discordwebhook")
    number_of_downloads = config.get("numberofdownloads", 3)
    config["ffmpeg"]["filename"] = "rtmp://a.rtmp.youtube.com/live2/{}".format(config["youtube_key"])

    # Create Media dictionary
    media_dictionary = {}
    for media_section in config["sections"]:
        print("Making media object {}".format(media_section))
        media = Media(config["sections"][media_section], media_section)
        media_dictionary[media_section] = media

    status_yaml = config.get("current_status", "/opt/Zanarkand/current_status.yaml")
    with open(status_yaml, 'r') as input_status:
        try:
            status = safe_load(input_status)
        except YAMLError as yerr:
            logging.error("Couldn't read the yaml config file: %s", yerr)
            sys.exit(1)

    stream = Stream(config.get("order"), media_dictionary, status.get("position", 1), status.get("episode", 1), status.get("loop", 1))
    default_stream = Process(target=stream_standby, args=(default_directory, config["ffmpeg"],))
    previous_media = None
    print("Media: {}".format(stream.media.name))
    print("Episode: {}".format(stream.episode))
    print("Loop: {}".format(stream.loop))
    print("Position: {}".format(stream.position))

    while True:
        if not media_files_exist(media_directory, stream.media.name, stream.episode) or yt_needs_updating():
            logging.warning("Could not find media files for %s-E%s. Switching to standby", stream.media.name, stream.episode)
            if not yt_needs_updating():
                print("Downloading {}-E{}".format(stream.media.name, stream.episode))
                download_episode = Process(target=stream.media.download_episode, args=(media_directory, stream.episode, webhook,))
                download_episode.start()
            while not media_files_exist(media_directory, stream.media.name, stream.episode):
                if not default_stream.is_alive():
                    default_stream.start()
            download_episode.join()
        if default_stream.is_alive():
            kill_process(default_stream.pid)
        streaming = Process(target=stream.stream_video, args=(media_directory, config.get("overlay"), config["ffmpeg"],))
        streaming.start()

        # Update status
        current_status = {'game': stream.media.name,
                          'position': stream.position,
                          'episode': stream.episode,
                          'loop': stream.loop}
        with open(status_yaml, 'w') as write_status:
            safe_dump(current_status,
                 write_status,
                 default_flow_style=False)

        # Delete previous episodes
        if previous_media:
            try:
                os.remove(media_directory + "{}.v".format(previous_media))
                os.remove(media_directory + "{}.v".format(previous_media))
            except OSError as err:
                logging.error("Could not remove the media files for %s-E%s: %s", stream.media.name, stream.episode, err)

        # Download next N episodes
        Process(target=stream.download_next_n_episodes, args=(number_of_downloads, media_directory, webhook,)).start()
        # Set up for next episode
        previous_media = "{}{}-E{}".format(media_directory, stream.media.name, stream.episode)
        stream.next()

        # Wait until Stream ends
        streaming.join()

if __name__ == "__main__":
    main()
