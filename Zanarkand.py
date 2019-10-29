#!/usr/bin/env python
from __future__ import unicode_literals
#TODO: - Check to see if ffmpeg can start a video on a specific timestamp
#      - Add in limited number of yt-dl requests
#      - Add ability to auto-update

import os
import sys
import random
import logging
from argparse import ArgumentParser
from multiprocessing import Process
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError, ParsingError

import ffmpeg
import youtube_dl
from psutil import Process as p_process

class Game:
    def __init__(self, config, name):
        self.name = name
        self.playlist_id = config.get(name, "PlaylistID")
        self.loops = config.getint(name, "NumberOfLoops")
        ydl = youtube_dl.YoutubeDL({'extract_flat': True, 'quiet': True})
        playlist_information = ydl.extract_info("https://www.youtube.com/playlist?list={}".format(self.playlist_id), download=False)
        self.total_episodes = len(playlist_information['entries'])

class Stream:
    def __init__(self, config):
        self.game = None
        self.next_game = None
        self.episode = None
        self.loop = None
        self.position = None
        self.playlist_file = config

        try:
            self.playlist = dict(config._sections['Order'])
            del self.playlist['__name__']
        except KeyError:
            logging.error("There's no 'Order' section in the playlist file.")
            sys.exit(4)

        self.number_of_games = len(self.playlist.keys())

    def update_status(self, status_conf):
        self.game = Game(self.playlist_file, status_conf.get("current", "Game", "FF7"))
        self.episode = status_conf.getint("current", "Episode") if status_conf.has_option("current", "Episode") else 1
        self.loop = status_conf.getint("current", "Loop") if status_conf.has_option("current", "Loop") else 1
        self.position = status_conf.getint("current", "Position") if status_conf.has_option("current", "Position") else 1
        return

    def next(self):
        if self.episode < self.game.total_episodes:
            self.episode += 1
        else:
            self.episode = 1
            if self.loop == self.game.loops:
                self.game = self.next_game
                self.loop = 1
                if self.position == self.number_of_games:
                    self.position = 1
                else:
                    self.position += 1
            else:
                self.loop += 1
        return

    def get_next_game_name(self):
        if self.position == self.number_of_games:
            return self.playlist['1']
        return self.playlist[str(self.position + 1)]

    def get_next_n_episodes(self, n):
        list_of_episodes = []
        for i in xrange(1, n+1):
            download_episode = self.episode + i
            if download_episode > self.game.total_episodes:
                download_episode = download_episode % self.game.total_episodes
                if not self.next_game or (self.next_game.name != self.get_next_game_name()):
                    self.next_game = Game(self.playlist_file, self.get_next_game_name())
                if self.loop == self.game.loops:
                    list_of_episodes.append((self.next_game.name, self.next_game.playlist_id, download_episode))
                else:
                    list_of_episodes.append((self.game.name, self.game.playlist_id, download_episode))
            else:
                list_of_episodes.append((self.game.name, self.game.playlist_id, download_episode))
        return list_of_episodes

    def current_video_exists(self, media_folder):
        if not os.path.exists("{}{}-E{}.v".format(media_folder, self.game.name, self.episode)) or not os.path.exists("{}{}-E{}.v".format(media_folder, self.game.name, self.episode)):
            return False
        return True


def yt_download_episode(playlist, game, episode, media_folder):
    # Check if needs update
    if youtube_dl.utils.ytdl_is_updateable():
        logging.critical("Please update youtube-dl!")
        #TODO - Add in discord notification

    #Video
    if os.path.exists("{}{}-E{}.v.part".format(media_folder, game, episode)):
        logging.debug("%s%s-E%s.v is partially downloaded. Removing", media_folder, game, episode)
        try:
            os.remove("{}{}-E{}.v.part".format(media_folder, game, episode))
        except OSError as err:
            logging.error("Could not remove %s%s-E%s.v.part: %s", media_folder, game, episode, err)
    if not os.path.exists("{}{}-E{}.v".format(media_folder, game, episode)):
        logging.info("Downloading %s-E%s", game, episode)
        ytdl_options_video = {"format": "bestvideo",
                              "quiet": True,
                              "outtmpl": media_folder + "{}-E{}.v".format(game, episode),
                              "playlist_items": str(episode)}
        ytdl_v = youtube_dl.YoutubeDL(ytdl_options_video)
        ytdl_v.download(["https://www.youtube.com/playlist?list=" + playlist])

    # Audio
    if os.path.exists("{}{}-E{}.a.part".format(media_folder, game, episode)):
        logging.debug("%s%s-E%s.a is partially downloaded. Removing", media_folder, game, episode)
        try:
            os.remove("{}{}-E{}.a.part".format(media_folder, game, episode))
        except OSError as err:
            logging.error("Could not remove %s%s-E%s.a.part: %s", media_folder, game, episode, err)
    if not os.path.exists("{}{}-E{}.a".format(media_folder, game, episode)):
        ytdl_options_audio = {"format": "bestaudio",
                              "quiet": True,
                              "outtmpl": media_folder + "{}-E{}.a".format(game, episode),
                              "playlist_items": str(episode)}
        ytdl_a = youtube_dl.YoutubeDL(ytdl_options_audio)
        ytdl_a.download(["https://www.youtube.com/playlist?list=" + playlist])
        logging.info("Download of %s-E%s complete", game, episode)

    return

