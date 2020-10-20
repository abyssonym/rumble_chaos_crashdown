#!/bin/sh

# randomize
python /rumble_chaos_crashdown/randomizer.py /input/$filename

# rename .iso to .bin for OpenEmu
 for file in *.iso
  do
   mv "$file" "/output/${file%.iso}.bin"
  done

# correct cue file for OpenEmu
 # add quotes at beginning of filename
  sed -i '1 s/fft/"fft/' ${file%.iso}.cue
 # change file extension and close quotes
  sed -i '1 s/iso/bin"/' ${file%.iso}.cue
mv ${file%.iso}.cue /output
