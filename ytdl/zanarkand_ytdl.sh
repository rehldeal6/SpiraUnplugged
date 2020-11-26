#!/bin/bash

for EXTENSION in v a
do
    if [[ "$EXTENSION" == "a" ]]; then
        FORMAT=${YTDL_AUDIOID:-bestaudio}
    else
        FORMAT=${YTDL_VIDEOID:-bestvideo}
    fi
    FILENAME="/media/$YTDL_PLAYLIST-E$YTDL_EPISODE.$EXTENSION"
    if [[ -f $FILENAME.part ]]; then
        echo "$FILENAME is partially downloaded. Removing"
        rm -f $FILENAME
    fi
    if [[ ! -f $FILENAME ]]; then
        echo "Downloading $FILENAME"
        if [[ "${YTDL_TYPE^^}" == "PLAYLIST" ]]; then
            youtube-dlc \
            --no-cache-dir \
            --limit-rate 6291456 \
            --format $FORMAT \
            --output "$FILENAME" \
            --playlist-items $YTDL_EPISODE \
            https://www.youtube.com/playlist?list=$YTDL_URL
        else
            youtube-dlc \
            --no-cache-dir \
            --limit-rate 6291456 \
            --format $FORMAT \
            --output "$FILENAME" \
            https://www.youtube.com/watch?v=$YTDL_URL
        fi
    sleep 5
    fi
    if [[ ! -f $FILENAME ]]; then
        echo "COULD NOT DOWNLOAD $FILENAME"
    fi
done