def stream_standby(standby_directory, ffmpeg_opts):
    video = random.choice(os.listdir(standby_directory))
    while True:
        try:
            logging.info("Starting standby video %s", video)
            ffmpeg.input(standby_directory + video, re=None).output(ffmpeg_opts['filename'],
                                                                    format=ffmpeg_opts['format'],
                                                                    vcodec="libx264",
                                                                    acodec="libmp3lame",
                                                                    minrate=ffmpeg_opts['minrate'],
                                                                    maxrate=ffmpeg_opts['maxrate'],
                                                                    crf=ffmpeg_opts['crf'],
                                                                    preset=ffmpeg_opts['preset'],
                                                                    audio_bitrate="128k",
                                                                    ar="44100",
                                                                    g="30").run()#quiet=True)
        except ffmpeg.Error as err:
            logging.error("Error while streaming %s: %s", video, err)
    return

def stream_video(media_folder, game_name, episode_number, overlay, ffmpeg_opts):
    overlay_input = ffmpeg.input(overlay)
    video = ffmpeg.input("{}{}-E{}.v".format(media_folder, game_name, episode_number), re=None).video.filter("scale", 1760, 990).filter("pad", 1920, 1080, 0, 90) .overlay(overlay_input)
    audio = ffmpeg.input("{}{}-E{}.a".format(media_folder, game_name, episode_number), re=None)
    try:
        logging.info("Starting episode %s-E%s", game_name, episode_number)
        ffmpeg.output(video,
                      audio,
                      ffmpeg_opts['filename'],
                      format=ffmpeg_opts['format'],
                      vcodec=ffmpeg_opts['vcodec'],
                      acodec=ffmpeg_opts['acodec'],
                      minrate=ffmpeg_opts['minrate'],
                      maxrate=ffmpeg_opts['maxrate'],
                      bufsize=ffmpeg_opts['bufsize'],
                      crf=ffmpeg_opts['crf'],
                      preset=ffmpeg_opts['preset'],
                      audio_bitrate=ffmpeg_opts['audio_bitrate'],
                      ar=ffmpeg_opts['ar'],
                      g=ffmpeg_opts['g'])\
              .run()#quiet=True)
    except ffmpeg.Error as err:
        logging.error("Error while streaming %s-E%s: %s", game_name, episode_number, err)
    return

