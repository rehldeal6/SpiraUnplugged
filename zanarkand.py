#!/usr/bin/env python3
#TODO: - Check to see if ffmpeg can start a video on a specific timestamp
#      - Add in bot to send messages to YT stream chat

import os
import logging
from time import sleep
from random import choice
from sys import exit as sys_exit
from subprocess import check_call
from signal import signal, SIGTERM
from argparse import ArgumentParser
from multiprocessing import Process

import ffmpeg
import youtube_dl
from youtube_dl.utils import ytdl_is_updateable as yt_needs_updating
from yaml import safe_load, YAMLError, safe_dump
from psutil import Process as p_process
from discord_webhook import DiscordWebhook

class Media:
    '''
    Object for a specific media or game (playlist of single video).
    Contains information such as youtube ID, number of loops, video/audio quality, etc.
    '''
    def __init__(self, config, name):
        '''
        Create the media object

        Inputs:
        config      [dict] Media configuration
        name        [str]  Name of media
        '''
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

    def download_episode(self, media_directory, episode, webhook):
        '''
        Uses youtube-dl to download the specific episode. First downloads the video file, then audio file. Will also try to
        self update if needed. Sends notifications to discord if anything fails or it attempts to update itself

        Input:
        media_directory     [str] Location where to save the files
        episode             [int] Episode number to download
        webhook             [str] Discord webhook for notifications
        '''

        if yt_needs_updating():
            DiscordWebhook(url=webhook, content='@everyone Youtube-dl needs updating! Attempting to upgrade it myself...').execute()
            check_call(['youtube-dl', '-U'])
            check_call(['python', '-m', 'pip', 'install', '--upgrade', 'youtube_dl'])
        for extension in ["v", "a"]:
            filename = "{}{}-E{}.{}".format(media_directory, self.name, episode, extension)
            if os.path.exists("{}.part".format(filename)):
                logging.warning("%s is partially downloaded. Removing", filename)
                try:
                    os.remove("{}.part".format(filename))
                except OSError as err:
                    logging.error("Could not remove %s.part: %s", filename, err)
            if not os.path.exists(filename):
                logging.info("Downloading %s", filename)
                ytdl_options_video = {"quiet": True,
                                      "cachedir": False,
                                      "outtmpl": filename}
                if self.type == "playlist":
                    ytdl_options_video["playlist_items"] = str(episode)
                    download_url = "https://www.youtube.com/playlist?list={}".format(self.id)
                elif self.type == "video":
                    download_url = "https://www.youtube.com/watch?v={}".format(self.id)
                if extension == "v":
                    ytdl_options_video["format"] = str(self.videoid)
                elif extension == "a":
                    ytdl_options_video["format"] = str(self.audioid)
                ytdl = youtube_dl.YoutubeDL(ytdl_options_video)
                ytdl.download([download_url])
        if not media_files_exist(media_directory, self.name, episode):
            DiscordWebhook(url=webhook, content='@everyone Failed download episode {}-E{}!'.format(self.name, episode)).execute()

