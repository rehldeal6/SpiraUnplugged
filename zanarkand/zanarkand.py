#!/usr/bin/env python3
#TODO: - Check to see if ffmpeg can start a video on a specific timestamp
#      - Add in bot to send messages to YT stream chat

# Standard imports
import os
import logging
from time import sleep
from argparse import ArgumentParser

# Third party imports
import docker
from yaml import safe_load, YAMLError, safe_dump

def find_containers(name, label=None):
    '''
    Return the list of containers with a given name
    '''
    client = docker.from_env()
    labels = []
    if label:
        for k, v in label.items():
            labels.append("{}={}".format(k, v))
    return client.containers.list(all=True,
                                  filters={"name": name.replace(" ", "_"),
                                           "label": labels})

def remove_containers(name):
    '''
    Removes a container with a given name
    '''
    client = docker.from_env()
    containers = client.containers.list(all=True, filters={"name": name.replace(" ", "_")})
    for container in containers:
        if container.status == "running":
            container.stop()
    container.remove()

def media_files_exist(media, episode):
    '''
    Check if both audio and video file exists for a particular episode of media
    '''
    return (os.path.exists("/media/{}-E{}.v".format(media, episode)) and os.path.exists("/media/{}-E{}.a".format(media, episode)))

class Stream:
    '''
    Overall stream object. It contains information about what's currently being played, the order of media to play,
    current loop, etc.
    '''
    def __init__(self):
        '''
        Create the stream object

        Inputs:
        order               [list] Order of media to play
        media_dictionary    [dict] Dictionary of Media objects
        position            [int]  Current position in order
        episode             [int]  First episode to play
        loop                [int]  Loop order
        '''

        # Get configuration settings
        with open("/resources/config.yml") as input_config:
            try:
                config = safe_load(input_config)
            except YAMLError as yerr:
                logging.error("Couldn't read yaml config file: %s", yerr)
        # Check mandatory options:
        for mandatory in ["order", "sections"]:
            if mandatory not in config:
                logging.error("Mandatory option %s is not in the config file", mandatory)

        # Get current status
        with open("/resources/status.yml", 'r') as input_status:
            try:
                status = safe_load(input_status)
            except YAMLError as yerr:
                logging.error("Couldn't read the yaml config file: %s", yerr)

        self.order = config["order"]
        self.sections = config["sections"]
        self.position = status.get("position", 1)
        self.media = self.order[self.position - 1]
        self.episode = status.get("episode", 1)
        self.loop = status.get("loop", 1)
        self.download_number = int(os.environ["NUMBER_OF_DOWNLOADS"])
        self.webhook = os.environ["DISCORD_WEBHOOK"]
        self.download_attempts = 0
        self.previous_media = None
        self.previous_episode = None
        self.next_container = None
        self.current_container = None
        self.set_subtitles()

        initial_container = find_containers("ffmpeg_initial_standby")
        if not initial_container:
            self.initial_container = self.create_ffmpeg(1)
        else:
            self.initial_container = initial_container[0]

        longer_container = find_containers("ffmpeg_longer_standby")
        if not longer_container:
            self.longer_container = self.create_ffmpeg(2)
        else:
            self.longer_container = longer_container[0]

    def next_video(self):
        '''
        Set the stream to play the next episode
        '''
        self.current_container = self.next_container
        self.download_attempts = 0
        # Delete previous episodes
        if self.previous_media and self.previous_episode:
            remove_containers("ffmpeg_{}_E{}".format(self.previous_media, self.previous_episode))
            try:
                os.remove("/media/{}-E{}.v".format(self.previous_media, self.previous_episode))
                os.remove("/media/{}-E{}.a".format(self.previous_media, self.previous_episode))
            except OSError as err:
                logging.error("Could not remove the media files for %s-E%s: %s", self.media, self.episode, err)

        self.previous_episode = self.episode
        self.previous_media = self.media
        if self.episode < self.sections[self.media].get("ending"):
            self.episode += 1
            while (self.episode in self.sections[self.media].get("exclude", [])
                   and self.episode < self.sections[self.media].get("ending")):
                self.episode += 1
        else:
            if self.loop < self.sections[self.media].get("loops", 1):
                self.loop += 1
            else:
                self.loop = 1
                if self.position != len(self.order):
                    self.position += 1
                else:
                    self.position = 1
                self.media = self.order[self.position - 1]
            self.episode = self.sections[self.media].get("beginning", 1)
        if not find_containers("ffmpeg_{}_E{}".format(self.media, self.episode)):
            self.next_container = self.create_ffmpeg(0, self.media, self.episode)

    def download_next_n_episodes(self):
        '''
        Get the next N episodes and download them preemptively

        Inputs:
        number          [int] Number of episodes ahead to download
        webhook         [str] Discord webhook for notifications
        '''
        download_episode = self.episode
        download_media = self.media
        download_loop = self.loop
        download_position = self.position
        for _ in range(1, self.download_number + 1):
            if download_episode < self.sections[download_media].get("ending"):
                download_episode += 1
                while (download_episode in self.sections[download_media].get("exclude", [])
                       and download_episode < self.sections[download_media].get("ending")):
                    download_episode += 1
            else:
                if download_loop < self.sections[download_media].get("loops", 1):
                    download_loop += 1
                else:
                    download_loop = 1
                    if download_position == len(self.order):
                        download_position = 1
                    else:
                        download_position += 1
                    download_media = self.order[download_position - 1]
                download_episode = self.sections[download_media].get("beginning", 1)
            if not media_files_exist(download_media, download_episode) and not find_containers("ytdl_{}_E{}".format(download_media, download_episode)):
                self.run_ytdl(download_media, download_episode)

    def set_subtitles(self):
        '''
        Create "subtitles" that display the order of the games

        Inputs:
        ffmpeg_opts         [dict] Dictionary of ffmpeg options used
        '''
        before_games = []
        for game in self.order[:self.position-1]:
            if self.sections[game]["type"] == "playlist":
                before_games.append(game)
        before = " -> ".join(before_games)
        if before:
            before += " -> "
        after_games = []
        for game in self.order[self.position:]:
            if self.sections[game]["type"] == "playlist":
                after_games.append(game)
        after = " -> ".join(after_games)
        if after:
            after = " -> " + after
        if self.sections[self.media]["type"] == "playlist":
            current_game = "{} (Ep {}/{} Loop {}/{})".format(self.media,
                                                             self.episode,
                                                             self.sections[self.media]["ending"],
                                                             self.loop,
                                                             self.sections[self.media].get("loops", 1))
        else:
            current_game = self.media
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
            with open('/resources/template.ass', 'r') as st:
                content = st.read().rstrip()
            content += dialogue
            with open('/resources/final.ass', 'w') as sf:
                sf.write(content)
        except IOError as ioe:
            logging.error("Couldn't open or write script file: %s", ioe)

    def run_ytdl(self, media, episode):
        '''
        Create a ytdl container that will download a specific episode

        Inputs:
        media:      <str> Media playlist to choose from
        episode:    <int> Episode number to download
        '''
        client = docker.from_env()
        env_dict = {"YTDL_PLAYLIST": media,
                    "YTDL_EPISODE": str(episode),
                    "YTDL_TYPE": self.sections[media]["type"].upper(),
                    "YTDL_URL": self.sections[media]["id"],
                    "YTDL_VIDEOID": str(self.sections[media].get("videoformatid", "bestvideo")),
                    "YTDL_AUDIOID": str(self.sections[media].get("audioformatid", "bestaudio")),
                    "DISCORD_WEBHOOK": os.environ["DISCORD_WEBHOOK"]}
        logging.info("Starting ytdl container to download %s E%s", media, episode)
        return client.containers.run(name="ytdl_{}_E{}".format(media.replace(" ", "_"), episode),
                                     image="ytdl",
                                     detach=True,
                                     environment=env_dict,
                                     remove=True,
                                     volumes_from=["zanarkand"])

    def create_ffmpeg(self, standby, media=None, episode=None):
        '''
        Create an container based off the ffmpeg image

        Inputs:
        standby     <int> 0 for not standby, 1 for initial standby, 2 for longer standby
        media       <str> Media playlist to choose from
        episode:    <int> Episode number to play
        '''
        client = docker.from_env()
        env_dict = {"YOUTUBE_KEY": os.environ["YOUTUBE_KEY"],
                    "STREAM_STANDBY": standby,
                    "DISCORD_WEBHOOK": os.environ["DISCORD_WEBHOOK"],
                    "FFMPEG_VIEWPORT_WIDTH": os.environ["FFMPEG_VIEWPORT_WIDTH"],
                    "FFMPEG_VIEWPORT_HEIGHT": os.environ["FFMPEG_VIEWPORT_HEIGHT"],
                    "FFMPEG_VIEWPORT_X": os.environ["FFMPEG_VIEWPORT_X"],
                    "FFMPEG_VIEWPORT_Y": os.environ["FFMPEG_VIEWPORT_Y"],
                    "FFMPEG_RESOLUTION_WIDTH": os.environ["FFMPEG_RESOLUTION_WIDTH"],
                    "FFMPEG_RESOLUTION_HEIGHT": os.environ["FFMPEG_RESOLUTION_HEIGHT"],
                    "FFMPEG_FORMAT": os.environ["FFMPEG_FORMAT"],
                    "FFMPEG_VCODEC": os.environ["FFMPEG_VCODEC"],
                    "FFMPEG_ACODEC": os.environ["FFMPEG_ACODEC"],
                    "FFMPEG_MINRATE": os.environ["FFMPEG_MINRATE"],
                    "FFMPEG_MAXRATE": os.environ["FFMPEG_MAXRATE"],
                    "FFMPEG_BUFSIZE": os.environ["FFMPEG_BUFSIZE"],
                    "FFMPEG_CRF": os.environ["FFMPEG_CRF"],
                    "FFMPEG_PRESET": os.environ["FFMPEG_PRESET"],
                    "FFMPEG_AUDIO_BITRATE": os.environ["FFMPEG_AUDIO_BITRATE"],
                    "FFMPEG_AR": os.environ["FFMPEG_AR"],
                    "FFMPEG_G": os.environ["FFMPEG_G"]}
        label_dict = {"standby": str(standby), "image": "ffmpeg"}
        if standby == 0:
            env_dict["FFMPEG_PLAYLIST"] = media
            env_dict["FFMPEG_EPISODE"] = str(episode)
            container_name = "ffmpeg_{}_E{}".format(media.replace(" ", "_"), episode)
            label_dict["playlist"] = media
            label_dict["episode"] = str(episode)
        elif standby == 1:
            container_name = "ffmpeg_initial_standby"
        elif standby == 2:
            container_name = "ffmpeg_longer_standby"
        logging.info("Creating ffmpeg container %s", container_name)
        return client.containers.create(name=container_name,
                                        image="ffmpeg",
                                        detach=True,
                                        environment=env_dict,
                                        labels=label_dict,
                                        volumes_from=["zanarkand"])

    def update_status(self):
        # Update status
        with open("/resources/current_status.yml", 'w') as write_status:
            safe_dump({'game': self.media, 'position': self.position, 'episode': self.episode, 'loop': self.loop},
                      write_status,
                      default_flow_style=False)

