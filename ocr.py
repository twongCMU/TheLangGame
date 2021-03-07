from google.cloud import texttospeech
from google.cloud import translate_v2 as translate
import hunspell
import json
import mss
import mss.tools
from pydub import AudioSegment
from pydub.playback import play
import random
import re
import six
import subprocess
import time

"""
This is a hacked together script to extract text from a text-dialog video game,
send it to Google TTS to read the lines out loud, then look up translations for
words that are deemed to be uncommon
"""

# Export this on in the terminal to import google credentials
#export GOOGLE_APPLICATION_CREDENTIALS=/home/tw/google_tts_creds.json 

my_name = "Roose"

cursor_ocr_characters = ["v","»","+","&","7","x","=","-"]

voice_names = ["fr-CA-Wavenet-A",
               "fr-CA-Wavenet-B",
               "fr-CA-Wavenet-C",
               "fr-CA-Wavenet-D",
               "fr-FR-Wavenet-A",
               "fr-FR-Wavenet-B",
               "fr-FR-Wavenet-C",
               "fr-FR-Wavenet-D",
               "fr-FR-Wavenet-E"]

narrator_voice = random.choice(voice_names)

voice_names_orig = []
for v in voice_names:
    #(mixing pitch and speaking_rate)
    # My French isn't great so all of them have a slow speaking rate
    for option in [",5,.9",",-5,.85",",0,.8"]: 
        voice_names_orig.append(v+option)

voice_names = voice_names_orig.copy()

# make sure the narrator has a more reasonable voice
narrator_voice += ",0,.8"
voices_used = {}
voices_used["Narrator"] = narrator_voice
voice_names.remove(narrator_voice)

# Instantiates a client
tts_client = texttospeech.TextToSpeechClient()
translate_client = translate.Client()

# Games
# Oxenfree (have key in Humble Bundle)
# Chicken Police
# Haven
# Hatoful Boyfriend

# FTL
# Coffee Talk

# ignore words less common than this
WORD_FREQ_THRESHOLD = 500 

# if the % of identical words seen in the screenshot compared to the previous screenshot is higher than this we don't recompute
# I think we have to set this pretty high because OCR is reliable but words print slowly to the screen
# so we could screenshot mid-sentence
WORD_SAME_THRESHOLD = .90

MIN_WORD_LENGTH = 4

MAX_DEFINITION_LENGTH = 30

# if the word is not found, display max this many similar definitions
MAX_WORD_MATCHES = 1

MAX_DEFINITIONS = 5

hunspell_obj = hunspell.HunSpell('/home/tw/index.dic', '/home/tw/index.aff')

def process_word(word):
    """ Standardize a word. Reformat it then get the stem

    Returns a list of words, possibly zero, one, or more values. This is because
    a word may have multiple stems and we don't know which one it is so we get 
    all of them. For example, suis -> etre or suivre
    """
    ret_list = []
    
    word = word.strip()
    if len(word) < MIN_WORD_LENGTH:
        return ret_list

    # filter out contractions (e.g., l'objet, d'avoir, j'etais, c'est, s'abrir)
    if word[1] == "'":
        word = word[2:]
        
    word = word.lower()

    root_word = hunspell_obj.stem(word)
    for r in root_word:
        ret_list.append(r.decode('utf-8'))

    return ret_list
                
def build_word_filter(filename, top_words):
    """ Build a dict of word stems to integers

    The integer generally represents the difficulty of the word but it's hard to get, for example, a CEFR
    aligned list of words so instead this mashes together some beginner vocab lists I found from a New
    Zealand website and a list of the top 10000 most common words. 

    For the latter I estimate that the more common a word is, the more well known it is to beginners. For
    the former I just stuff all of the beginner words in withan integer value of 1

    Modifies the dict in place
    """
    # common words list
    with open(filename) as f:
        line = f.readlines()

        row = 1
        for l in line:
            word_list = process_word(l)

            # if the processed word did not return a stem. Maybe it was too short or wasn't a real word
            if len(word_list) == 0:
                continue

            # the stemmer may return multiple stems. Usually they're related words so it's ok
            # for example appelees -> appele or appeler
            # on a rare occasion the stemmer might return wildly different difficulty words like
            # oignons -> oignon, oindre but I think it's rare and also it might get tagged with a high integer anyway
            for one_word in word_list:
                # if we've already processed this word skip it since we want the lowest score
                if one_word in top_words:
                    continue

                top_words[one_word] = row
                row += 1

    top_words["retard"]=1
    top_words["pigeon"]=1

