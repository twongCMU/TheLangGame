from google.cloud import texttospeech
""" The game Coffee Talk is excellent and is localized to many languages. It doesn't have voice
overs but it has mod support for creating one's own VO. One steam workshop mod says it took the
author 60 hours just to record the voice for the Bartender. The voice work is excellent but it
also suggests that there won't be one for French any time soon. This script generates all of the
voices for the game for a language learner. The speech is generated at 85-90% speed and the
Bartender is not voiced so the player can say those lines themselves

Google Text to Speech happens to have 9 voices for French (between Canadian and France French)
so with slight tweaks to the pitch and speed we can have decent variety.
"""

tts_client = texttospeech.TextToSpeechClient()

"""
F: CA A(aqua-high, silver-low),C(myrtle) FR A(lua),C(rachel),E(freya)
M: CA B(baileys),D(gala-low,agent-high) FR B(neil-low, hendry-high),D(hyde-high, jorji-low)
"""
voices = {
    "Freya":"fr-FR-Wavenet-E,3,.85",
    "Baileys":"fr-CA-Wavenet-B,0,.85",
    "Rachel":"fr-FR-Wavenet-C,3,.90",
    "Gala":"fr-CA-Wavenet-D,-3,.85",
    "Aqua":"fr-CA-Wavenet-A,3,.85",
    
    "Neil":"fr-FR-Wavenet-B,-3,.85",
    "Hyde":"fr-FR-Wavenet-D,3,.85",
    
    "Lua":"fr-FR-Wavenet-A,0,.85",
    "Jorji":"fr-FR-Wavenet-D,-3,.90",
    "Myrtle":"fr-CA-Wavenet-C,0,.85",
    "Hendry":"fr-FR-Wavenet-B,3,.85",
    
    "Agent":"fr-CA-Wavenet-D,3,.85",
    "NekoHendry":"fr-FR-Wavenet-B,5,.85",
    "Silver":"fr-CA-Wavenet-A,-3,.85",
    "Weregala":"fr-CA-Wavenet-D,-5,.85",
    }

def get_tts(voices, speech_text, filename):
    (_,day,dialog_id,who) = filename.split('.')
    out_file = "/home/tw/French_TTS_VO/VO/" + day + "/"+ dialog_id + ".wav"

    if who == "Barista":
        return

    #if day == "Day1":
    #    return
    
    speaker_voice = voices[who]
    (tts_name, tts_pitch, tts_speaking_rate) = speaker_voice.split(',')

    print(out_file + " : " + who + " : " + speaker_voice)
    
    tts_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=float(tts_speaking_rate),
        pitch=int(tts_pitch)
    )
    tts_input = texttospeech.SynthesisInput(text=speech_text)
    tts_voice = texttospeech.VoiceSelectionParams(
        language_code=tts_name[0:6], name=tts_name
    )
    
    tts_response = tts_client.synthesize_speech(
        input=tts_input, voice=tts_voice, audio_config=tts_config
    )
    
    with open(out_file, "wb") as out:
        out.write(tts_response.audio_content)
    
wordslist = []
nameslist = []

# names are SAY.DAY#.#.Who
# DAY might be AfterCredits but it's the dir name in any case
with open("/home/tw/coffee_talk_names") as f:
    line = f.readlines()
    for l in line:
        v = l.strip()
        if len(v) < 1:
            continue
        nameslist.append(v)

with open("/home/tw/coffee_talk_french_processed") as f:
    line = f.readlines()
    for l in line:
        v = l.strip()
        if len(v) < 1:
            continue
        wordslist.append(v)


for i in range(len(wordslist)):
    get_tts(voices, wordslist[i], nameslist[i])

        