def main():
    '''
    main
    '''
    client = docker.from_env()
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", help="Enabled debug mode", action="store_true")
    args = parser.parse_args()

    # Set up logging
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    logging.info("Starting Stream...")

    # Create the stream object
    stream = Stream()

    startup_container = None
    containers = client.containers.list(all=True, filters={"label": ["standby=0", "image=ffmpeg"]})
    for container in containers:
        if container.status != "running":
            container.stop()
            container.remove()
    containers = client.containers.list(filters={"label": ["standby=0", "image=ffmpeg"]})
    if len(containers) == 0:
        stream.next_container = stream.create_ffmpeg(0, stream.media, stream.episode)
    elif len(containers) == 1:
        container = containers[0]
        if container.name == "ffmpeg_{}_E{}".format(stream.media.replace(" ", "_"), stream.episode):
            stream.next_container = container
        else:
            startup_container = container
            stream.next_container = stream.create_ffmpeg(0, stream.media, stream.episode)
    else:
        logging.error("More than one episode is playing. Please clean up ")
        return 2

    while True:
        #Run the standby if the files don't exist
        while not media_files_exist(stream.media, stream.episode):
            stream.next_container.reload()
            stream.initial_container.reload()
            stream.longer_container.reload()
            #Check to see if we attempted to download the episode too many times
            if stream.download_attempts < int(os.environ.get("MAX_DOWNLOAD_ATTEMPTS", 5)):
                #Check to see if we're already attempting to download the episode
                if not find_containers("ytdl_{}_E{}".format(stream.media, stream.episode)):
                    #Create the container to download the episode
                    logging.info("Creating container ytdl_{}_E{}".format(stream.media, stream.episode))
                    ytdl = stream.run_ytdl(stream.media, stream.episode)
                    stream.download_attempts += 1
                # If an episode was already running, let it keep running
                if startup_container:
                    startup_container.reload()
                    if startup_container.status != "running" and stream.longer_container.status != "running":
                        stream.initial_container.start()
                        startup_container = None
                # Otherwise, run the initial standby container
                else:
                    if stream.longer_container.status != "running":
                        stream.initial_container.start()
            else:
                # If an episode was already running, let it keep running
                if startup_container:
                    startup_container.reload()
                    if startup_container.status != "running":
                        stream.initial_container.stop()
                        stream.longer_container.start()
                # Otherwise, start the longer standby
                else:
                    stream.initial_container.stop()
                    stream.longer_container.start()
            ytdl_containers = client.containers.list(filters={"name": "ytdl"})
            for container in ytdl_containers:
                if container.name != "ytdl_{}_E{}".format(stream.media.replace(" ", "_"), stream.episode):
                    container.stop()

        if startup_container:
            startup_container.stop()
            startup_container.remove()
            startup_container = None
        # Stream the episode!
        stream.next_container.start()
        logging.info("Starting container %s", stream.next_container.name)

        stream.initial_container.stop()
        stream.longer_container.stop()

        # Update the status file
        stream.update_status()
        # Download the next episodes
        stream.download_next_n_episodes()
        # Set up for the next video
        stream.next_video()

        # Sleep so that the video plays the correct subtitles
        sleep(5)
        #Set the subtitles for the next video
        stream.set_subtitles()

        # Wait until ffmpeg container stops
        stream.current_container.wait()

if __name__ == "__main__":
    main()
