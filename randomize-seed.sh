#!/bin/sh

INPUTPATH=
while true ; do
    read -r -p "enter the path to the directory containing your 'fft.bin' disk image file: " INPUTPATH
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

FLAGS=
    read -r -p "choose some randomizer flags [ujisayrtpwmcfzo]: " FLAGS
    FLAGS=${FLAGS:-ujisayrtpwmcfzo}
    echo "randomizing with flags $FLAGS"

CHAOS=
    read -r -p "please select your chaos (difficulty) level from 0.1 to 500.0 [1.0]: " CHAOS
    CHAOS=${CHAOS:-1.0}
    echo "chaos level is set to $CHAOS"

docker build .

IMAGEID=$(docker images --format='{{.ID}}' | head -1)
echo && echo "folder with your fft.bin: $INPUTPATH"
echo "output folder: $OUTPUTPATH"
echo "randomizer flags: $FLAGS"
echo "chaos level: $CHAOS"
echo "your image id: $IMAGEID" && echo
echo "Randomizing now"

docker run --rm -e flags=${FLAGS} -e chaos=${CHAOS} -v ${INPUTPATH}:/input -v ${OUTPUTPATH}:/output ${IMAGEID}
