#!/bin/sh

FILENAME='fft.bin'
if [ $# -gt 0 ] ; then
    FILENAME=$1
fi

if [ $# -gt 2 ] ; then
    INPUTPATH=$2
    OUTPUTPATH=$3
else
    INPUTPATH=
    while true ; do
        read -r -p "enter the path to the directory containing your $FILENAME disk image file: " INPUTPATH
        if [ -d "$INPUTPATH" ] ; then
            break
        fi
        echo "$INPUTPATH is not a directory..."
    done

    OUTPUTPATH=
    while true ; do
        read -r -p "enter the path your randomized seed should go to: " OUTPUTPATH
        if [ -d "$OUTPUTPATH" ] ; then
            break
        fi
        echo "$OUTPUTPATH is not a directory..."
    done
fi

docker build --tag fft_rcc .

IMAGEID=$(docker images fft_rcc --format='{{.ID}}' | head -1)
echo && echo "folder with your fft.bin: $INPUTPATH"
echo "output folder: $OUTPUTPATH"
echo "your image id: $IMAGEID" && echo
echo "Randomizing now"

docker run -it --rm -e filename=${FILENAME} -v `pwd`/${INPUTPATH}:/input -v `pwd`/${OUTPUTPATH}:/output ${IMAGEID}