class Stream:
    '''
    Overall stream object. It contains information about what's currently being played, the order of media to play,
    current loop, etc.
    '''
    def __init__(self, order, media_dictionary, position, episode, loop):
        '''
        Create the stream object

        Inputs:
        order               [list] Order of media to play
        media_dictionary    [dict] Dictionary of Media objects
        position            [int]  Current position in order
        episode             [int]  First episode to play
        loop                [int]  Loop order
        '''

        self.media = media_dictionary[order[position - 1]]
        self.episode = episode
        self.position = position

        self.loop = loop
        self.order = order
        self.media_dictionary = media_dictionary


    def next_video(self):
        '''
        Set the stream to play the next episode
        '''
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

    def download_next_n_episodes(self, number, media_directory, webhook):
        '''
        Get the next N episodes and download them preemptively

        Inputs:
        number          [int] Number of episodes ahead to download
        media_directory [str] Directory to store the downloaded media
        webhook         [str] Discord webhook for notifications
        '''
        download_episode = self.episode
        download_media = self.media
        download_loop = self.loop
        download_position = self.position
        for _ in range(1, number + 1):
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
            download = Process(target=download_media.download_episode, args=(media_directory, download_episode, webhook,))
            download.start()
            download.join()

    def stream_video(self, media_directory, overlay, ffmpeg_opts, webhook):
        '''
        Use ffmpeg to stream the current stream episode

        Inputs:
        media_directory     [str]  Directory containing media files
        overlay             [str]  Location of the overlay to put on top of the video
        ffmpeg_opts         [dict] Dictionary of ffmpeg options used
        webhook             [str] Discord webhook for notifications
        '''
        overlay_input = ffmpeg.input(overlay)\
                               .filter("ass",
                                       filename=ffmpeg_opts['subtitles']['final'])
        video = ffmpeg.input("{}{}-E{}.v".format(media_directory, self.media.name, self.episode), re=None)\
                      .video\
                      .filter("scale",
                              ffmpeg_opts['viewportwidth'],
                              ffmpeg_opts['viewportheight'])\
                      .filter("pad",
                              ffmpeg_opts['resolutionwidth'],
                              ffmpeg_opts['resolutionheight'],
                              ffmpeg_opts['viewportx'],
                              ffmpeg_opts['viewporty'])\
                      .overlay(overlay_input)
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
                  .run(capture_stdout=True,
                       capture_stderr=True,
                       quiet=True)
        except ffmpeg.Error as err:
            logging.error("Error while streaming %s-E%s.", self.media.name, self.episode)
            DiscordWebhook(url=webhook, content=err.stderr.decode('utf8')[-2000:]).execute()

    def set_subtitles(self, ffmpeg_opts):
        '''
        Create "subtitles" that display the order of the games

        Inputs:
        ffmpeg_opts         [dict] Dictionary of ffmpeg options used
        '''
        before_games = []
        for game in self.order[:self.position-1]:
            if self.media_dictionary[game].type == "playlist":
                before_games.append(game)
        before = " -> ".join(before_games)
        if before:
            before += " -> "
        after_games = []
        for game in self.order[self.position:]:
            if self.media_dictionary[game].type == "playlist":
                after_games.append(game)
        after = " -> ".join(after_games)
        if after:
            after = " -> " + after
        if self.media.type == "playlist":
            current_game = "{} (Ep {}/{} Loop {}/{})".format(self.media.name,
                                                             self.episode,
                                                             self.media.ending,
                                                             self.loop,
                                                             self.media.loops)
        else:
            current_game = self.media.name
        dialogue = ""
        if before:
            dialogue += "{\\c&H7F7F7F&\\fscx115\\fscy115\\pos(960,85)}"
            dialogue += "{}".format(before)
            dialogue += "{\\c&H00FFFF&\\fscx130\\fscy130}"
            dialogue += "{}".format(current_game)
        else:
            dialogue += "{\\c&H00FFFF&\\fscx130\\fscy130\\pos(960,85)}"
            dialogue += "{}".format(current_game)
        if after:
            dialogue += "{\\c&H7F7F7F&\\u0\\fscx115\\fscy115}"
            dialogue += "{}".format(after)
        logging.debug("Subtitle should read %s", dialogue)
        try:
            with open(ffmpeg_opts['subtitles']['template'], 'r') as st:
                content = st.read().rstrip()
            content += dialogue
            with open(ffmpeg_opts['subtitles']['final'], 'w') as sf:
                sf.write(content)
        except IOError as ioe:
            logging.error("Couldn't open or write script file: %s", ioe)

