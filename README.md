# TheLangGame
A tool for adding TTS and translations to video text heavy video games

I'm keeping this repo up to date as a backup of my code but don't expect it to work well out of the box. It depends on a hunspell dictionary, a stardict dictionary, and a bunch of files that list common French words. I'm not providing them because I don't own the files I'm using, but these are all standard files that can be found online.

This code was first written for the game Hatoful Boyfriend but over time will be adapted for other games as I play them.

apt-get install libhunspell-dev hunspell-fr  libffi-dev libffi6 tesseract imagemagick tesseract-ocr-fra sdcv

pip install hunspell mss hunspell playsound pydub google-cloud-texttospeech google-cloud-translate 