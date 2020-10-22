FFT Rumble Chaos Crashdown Randomizer
Version:    27
Date:       May 23, 2020
URL:        https://github.com/abyssonym/rumble_chaos_crashdown
Contact:    https://twitter.com/abyssonym

--- HOW TO USE ---
Running the randomizer:
    Windows users may use the executable file, `fft_rcc.exe`. Other users, please run `randomizer.py` using Python version 2.7.
    Python command line arguments:
        `python randomizer.py <ISO_FILENAME> <FLAGS>.<SEED> <CHAOS MULTIPLIER>`
    Windows, macOS, and *nix users (who may already be using Python 3 or higher) may also install `docker` and run `sh docker-randomize-seed.sh`, which will output an OpenEmu-ready .bin and .cue file
    Docker script command line arguments:
        `sh docker-randomize-seed.sh <ISO_FILENAME> <ISO_DIRECTORY> <OUTPUT_DIRECTORY> <FLAGS> <SEED> <CHAOS MULTIPLIER>`
    
Source ISO file:
    The randomizer will ask for a filename. Place your Final Fantasy Tactics ISO in the same directory as "fft_rcc.exe" and input the name of the file. You must include the file extension (ex: fft.img). Please note that the randomizer needs 1 GB of free space to create the randomized ISO. The ISOs used for testing have the following hashes:
    MD5 - b156ba386436d20fd5ed8d37bab6b624
          aefdf27f1cd541ad46b5df794f635f50
          3bd1deebc5c5f08d036dc8651021affb (J)
    CRC32 - 377f6510
            8ab1b7b1
            a6361fd1 (J)
    If your file is about 517 MB then it's probably correct. The Japanese version is the Square Millennium Collection edition (1.1). This is the version more commonly used by Japanese hackers. The original Japanese version will not work.
    The Docker image will check this for you automatically.

Flags:
    Input the following flags to customize your RUMBLE CHAOS CRASHDOWN experience.

    u  Randomize enemy and ally units.
    j  Randomize job stats and JP required for skills.
    i  Randomize innate properties of jobs.
    s  Randomize job skillsets.
    a  Randomize abilities, including CT, MP cost, etc.
    y  Randomize ability and weapon status effects.
    r  Randomize job requirements and job level JP.
    t  Randomize trophies, poaches, and move-find items.
    p  Randomize item prices and shop availability.
    w  Randomize weapon and item stats.
    m  Randomize monster stats and skills.
    c  Randomize battle music.
    f  Randomize enemy and ally formations.
    z  Enable special surprises.
    o  Enable autoplay cutscenes.

Seed value:
    Input a seed value here, or leave it blank if you don't care.

Chaos multiplier:
    This is a difficulty setting for RCC. It mainly affects enemy stats and the level of treasure you acquire. The standard difficulty is 1.0, with 0.5 being quite easy and 1.5 being quite hard. Difficulty scales quadratically with the chaos multiplier, so don't raise it too high!

Output files:
    The randomizer will output a new, randomized ISO with the seed in the filename. If you choose to randomize job requirements, it will also output a text file with the new job requirements inside.

--- SPECIAL THANKS & CONTRIBUTORS ---
Ryason55 - https://www.youtube.com/user/Ryason55
    Contributed the code to randomize item/equipment stats and weapon/ability status effects, plus bugfixes.
VirtualEstatePlanner - https://github.com/VirtualEstatePlanner
    Put it in a Docker container and made it easy for OpenEmu users to enjoy
    
Like this randomizer? Be sure to check out my other projects at www.abyssonym.com, on my github, and on twitter.
