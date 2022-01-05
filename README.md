# SpiraUnplugged

## Overview
Welcome to the stream that never sleeps! This software is essentially a Remake/Remaster of Topher's beautiful program that has kept the stream alive for over a year. Due to Topher not being around anymore to help debug issues that we've seen with the stream, we decided to re-write the software for a few reasons.
1. Topher's software on the server is compiled. This means that we are unable to make any changes or read the code to see what he's doing.
2. Python is a little bit easier to read (if anyone cared to read it) and the code can be edited on the server. After restarting the software, the change takes place
3. Berk had a few new ideas and upgrades for the stream. If we wanted to incorporate these changes, we pretty much had to re-write the software.
After Berk and I have debugged some of the issues that we had to deal with, we had a good general idea of what the software was doing. So this code _doesn't_ perform everything the same way Topher's program executed things, but the end result is the same along with some updates.

***NOTE:*** Most, if not all, of these commands assumes you are in the directory containing this github repository.

## Components
There are four main pieces of software that this program uses that are essential for the stream:
1. [ffmpeg](https://www.ffmpeg.org/) - "A complete, cross-platform solution to record, convert and stream audio and video."
2. [yt-dlp](https://github.com/yt-dlp/yt-dlp) - "A command-line program to download videos from YouTube.com"
3. zanarkand.py - The software I wrote that brings everything together.
4. [docker](https://www.docker.com/resources/what-container) - Software bundling

## Starting from scratch
So you decided you want to use this software, eh? Well props to you, I think! Here's what you need to do in order for things to get running. This is all assuming you have some version of Ubuntu installed (probably `18.04` or later) and have access to the command line for the server; either through the desktop and bringing up a **Terminal** application or connecting through SSH. All commands also assume you're **NOT** root. You shouldn't be logging in as root directly anyway. If you logged in as `root` and need to make a user, issue the following command
```console
# useradd <username>
# passwd <username>
(Enter in password for the new user)
```
Then log out as root and re-log in as the new user. 

### Getting the software
First think you need to do is install `git` so you can clone this software locally onto the server. You can do this with the following command:
```console
$ sudo apt install -y git
```
Assuming you have a github account to access this repo, you need to connect your Github account to your user account on the Ubuntu server.
First, run a command to generate **SSH Keys**:
```console
$ ssh-keygen
```
You can just keep hitting enter to use the default values. Once that is completed, obtain your **public SSH key**:
```console
$ cat ~/.ssh/id_rsa.pub
```
Once you have that value, log into github via a web browser. Click on your user icon in the top right and select **Settings**. Select **SSH and GPG Keys** on the left side, then **Add SSH Key** up top of the new window. Add whatever you want to title the new key, and paste in the contents of the command before.

There's one more small step to perform on the linux side to be able to use git:
```console
$ git config --global user.name "John Doe"
$ git config --global user.email johndoe@example.com
```
Just rpelace your name and email with your values (could be fake values, idc).

Now you can clone the github repository on the new server.
```console
$ cd
$ git clone git@github.com:rehldeal6/SpiraUnplugged.git zanarkand
```
This will create a new folder in your home directory called `zanarkand` with the contents of this github repository. 

### Installing Docker
Docker is needed in order to run the zanarkand software. It makes it extremely easy to run everything. Instead of installing dependencies, making sure different software versions are compatible with each other, etc, docker just runs an "image" as a "container". The image we will run will include all of the necessary software needed to run the stream. A container is a running instance of an image. It's a little confusing, but you don't really need to know the nitty-gritty.
Rather than repeating lots of the same instructions, just follow [these steps](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository) to install Docker on Ubuntu. Your architecture will most likely be **x86_64/amd64**. 
Once the software is installed, add your username to the **docker** group.
```console
$ sudo usermod -aG docker <your username>
```
This will require you to log out of the server and re-log in. 

### Installing Docker-Compose
One last thing needed is an additional piece of software for Docker called **docker-compose**. This makes controlling the container much simpler. 
[This link](https://docs.docker.com/compose/install/#install-compose-on-linux-systems) contains the commands to install docker-compose on the server.

### Setting up
I made a script that should create everything needed to run the stream. There is a file called `setup.sh` located where you pulled the git repository.
```console
./setup.sh
```
This will take quite some time for the downloads the complete. 
Once you have this completed, that's it! You now have all of the necessary peices for running the stream. To get started with running the stream, go to [Controlling the stream](#controlling-the-stream)

### Folder Structure and File Information
The main bulk of the code and files are stored on the server in the `/opt/zanarkand/` directory. From there, there are specific and important directories that need to exist:
```
zanarkand/
          ffmpeg/
          ytdl/
          zanarkand/
          resources/
          media/
          standby/
          docker-compose.yml
          docker-compose.override.yml
          docker-compose.dev.yml
          setup.sh
```
* `ffmpeg/` - Directory containing everything needed to build the `ffmpeg` image. This image is used to stream the downloaded media to youtube
* `ytdl/` - Directory containing everything needed to build the `ytdl` image. This image is used to download videos from youtube
* `zanarkand/` - Directory containing everything needed to build the `zanarkand` image. This is the scheduler that controls the `ffmpeg` and `ytdl` images. 
* `media/` - Directory containing the audio and video files of the youtube videos
* `resources/` - Directory containing additional resources needed for the stream (configs, overlay image, subtitles, etc.)
* `standby/` - Directory containing the pre-downlowned videos used for standby

Required files in `resources`:
***NOTE*** If these files do not exist, the stream will fail to run!
* `config.yml` - Contains the order of videos to play along with information about each video
* `status.yml` - Contains information about the current video playing. When the stream starts, this is where it knows where to start off
* `template.ass` - Template subtitle file. 
* `standby.flv` - Pre-downloaded initial standby video.
* `overlay.png` - Overlay image

### Building the images
Three images are used within this software: `zanarkand`, `ffmpeg`, and `ytdl`. The folders with the same names are used to create the images. All three need to be created in order for anything to work. To create these images:
1. start within the directory pulled from github.
2. Go inside the directory of the image
```console
$ cd ffmpeg/
```
3. Use this command to build the image and tag it with a name
```console
$ docker image build -t ffmpeg . --no-cache
```
4. (Optional) Go up a directory so you can navigate to the other folders (`ytdl`, `zanarkand`)
```console
$ cd ..
```

## Controlling the stream
The stream is being run by the `docker` software. Docker uses the images defined in this github repository. This images contains all of the required software that is needed in order to run the stream. The docker images will only be updated in a developement environment, and the production server will rebuild the image locally. In order to run the following commands, your user account needs to be in the `docker` group on the server. If your user is not in the group, run the command `sudo usermod -aG docker <your username>`.

### Container overview
There are multiple images that get run out of this software: `zanarkand`, `ffmpeg`, and `ytdl`:
* `zanarkand` - schedules which video to stream and download
* `ffmpeg` - performs the actual streaming of a video
* `ytdl` - downloads videos from youtube.

The `docker-compose` commands below _ONLY_ control the `zanarkand` container by design. This helps the stream to continue to run even if we make updates to the schedule or code. If you view all of the containers running during the stream, you'll see multiple containers running at once. There are a few that get automatically generated:
* `zanarkand` - the main container that does the scheduling
* `ffmpeg_initial_standby` - a `ffmpeg` container that's configured specifically to run the initial standby video
* `ffmpeg_longer_standby` - a `ffmpeg` container that's configured specifically to run the longer standby videos

There are other containers that get automatically created and deleted as needed:
* `ffmpeg_<game>_E<episode>` - a `ffmpeg` container that's running the current episode
* `ffmpeg_<next game>_E<next episode>` - a stopped `ffmpeg` container that is ready to run the next episode
* `ytdl_<game>_E<episode>` - a `ytdl` container that's downloading a particular episode

The `ytdl` containers are not always listed, because the software is not always downloading episodes; it's created when needed (like at the start of each episode). 

If you want to specifically stop a container from running, say you want to stop the current episode from being played, there's an easy command to do it:
```console
$ docker container ls -a
```
to list the containers. The names are the last column on each line.
To stop a container:
```console
$ docker container stop <container name>
```
This will stop any container listed. Most containers are configured to be deleted after they've stopped, except for the main `zanarkand` container and the `ffmpeg_initial/longer_standby` containers.

STARTING a container is much more difficult, and it's best to let the zanarkand program to do all the work needed. It you want to START a container, change the values in `resources/status.yml` and set it to the desired episode.

### Before creating the docker containers
Make sure you follow the steps listed in [Starting from scratch](#starting-from-scratch). Once that is set up, make sure your youtube key is correct in `docker-compose.override.yml` in the line saying `- YOUTUBE_KEY=<key>`. 

### Note for developers
**Note**: If you are setting this up in a development environment, make sure you include the arguments `-f docker-compose.yml` and `-f docker-compose.dev.yml` in all of these commands below. This will ensure that you use the correct development environments. 
For example, to start the stream:
```console
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```
**Note #2**: Also make sure your `YOUTUBE_KEY` variable is set correctly in `docker-compose.dev.yml`. 

### Start the stream controller
**NOTE** This command needs to be run WITHIN the stream software directory
```console
docker-compose up -d
```
or
```console
docker-compose run zanarkand -d
```
To run it (not in detached mode) in debug mode (for development reasons)

### Stop the stream controller
**NOTE** This command needs to be run WITHIN the stream software directory
```console
docker-compose stop
```

### Restart the stream controller
**NOTE** This command needs to be run WITHIN the stream software directory
```console
docker-compose restart
```

### View the stream controller logs
```console
docker container logs zanarkand
```
or, if you want a live feed of the logs
```console
docker container logs -f zanarkand
```

## Common Tasks
### Changing the overlay
The overlay file is hardcoded to be `resources/overlay.png`. In order to make an update to that file, one needs to copy the file off the server, make the update, and put the file back onto the server in the correct location. A common program that can be used to transfer the file on or off the server is [WinSCP](https://winscp.net/eng/index.php). Once you enter in the server IP address and proper credentials, you can navigate to the file and transfer it to/from desktop. Once the overlay file has been updated, it will be applied to the next video in the stream.

### Changing the stream quality
The `ffmpeg` software can be tweaked to change the quality of the streaming video. The options with their default values are defined in `docker-compose.yml`. They can be either changed in that file or overridden in `docker-compose.override.yml` by adding the entry under `environment` (like how it is in `docker-compose.yml`). The most commong setting to change is the `preset` option. The `crf`, `groupofpictures` and some of the bitrate options are also configurable to the quality of the stream. [This ffmpeg link](https://trac.ffmpeg.org/wiki/Encode/H.264) shows the different values that can be used.

Another way to change the stream quality is to update the `videoformatid` and `audioformatid` options under `sections` section in `config.yml`. Each video or playlist has an option to specify the video or audio quality. Check out [this section](#view-all-of-the-formats-available-for-a-video) on how to option the types of video and audio formats available for each video or playlist.

If any of these values are updated, you need to [restart the stream](#restart-the-stream-controller).

### Change the stream schedule
The stream schedule is configured under the `order` section of `resources/config.yml`. Update the value as needed, but make sure that each entry in `order` **matches up with an entry under `sections`**. If there is something in `order` that does NOT match up with an entry in `sections`, the stream will not be able to start properly.

Once the update to the order has been made, [restart the stream](#restart-the-stream-controller).

### Changing the standby text
I should really make the standby text configurable, but for now it's hardcoded into the stream software. To update the text, one needs to edit the stream software file (`zanarkand.py`) which is located in `ffmpeg/zanarkand_ffmpeg.py`. After the update has been made, save the file. Then, [rebuild the image](#building-the-images).

### Checking if yt-dlp is up to date
See [Youtube-dl needs updating](#youtube-dl-needs-updating).

### Adding or changing videos that will play during standby
The list of standby videos are in `standby/`. These videos will be played after a set number of download attempts fail to download a video. The streaming software will randomly pick one of these videos in that directory to play during the downtime. To remove a video from being shown during standby, simply delete the video. To add a video to the directory, see [Downloading using a playlist](#downloading-using-a-playlist) or 
[Downloading a specific video](#downloading-a-specific-video). 
** PLEASE NOTE ** - When downloading a standby video, please make sure to add the `--output /opt/zanarkand/standby/%(title)s` option to the command. This will make sure the downloaded video will have the proper name.

### Changing the currently streaming video to play another video
Update `current_status.yml` to look like the following format:
```yaml
game: FFVII
episode: 2
loop: 1
position: 1
```
The order of the options may be different. The two options worth noting are `game` and `position`. The `game` option **has to match the game listed under `sections` in `config.yml`**. The `position` option refers to the order position we are in the stream. **FFVII** is the first game listed under `order` in `config.yml`, so it's listed as `position: 1`. This helps if there are any duplicate entries in `order`, like **FFX**. So if we were to update this file to play FFX after FFIX, episode 20, loop 1, we would make the following update:
```yaml
game: FFX
episode: 20
loop: 1
position: 8
```
since that specific instance of **FFX** is the **8th** entry under `order`. Once the update to the current status file has been made, [restart the stream](#restart-the-stream).

## Helpful commands
### Using Youtube-DL
The stream looks for videos in the `media/` folder. It looks for these videos in a specific format:
```
<game-name>-E<episode-number>.v
<game-name>-E<episode-number>.a
```
If it's a single video, it might look like this:
```
Intermission-E1.v
Intermission-E1.a
```
If you need to download a specific video, here's what you can do:

#### Downloading using a playlist
The use of docker containers made it a bit longer command to run, but since this is rarely used it's fine. This command also needs to be run within the github repository directory.
```console
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --playlist-items <episode-number> --format bestvideo --output "/media/<game-name>-E<episode-number>.v <playlist URL>"
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --playlist-items <episode-number> --format bestaudio --output "/media/<game-name>-E<episode-number>.a <playlist URL>"
```
Example command to download Episode 10 of the FFX playlist in the format the stream needs:
```console
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --playlist-items 10 --format bestvideo --output "/media/FFX-E10.v https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps"
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --playlist-items 10 --format bestaudio --output "/media/FFX-E10.a https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps"
```

#### Downloading a specific video
The use of docker containers made it a bit longer command to run, but since this is rarely used it's fine. This command also needs to be run within the github repository directory.
```console
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --format bestvideo --output /media/<game-name>-E<episode-number>.v <video URL>"
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --format bestaudio --output /media/<game-name>-E<episode-number>.a <video URL>"
```
Example command to download Episode 10 of the FFX playlist in the format the stream needs:
```console
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --format bestvideo --output /media/FFX-E10.v https://www.youtube.com/watch?v=xoLBwYgcsbk"
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --format bestaudio --output /media/FFX-E10.a https://www.youtube.com/watch?v=xoLBwYgcsbk"
```

#### View all of the formats available for a video
Youtube uses its own specific video format IDs to use for the `--format` option. To view the formats available for a video, run the following command:
```console
docker run --rm --entrypoint yt-dlp ytdl -F <video URL>
```
Example:
```console
docker run --rm --entrypoint yt-dlp ytdl -F https://www.youtube.com/watch?v=xoLBwYgcsbk
[youtube] xoLBwYgcsbk: Downloading webpage
[youtube] xoLBwYgcsbk: Downloading video info webpage
[info] Available formats for xoLBwYgcsbk:
format code  extension  resolution note
249          webm       audio only tiny   60k , opus @ 50k (48000Hz), 7.01MiB
250          webm       audio only tiny   80k , opus @ 70k (48000Hz), 9.24MiB
140          m4a        audio only tiny  129k , m4a_dash container, mp4a.40.2@128k (44100Hz), 18.66MiB
251          webm       audio only tiny  157k , opus @160k (48000Hz), 18.69MiB
278          webm       256x144    144p   98k , webm container, vp9, 30fps, video only, 11.50MiB
160          mp4        256x144    144p  113k , avc1.4d400c, 30fps, video only, 6.31MiB
242          webm       426x240    240p  230k , vp9, 30fps, video only, 19.23MiB
133          mp4        426x240    240p  245k , avc1.4d4015, 30fps, video only, 11.93MiB
243          webm       640x360    360p  416k , vp9, 30fps, video only, 35.82MiB
134          mp4        640x360    360p  634k , avc1.4d401e, 30fps, video only, 30.47MiB
244          webm       854x480    480p  771k , vp9, 30fps, video only, 61.96MiB
135          mp4        854x480    480p 1200k , avc1.4d401f, 30fps, video only, 59.63MiB
247          webm       1280x720   720p 1512k , vp9, 30fps, video only, 128.12MiB
136          mp4        1280x720   720p 2373k , avc1.4d401f, 30fps, video only, 109.89MiB
248          webm       1920x1080  1080p 2698k , vp9, 30fps, video only, 241.73MiB
137          mp4        1920x1080  1080p 4317k , avc1.640028, 30fps, video only, 206.44MiB
43           webm       640x360    360p , vp8.0, vorbis@128k, 102.34MiB
18           mp4        640x360    360p  490k , avc1.42001E, mp4a.40.2@ 96k (44100Hz), 72.09MiB
22           mp4        1280x720   720p  874k , avc1.64001F, mp4a.40.2@192k (44100Hz) (best)
```
So if we wanted to download a `1920x1080` mp4 video (format code `137`)  and the `m4a` audio (format code `140`), you would do the following (using FFX-E10 as an example):

```console
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --format 137 --output /media/FFX-E10.v https://www.youtube.com/watch?v=xoLBwYgcsbk
docker run --rm -v $(pwd)/media:/media --entrypoint yt-dlp ytdl --format 140 --output /media/FFX-E10.a https://www.youtube.com/watch?v=xoLBwYgcsbk
```

## Debugging the stream
This part of the README is designed to grow as we come across problems related to this software. We should document any fixes to the stream here.

### Youtube-dl needs updating
The most common issue that we come across is that yt-dlp needs updating. When this happens, the stream fails to download the upcoming episodes. The tech-support discord channel should be notified when this occues and the stream _should_ try to automatically update. If this still fails, the container image needs to be rebuilt. These commands will stop the stream, rebuild the image, and start it back up.

```console
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```
docker 

## TODOs
We can keep an official list of things we might want to add to the stream here
* A youtube bot that can let chat know that there's an issue
* Start a video at a specific timestamp
* Make the standby text configurable.
* Re-attempt downloading the correct video at the beginning of a random standby video
* Use docker-compose instead of just docker commands.
