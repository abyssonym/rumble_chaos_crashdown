#!/bin/sh

get_chaos_level() # no parameters
{
    read -r -p "Choose a chaos level from 0.1 to 7.0 [default 1.0]: " REQUESTEDCHAOS
    REQUESTEDCHAOS=${REQUESTEDCHAOS:-1.0}
    CHAOSISINRANGE=$(verify_in_range $REQUESTEDCHAOS 0.1 7.0)
    echo $CHAOSISINRANGE
}

get_directory() # parameters: a file path
{
    DESCRIPTION=$1
    read -r -p "Enter the path to the ${DESCRIPTION} directory: " REQUESTEDDIRECTORY
    if [ -d $REQUESTEDDIRECTORY ] ; then
        echo $REQUESTEDDIRECTORY
        return
        else echo "Error: The path '${REQUESTEDDIRECTORY} is not a directory"
        exit 1
    fi
}

get_disk_image()
{
    read -r -p "Enter the file name of your disk image of Final Fantasy Tactics [default: fft.bin]: " REQUESTEDNAME
    REQUESTEDNAME=${REQUESTEDNAME:-"fft.bin"}
    if [ -f $INPUTPATH/$REQUESTEDNAME ] ; then
        echo $REQUESTEDNAME
    else
        echo "Error: no file found at $INPUTPATH/$REQUESTEDNAME"
        exit 1
    fi
}

give_spoiler() # no parameters
{
    EXPORTSPOILER=false
    read -r -p "Output spoiler log [default: n]? " GETSPOILER
    case $GETSPOILER in
        [Yy]* ) EXPORTSPOILER=true ; echo "Spoiler log will be added to the output directory" ;;
        * ) echo "No spoiler log (Default)" ;;
    esac
}

get_seed() # no parameters
{
    read -r -p "Enter an optional 10-digit seed value [default: randomly chosen]: " REQUESTEDSEED
        if [ $( echo "${#REQUESTEDSEED}" != 10 ) ] ; then
            echo "Your seed number must be exactly 10-digits long"
            exit 1
        else SEED=".$REQUESTEDSEED"
        fi
    echo $SEED
}

set_flag() # parameters: a flag description and the letter for that flag on the python script
{
    DESCRIPTION=$1
    FLAGLETTER=$2
            read -r -p "(${FLAGLETTER}) ${DESCRIPTION} [default: y]? " GETFLAG
        case $GETFLAG in
            [Yy]* ) FLAGS+=${FLAGLETTER} ; echo "($FLAGLETTER) Chose yes" ;;
            [Nn]* ) echo "($FLAGLETTER) Chose no" ;;
            * ) FLAGS+=${FLAGLETTER} ; echo "($FLAGLETTER) Chose yes (Default)";;
        esac
    return
}

checksum_disk_image() # no parameters
{
    CHECKSUM=$(md5 "$INPUTPATH"/"$FILENAME" | cut -d " " -f 4)
    if [[ "$CHECKSUM" != "b156ba386436d20fd5ed8d37bab6b624" && "$CHECKSUM" != "aefdf27f1cd541ad46b5df794f635f50" && "$CHECKSUM" != "3bd1deebc5c5f08d036dc8651021affb" ]]; then
        echo "Error: Disk image failed md5 checksum.  This disk image is not Final Fantasy Tactics (PSX)."
        exit 1
    else
        echo $CHECKSUM
    fi
}

verify_in_range() # parameters: number to compare, bottom of range, top of range
{
    CHECK=$1
    BOTTOM=$2
    TOP=$3

    if [[ $(bc <<< "$BOTTOM <= $CHECK && $CHECK <= $TOP") == 1 ]] ; then
        echo $CHECK
    else
        echo "Error: ${CHECK} is out of the acceptable range of ${BOTTOM} to ${TOP}"
        exit 1
    fi
}


if [ $# -gt 2 ] ; then
    INPUTPATH=$2
    OUTPUTPATH=$3
    else
    INPUTPATH=$(get_directory input)
    OUTPUTPATH=$(get_directory output)
fi
    if [ $# -gt 0 ] ; then
        FILENAME=$1
    else
        FILENAME=$(get_disk_image)
    fi
checksum_disk_image
if [ $# -gt 4 ] ; then
    SEED=".$5"
    else
    SEED=$(get_seed)
fi
if [ $# -gt 3 ] ; then
    FLAGS=$4
    echo "Randomizer flags chosen at command line: $FLAGS"
    else
    echo "Job things:"
    set_flag "Randomize job stats and JP costs for skills" "j"
    set_flag "Randomize innate properties of jobs" "i"
    set_flag "Randomize job skillsets" "s"
    set_flag "Randomize job level requirements and job level JP" "r"
    echo "Item things:"
    set_flag "Randomize trophies, poaches, and move-find items" "t"
    set_flag "Randomize item prices and shop availability" "p"
    set_flag "Randomize weapon and item stats" "w"
    echo "Unit things:"
    set_flag "Randomize Enemy and Ally units" "u"
    set_flag "Randomize monster stats and skills" "m"
    echo "Map things:"
    set_flag "Randomize battle music" "c"
    set_flag "Randomize enemy and ally formations" "f"
    echo "Ability things:"
    set_flag "Randomize abilities" "a"
    set_flag "Randomize ability and weapon status effects" "y"
    echo "Quality of Life things:"
    set_flag "Enable special surprises" "z"
    set_flag "Enable autoplay cutscenes" "o"
fi
give_spoiler
if [ $# -gt 5 ] ; then
    CHAOS=$6
    else 
    CHAOS=$(get_chaos_level)
fi
echo
echo "building docker image 'fft_rcc' for local use"
echo
docker build --tag fft_rcc . | grep :
echo
IMAGEID=$(docker images fft_rcc --format='{{.ID}}' | head -1)
echo "Local docker image with id ${IMAGEID} has been tagged as 'fft_rcc:latest'"
echo
echo "chaos multiplier: ${CHAOS}"
echo "disk image: ${INPUTPATH}/${FILENAME}"
echo "disk image checksum: ${CHECKSUM}"
echo "exporting spoiler: ${EXPORTSPOILER}"
echo "seed value: ${SEED}"
echo "selected flags: ${FLAGS}"
echo "output directory: ${OUTPUTPATH}"
echo

docker run --rm -e SEED=${SEED} -e FLAGS=${FLAGS} -e CHAOS=${CHAOS} -e FILENAME=${FILENAME} -e EXPORTSPOILER=${EXPORTSPOILER} -v ${INPUTPATH}:/input -v ${OUTPUTPATH}:/output fft_rcc