def stream_longer_standby(standby_directory, ffmpeg_opts, webhook):
    '''
    Use ffmpeg to stream the current a random standby video

    Inputs:
    standby_directory   [str]  Directory containing pre-downloaded standby videos
    ffmpeg_opts         [dict] Dictionary of ffmpeg options used
    webhook             [str] Discord webhook for notifications
    '''
    while True:
        try:
            media = choice(os.listdir(standby_directory))
            logging.info("Starting longer standby video %s", media)
            video_name = os.path.splitext(media)[0]
            video = ffmpeg.input(standby_directory + media, re=None).video\
                          .drawtext(text="The stream is currently on standby, please bear with us while the Al-Bhed Tech Support fixes the issue.",
                                    x="(w-text_w)/2",
                                    y="h-100",
                                    fontcolor="yellow",
                                    fontsize=40,
                                    font=ffmpeg_opts['text']['font'],
                                    box=1,
                                    boxcolor="black",
                                    boxborderw=5)\
                          .drawtext(text="Now Playing: {}".format(video_name),
                                    x="(w-text_w)/2",
                                    y="h-50",
                                    fontcolor="yellow",
                                    fontsize=40,
                                    font=ffmpeg_opts['text']['font'],
                                    box=1,
                                    boxcolor="black",
                                    boxborderw=5)
            audio = ffmpeg.input(standby_directory + media, re=None).audio
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
                  .run(capture_stdout=True,
                       capture_stderr=True,
                       quiet=True)
        except ffmpeg.Error as err:
            logging.error("Error while streaming %s.", video)
            logging.error("\tstderr: %s", err.stderr.decode('utf8'))
            DiscordWebhook(url=webhook, content=err.stderr.decode('utf8')[-2000:]).execute()

def stream_initial_standby(standby_video, output, webhook):
    '''
    Use ffmpeg to stream the current a random standby video

    Inputs:
    standby_video   [str] Initial default standby video
    output          [str] youtube URL to output
    webhook             [str] Discord webhook for notifications
    '''
    try:
        logging.info("Starting initial standby video %s", standby_video)
        ffmpeg.input(standby_video, re=None)\
              .output(output, format="flv")\
              .run(capture_stdout=True,
                   capture_stderr=True,
                   quiet=True)
    except ffmpeg.Error as err:
        logging.error("Error while streaming %s.", standby_video)
        logging.error("\tstderr: %s", err.stderr.decode('utf8'))
        DiscordWebhook(url=webhook, content=err.stderr.decode('utf8')[-2000:]).execute()

def media_files_exist(media_directory, media, episode):
    '''
    Check if both audio and video file exists for a particular episode of media

    Inputs:
    media_directory     [str] Directory to check for downloaded media
    media               [str] Name of media
    episode             [int] Episode to check
    '''
    if not os.path.exists("{}{}-E{}.v".format(media_directory, media, episode)) or not os.path.exists("{}{}-E{}.a".format(media_directory, media, episode)):
        return False
    return True

def kill_process(parent_pid):
    '''
    Kill a process and its children. Used for the intial standby stream.

    Inputs:
    parent_pid      [int] PID of the standby process
    '''
    logging.info("Stopping standby video")
    parent = p_process(parent_pid)
    for child in parent.children(recursive=True):
        child.kill()
    parent.kill()

def stop_zanarkand(signum, frame):
    '''
    Handle the child processes when the container/process gets a STOP signal
    '''
    kill_process(os.getpid())