def media_files_exist(media_folder, game_name, episode_number):
    return os.path.exists("{}{}-E{}.v".format(media_folder, game_name, episode_number)) and os.path.exists("{}{}-E{}.a".format(media_folder, game_name, episode_number))

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

    zanarkand_defaults = {
        "CurrentStatusFile": "/opt/Zanarkand/current_status.txt",
        "Overlay": "/opt/Zanarkand/media/1080overlay.png",
        "PlaylistsFile": "/opt/zanarkand/playlist.conf",
        "LogFile": "/opt/Zanarkand/log/Zanarkand.log",
        "StandbyDirectory": "/opt/Zanarkand/standby/",
        "MediaFolder": "/opt/Zanarkand/media",
        "NumberOfDownloads": 3
        }

    zanarkand_config = SafeConfigParser(zanarkand_defaults)
    try:
        zanarkand_config.read(args.config)
    except ParsingError as e:
        print("Could not open configuration file {}: {}".format(args.config, e))
        sys.exit(1)

    # Youtube Key
    try:
        youtube_key = zanarkand_config.get("youtube", "StreamKey")
    except NoSectionError, NoOptionError:
        print("No streamkey found. Needs to be in the {} file under a section named \"youtube\" with an option named \"StreamKey\"".format(args.config))
        sys.exit(2)

    # Stream Config
    current_status = zanarkand_config.get("Zanarkand", "CurrentStatusFile")
    overlay = zanarkand_config.get("Zanarkand", "Overlay")
    playlists = zanarkand_config.get("Zanarkand", "PlaylistsFile")
    log_destination = zanarkand_config.get("Zanarkand", "LogFile")
    standby_directory = zanarkand_config.get("Zanarkand", "StandbyDirectory")
    media_folder = zanarkand_config.get("Zanarkand", "MediaFolder")
    number_of_downloads = zanarkand_config.getint("Zanarkand", "NumberOfDownloads")

    # Set up logging
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, filemode='a', filename=log_destination, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logging.info("Starting Stream...")

    #ffmpeg config
    ffmpeg_opts = {
        "audio_bitrate": zanarkand_config.get("ffmpeg", "AudioBitrate") if zanarkand_config.has_option("ffmpeg", "AudioBitrate") else "128k",
        "ar": zanarkand_config.get("ffmpeg", "AudioFrequency") if zanarkand_config.has_option("ffmpeg", "AudioFrequency") else "44100",
        "acodec": zanarkand_config.get("ffmpeg", "AudioCodec") if zanarkand_config.has_option("ffmpeg", "AudioCodec") else "libmp3lame",
        "vcodec": zanarkand_config.get("ffmpeg", "VideoCodec") if zanarkand_config.has_option("ffmpeg", "VideoCodec") else "libx264",
        "g": zanarkand_config.get("ffmpeg", "GroupOfPictures") if zanarkand_config.has_option("ffmpeg", "GroupOfPictures") else "30",
        "minrate": zanarkand_config.get("ffmpeg", "MinBitRate") if zanarkand_config.has_option("ffmpeg", "MinBitRate") else "5000K",
        "maxrate": zanarkand_config.get("ffmpeg", "MaxBitRate") if zanarkand_config.has_option("ffmpeg", "MinBitRate") else "6000K",
        "bufsize": zanarkand_config.get("ffmpeg", "BufRate") if zanarkand_config.has_option("ffmpeg", "BufRate") else "12000K",
        "preset": zanarkand_config.get("ffmpeg", "Preset") if zanarkand_config.has_option("ffmpeg", "Preset") else "superfast",
        "crf": zanarkand_config.get("ffmpeg", "CRF") if zanarkand_config.has_option("ffmpeg", "CRF") else "18",
        "filename": "rtmp://a.rtmp.youtube.com/live2/{}".format(youtube_key),
        "format": "flv"}

    standby_directory = standby_directory + "/" if not standby_directory.endswith('/') else standby_directory
    #Check media folder
    media_folder = media_folder + "/" if not media_folder.endswith('/') else media_folder
    if not os.path.exists(media_folder):
        logging.error("Media folder not found: %s", media_folder)
        sys.exit(3)

    # Get games list
    games_configs = SafeConfigParser()
    try:
        games_configs.read(playlists)
    except ParsingError as err:
        logging.error("Could not parse playlist configuration file %s: %s", playlists, err)
        sys.exit(1)

    current_video = SafeConfigParser()
    try:
        current_video.read(current_status)
    except ParsingError as err:
        logging.error("Could not parse current status file %s: %s", current_status, err)
        sys.exit(1)

    stream = Stream(games_configs)
    stream.update_status(current_video)

    while True:
        #Update current config
        current_video.set("current", "Game", stream.game.name)
        current_video.set("current", "Episode", str(stream.episode))
        current_video.set("current", "Loop", str(stream.loop))
        current_video.set("current", "Position", str(stream.position))
        with open(current_status, 'w') as f:
            current_video.write(f)

        if not media_files_exist(media_folder, stream.game.name, stream.episode):
            logging.warning("Could not find media files for %s-E%s. Switching to standby", stream.game.name, stream.episode)
            default_stream = Process(target=stream_standby, args=(standby_directory, ffmpeg_opts))
            default_stream.daemon = True
            default_stream.start()
            download_episode = Process(target=yt_download_episode, args=(stream.game.playlist_id, stream.game.name, stream.episode, media_folder,))
            download_episode.start()
            download_episode.join()
            kill_process(default_stream.pid)
        streaming = Process(target=stream_video, args=(media_folder, stream.game.name, stream.episode, overlay, ffmpeg_opts,))
        streaming.start()

        # Download next N episodes
        for download_game, download_playlist, download_episode in stream.get_next_n_episodes(number_of_downloads):
            if not media_files_exist(media_folder, download_game, download_episode):
                download = Process(target=yt_download_episode, args=(download_playlist, download_game, download_episode, media_folder,))
                download.start()

        # Wait until Stream ends
        streaming.join()

        # Remove file
        try:
            os.remove(media_folder + "{}-E{}.v".format(stream.game.name, stream.episode))
            os.remove(media_folder + "{}-E{}.a".format(stream.game.name, stream.episode))
        except OSError as err:
            logging.error("Could not remove the media files for %s-E%s: %s", stream.game.name, stream.episode, err)

        # Set up for next episode
        stream.next()

if __name__ == "__main__":
    main()