def pick_voice(username_text, voices_used, voice_names):
    # pick a voice

    unknown_user = None
    unknown_voice = None

    # In Hatoful Boyfriend the first time a character appears they are named ???
    # until they introduce themselves. The OCR sometimes reads this as 27?
    
    # if ??? user exists in the dict then the current user's voice is actually that
    # one now that they have identified themselves
    for k,v in voices_used.items():
        if k.startswith("??") or k.startswith("27?"):
            unknown_user = k
            unknown_voice = v
            break
        
    # update the username_text user to have the voice from the ??? user
    if unknown_user is not None:
        voices_used[username_text] = unknown_voice
        if username_text != unknown_user:
            del voices_used[unknown_user]
        return

    # otherwise, pick a new voice
    if username_text not in voices_used:
        # pick a voice, or, if one is saved, use that instead
        tts_name = random.choice(voice_names)
        voice_names.remove(tts_name)
        voices_used[username_text] = tts_name

        if len(voice_names) == 0:
            voice_names = voice_names_orig.copy()

def get_tts(username_text, voices_used, original_text):
    # pitch and speaking_rate are strings so be sure to convert them before using
    (tts_name, tts_pitch, tts_speaking_rate) = voices_used[username_text].split(',')
    tts_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=float(tts_speaking_rate),
        pitch=int(tts_pitch)
    )
    tts_input = texttospeech.SynthesisInput(text=original_text)
    tts_voice = texttospeech.VoiceSelectionParams(
        language_code=tts_name[0:6], name=tts_name
    )

    print("Voice " + tts_name + ", pitch " + tts_pitch + ", rate " + tts_speaking_rate)
    #print(original_text)
    tts_response = tts_client.synthesize_speech(
        input=tts_input, voice=tts_voice, audio_config=tts_config
    )
    
    with open("output.mp3", "wb") as out:
        out.write(tts_response.audio_content)


top_words = {}

# beginner files
filter_files = ["french2.txt", "french3.txt"]
for filter_file in filter_files:
    build_word_filter(filter_file, top_words)

# these are beginner words so override the integer to something low so we filter it out
for k in top_words.keys():
    top_words[k] = 1

build_word_filter("french.txt", top_words)

    
#print("top words size " + str(len(top_words.keys())))

# In the French->English dictionary we use, most definitions are enclosed in <B> </B> tags
# so we search for that
en_regex = re.compile(r"<B> ([^<]+)<")
regex_punctuation = re.compile("[\.\!\?,\"\+]")
regex_quotes = re.compile("[\"]")
en_regex_brackets = re.compile(r"\[[^\]]*\]")
en_regex_close_bracket = re.compile(r"^[^\]]*\]") #from start of string

filename = "ocr.png"
filename_edit = "ocr_edit.png"
filename_username_edit = "ocr_username_edit.png"

old_sentence_words = set()
sct = mss.mss()

