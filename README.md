# SpiraUnplugged

## Overview
Welcome to the stream that never sleeps! This software is essentially a Remake/Remaster of Topher's beautiful program that has keep the stream alive for over a year. Due to Topher not being around anymore to help debug issues that we've seen with the stream, we decided to re-write the software for a few reasons.
1. Topher's software on the server is compiled. This means that we are unable to make any changes or read the code to see what he's doing.
2. Python is a little bit easier to read (if anyone cared to read it) and the code can be edited on the server. After a restarting the software, the change takes place
3. Berk had a few new ideas and upgraded for the stream. If we wanted to incorporate these changes, we pretty much had to re-write the software.
After Berk and I have debugged some of the issues that we had to deal with, we had a good general idea of what the software was doing. So this code doesn't do everything the same way Topher's program executed things, but the end result is the same, along with my additions.

## Components
There are three main pieces of software that this program uses that are essential for the stream:
1. [ffmpeg](https://www.ffmpeg.org/) - "A complete, cross-platform solution to record, convert and stream audio and video."
2. [youtube-dl](https://ytdl-org.github.io/youtube-dl/index.html) - "A command-line program to download videos from YouTube.com"
3. This software :)

## Folder Structure and File Information
The main bulk of the code and files are stored on the server in the `/opt/zanarkand/` directory. From there, there are specific and important directories that need to exist:
```console
/opt/zanarkand/
               config.yml
               current_status.yml
               zanarkand.py
               fonts/
               logs/
               media/
               resources/
               standby/
```
* `config.yml` - Contains all of the stream configuration. Options should hopefully be self explanatory, and should really only be updated if there's a new playlist or video to add, or if the stream quality needs to go up/down.
* `current_status.yml` - Contains the information about the current video being played. Used when the stream software is restarted so it knows where to pick up from.
* `zanarkand.py` - The main piece of software.
* `fonts/` - Directory containing the fonts files (The one that we mostly use is `agency-fb-bold.ttf`)
* `logs/` - Directory containing the log files written by the stream software
* `media/` - Directory containing the audio and video files of the youtube videos
* `resources` - Directory containing additional resources needed for the stream (overlay image, standby video, etc.)
* `standby` - Directory containing the pre-downlowned videos used for standby

There are a few other files that are used by the stream...
`/lib/systemd/system/zanarkand.service` - A file that makes the stream software a system service, makes it easier to stop/start/restart the software.
`/etc/logrotate.d/zanarkand` - A file that "rotates" the log file, so that it doesn't continuously grow forever and eat up disk space.

## Controlling the stream
Due to that `zanarkand.service` file, it's now super easy to start, stop, and restart the stream on the command line. 
### Start the stream
```console
sudo systemctl start zanarkand
```

### Stop the stream
```console
sudo systemctl stop zanarkand
```

### Restart the stream
```console
sudo systemctl restart zanarkand
```

### View the log files
```console
tail -f /opt/zanarkand/logs/zanarkand.log
```

If you are using a desktop environment for the stream, then there should be executables you can double click that will perform these same actions.;


## Debugging the stream
This part of the README is designed to grow as we come across problems related to this software. We should document any fixes to the stream here.

### Youtube-dl needs updating
The most common issue that we come across is that youtube-dl needs updating. When this happens, the stream fails to download the upcoming episodes. The tech-support discord channel should be notified when this occues and the stream _should_ try to automatically update. If this still fails, perform the following on the stream command line.
```console
sudo youtube-dl -U
```
or
```console
sudo pip install youtube-dl --upgrade
```

Afterwards, [restart the stream](restart-the-stream)