def main():
    '''
    main
    '''
    signal(SIGTERM, stop_zanarkand)
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="Main configuration file location", default="/opt/zanarkand/config.yml")
    parser.add_argument("-d", "--debug", help="Enabled debug mode", action="store_true")
    args = parser.parse_args()

    with open(args.config, 'r') as input_config:
        try:
            config = safe_load(input_config)
        except YAMLError as yerr:
            print("Couldn't read yaml config file {}: {}".format(args.config, yerr))
            logging.error("Couldn't read yaml config file %s: %s", args.config, yerr)
            sys_exit(1)

    #Check mandatory options:
    for mandatory in ["youtube_key", "mediadirectory", "standbydirectory", "order", "sections", "discordwebhook"]:
        if mandatory not in config:
            print("Mandatory option {} is not in the config file {}".format(mandatory, args.config))
            logging.error("Mandatory option %s is not in the config file %s", mandatory, args.config)
            sys_exit(1)

    # Check folders
    for check_dir in ["standbydirectory", "mediadirectory"]:
        if check_dir in config:
            config[check_dir] = config[check_dir] + "/" if not config[check_dir].endswith('/') else config[check_dir]
            if not os.path.exists(config[check_dir]):
                print("Directory {} specified in the configuration does not exist".format(check_dir))
                logging.error("Directory %s specified in the configuration does not exist", check_dir)
                sys_exit(1)
    standby_directory = config.get("standbydirectory", "/opt/zanarkand/standby/")
    media_directory = config.get("mediadirectory", "/opt/zanarkand/media/")
    initial_standby_video = config.get("initialstandbyvideo", "/opt/zanarkand/resouces/standby.flv")

    # Set up logging
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level,
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
        media = Media(config["sections"][media_section], media_section)
        media_dictionary[media_section] = media

    status_yaml = config.get("current_status", "/opt/zanarkand/current_status.yaml")
    with open(status_yaml, 'r') as input_status:
        try:
            status = safe_load(input_status)
        except YAMLError as yerr:
            logging.error("Couldn't read the yaml config file: %s", yerr)
            sys_exit(1)

    stream = Stream(config.get("order"), media_dictionary, status.get("position", 1), status.get("episode", 1), status.get("loop", 1))
    stream.set_subtitles(config["ffmpeg"])
    initial_standby = Process(target=stream_initial_standby, args=(initial_standby_video, config["ffmpeg"]["filename"], webhook))
    longer_standby = Process(target=stream_longer_standby, args=(standby_directory, config["ffmpeg"], webhook))
    initial_standby_played = False
    previous_media = None
    download_next = None

    while True:
        download_attempts = 0
        while not media_files_exist(media_directory, stream.media.name, stream.episode):
            if not initial_standby.is_alive() and not initial_standby_played:
                logging.warning("Could not find media files for %s-E%s. Switching to standby", stream.media.name, stream.episode)
                initial_standby.start()
            elif initial_standby.is_alive() and not initial_standby_played:
                initial_standby.join()
                initial_standby_played = True
            elif initial_standby_played:
                longer_standby.start()
                longer_standby.join()
            while download_attempts < config.get("downloadattemps", 5) and not media_files_exist(media_directory, stream.media.name, stream.episode):
                if download_attempts >= 1:
                    sleep(config.get("faileddownloadwait", 60))
                download_episode = Process(target=stream.media.download_episode, args=(media_directory, stream.episode, webhook))
                download_episode.start()
                download_episode.join()
                download_attempts += 1
        if initial_standby.is_alive():
            kill_process(initial_standby.pid)
        streaming = Process(target=stream.stream_video, args=(media_directory, config.get("overlay"), config["ffmpeg"], webhook))
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
                os.remove("{}.v".format(previous_media))
                os.remove("{}.a".format(previous_media))
            except OSError as err:
                logging.error("Could not remove the media files for %s-E%s: %s", stream.media.name, stream.episode, err)

        # Download next N episodes
        if download_next:
            if download_next.is_alive():
                kill_process(download_next.pid)
        download_next = Process(target=stream.download_next_n_episodes, args=(number_of_downloads, media_directory, webhook))
        download_next.start()

        #Sleep so that the video plays the correct subtitles
        sleep(10)
        # Set up for next episode
        previous_media = "{}{}-E{}".format(media_directory, stream.media.name, stream.episode)
        stream.next_video()
        stream.set_subtitles(config["ffmpeg"])

        # Wait until Stream ends
        streaming.join()

if __name__ == "__main__":
    main()