while 1:
    input("Press key when ready")

    # Take a screenshot of just a part of the screen where the game window is
    #monitor = {"top": 0, "left": 1920, "width": 1920, "height": 1080} # top right corner 1080p
    #monitor = {"top": 0, "left": 2474, "width": 1366, "height": 768} # top right corner 768p
    monitor = {"top": 0, "left": 553, "width": 1366, "height": 768} # top right corner 768p
    sct_img = sct.grab(monitor)
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)

    # cut out the username area
    subprocess.Popen(["convert","-crop","300x50+60+450","-threshold","80%",filename,filename_username_edit]) #Hatoful username 768p
    # check if the username area is a high % white pixels so we don't accidentally OCR some background image
    time.sleep(0.1) # sometimes the next step picks up a stale image I think
    p = subprocess.Popen(["convert", filename_username_edit, "-threshold", "99%", "-format", "%[fx:100*image.mean]", "info:"], stdout=subprocess.PIPE)
    username_pct = p.communicate()[0]
    username_pct = username_pct.decode('utf-8')

    print("pct is " + username_pct)
    if float(username_pct) > 70 and float(username_pct) < 97:
        p = subprocess.Popen(["tesseract",filename_username_edit,"stdout","-l","fra"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        username_text = p.communicate()[0]
        username_text = username_text.decode('utf-8')
        username_text = username_text.strip()
        print("username is " + username_text)
        if float(username_pct) > 95 and not (username_text.startswith("??") or username_text.startswith("27?")):
            username_text = "Narrator"
    else:
        username_text = "Narrator"

    #subprocess.Popen(["convert","-crop","1920x325+0+675","-threshold","60%", "-negate",filename,filename_edit]) #hatoful 1080p
    subprocess.Popen(["convert","-crop","1280x220+40+510","-threshold","60%", "-negate",filename,filename_edit]) #Hatoful 768p
    #subprocess.Popen(["convert","-crop","1090x600+280+250","-threshold","60%", "-negate",filename,filename_edit]) #ftl 1080p
    p = subprocess.Popen(["tesseract",filename_edit,"stdout","-l","fra"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    text = p.communicate()[0]
    text = text.decode('utf-8')
    text = text.strip()
    text = re.sub(regex_quotes, "", text)
    
    # if the last character is a v or » or + it probably OCR'd the cursor
    print("last char is " + text[-1])

    if text[-1] in cursor_ocr_characters:
        text = text[:-1]
    print(text)
    original_text = text

    text = text.lower()
    #replace sentence punctuation with a space so we look up real words

    text = re.sub(regex_punctuation, " ", text)

    if len(text) < 5:
        continue
    
    words_to_translate = set()
    new_sentence_words = set()
    words_same_as_previous = 0

    for w in re.split('\s', text):
        word_list = process_word(w)

        # We operate on the original word not the processed one here because we just want to
        # detect changes. process_word might munge the word and confuse things
        if w in old_sentence_words:
            words_same_as_previous+=1

        if len(word_list) == 0:
            continue

        # Again, we operate on the original word for this detection
        new_sentence_words.add(w)
        for root_word in word_list:
            if len(root_word) < MIN_WORD_LENGTH:
                continue
            #print("operating on root " + root_word + " thresh " + str(top_words[root_word]))
            # discard anything that is lower than a certain score on the list of common words
            if root_word not in top_words or top_words[root_word] > WORD_FREQ_THRESHOLD:
                #save the root of the word
                words_to_translate.add(root_word)

    word_count = max(len(new_sentence_words), len(old_sentence_words))
    #if (word_count > 0 and (float(words_same_as_previous))/(float(word_count)) > WORD_SAME_THRESHOLD) or len(words_to_translate) == 0:
    #    continue
    print(chr(27) + "[2J")

    if my_name != username_text:
        pick_voice(username_text, voices_used, voice_names)

        # quick hack: if the words didn't change much, don't redo the tts just play the existing file
        if not (word_count > 0 and (float(words_same_as_previous))/(float(word_count)) > WORD_SAME_THRESHOLD):
            get_tts(username_text, voices_used, original_text)
        else:
            print("Repeating audio")


    print("Username pct " + username_pct)
    if my_name != username_text:
        song = AudioSegment.from_mp3('output.mp3')
        play(song)
    
    print(chr(27) + "[2J")
    print(username_text + ": " + text)
    old_sentence_words = new_sentence_words
    sdcv_words_seen = set()
    words_to_translate_seen = set()
    for w in sorted(words_to_translate):
        if w in words_to_translate_seen:
            continue
        en_command = ['sdcv', '--data-dir', '/home/tw/stardict/', '--use-dict', "Larousse Chambers français-anglais",  "-e", "-j", "-n",  w]
        p = subprocess.Popen(en_command, stdout=subprocess.PIPE)
        en_definition = p.communicate()[0]
        en_definition = en_definition.decode('utf-8')
        # json gives us a list of [dict, word, definition]
        en_definitions = json.loads(en_definition)

        if len(en_definitions) > MAX_WORD_MATCHES:
            en_definitions = en_definitions[:MAX_WORD_MATCHES+1]

        printed = 0
        # There can be more than one match if there was not an exact match in the dictionary
        for i in range(min(len(en_definitions), MAX_WORD_MATCHES)):
            en_definition = en_definitions[i]["definition"]
            en_word = en_definitions[i]["word"]

            # don't print out duplicates of the word sdcv looked up
            if en_word in sdcv_words_seen:
                continue
            sdcv_words_seen.add(en_word)
            
            en_reg = re.findall(en_regex, en_definition)

            # prevent duplicate printouts within one lookup
            # sometimes a word has multiple translations but they're all the same
            en_seen = set() 

            definitions_displayed = 0
            for index in range(min(len(en_reg), 5)):
                definition = en_reg[index].strip()
                if len(definition) > MAX_DEFINITION_LENGTH + 5:
                    definition = definition[:MAX_DEFINITION_LENGTH] + "[...]"
                if definition not in en_seen:
                    if definitions_displayed == 0:
                        print("["+en_word+"]")
                    definitions_displayed+=1
                    printed+=1
                    print(" * " + definition)
                    en_seen.add(definition)
                    if definitions_displayed >= MAX_DEFINITIONS:
                        break

        # if no definition printed because it wasn't in the local dictionary, ask Google translate
        if printed == 0:
            if w in sdcv_words_seen:
                continue
            sdcv_words_seen.add(w)
            print("{"+w+"}")
            result = translate_client.translate(w, target_language="en")
            print(u" * {}".format(result["translatedText"]))

        words_to_translate_seen.add(w)


