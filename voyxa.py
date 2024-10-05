import os
from flask import Flask, request, send_file
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from openai import OpenAI
import logging
import requests
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
# load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load API keys and tokens
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
# TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
# ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')
DEEPGRAM_API_KEY="282f561f600e5644aeeecef522be4495ebec885d"
ELEVEN_LABS_API_KEY="sk_aec128359cc98eca34d346d76bf33f1fe0277aaefdf022e8"
TWILIO_ACCOUNT_SID="ACbf5dec6dbcc11c81771660a8c91b317a"
TWILIO_AUTH_TOKEN="79f3419acbf0ee454cb0b6b439492817"
TWILIO_PHONE_NUMBER="+1 219 359 4055"

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Eleven Labs configuration
ELEVEN_LABS_VOICE_ID = "3DPhHWXDY263XJ1d2EPN"  # Replace with an Italian voice ID
ELEVEN_LABS_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_LABS_VOICE_ID}"

# Store conversation history
conversation_memory = []

# AI assistant prompt (in Italian)
prompt = """##Obiettivo
Sei un assistente vocale AI chiamato Voyxa, progettato per aiutare gli utenti con problemi tecnici in un contesto di helpdesk. La tua lingua principale è l'italiano. Il tuo stile di comunicazione deve essere professionale, chiaro, coinvolgente e mantenere una voce e un comportamento simili a quelli umani.

## Ruolo

Personalità: Il tuo nome è Voyxa e sei un assistente vocale AI per il supporto helpdesk. Mantieni un atteggiamento piacevole e amichevole durante tutte le interazioni. Questo approccio aiuta a costruire un rapporto positivo con i clienti e i colleghi, garantendo una comunicazione efficace e piacevole.

Compito: Il tuo compito principale è diagnosticare e risolvere problemi tecnici segnalati dagli utenti. Questo può comportare fare domande di chiarimento, fornire soluzioni passo-passo in italiano o, se necessario, elevare il problema a un tecnico umano.

Stile conversazionale: Il tuo stile di comunicazione deve essere proattivo e guidare la conversazione, facendo domande mirate per comprendere meglio le esigenze del cliente. Assicurati che le tue risposte siano concise, chiare e mantengano un tono conversazionale. Se non c'è una risposta iniziale, continua a coinvolgere con domande pertinenti per ottenere chiarezza sulle loro esigenze. Mantieni la tua prosa succinta e al punto.

## Linee guida per la risposta

- [Supera gli errori ASR] Questa è una trascrizione in tempo reale, aspettati che ci siano errori. Se puoi indovinare cosa sta cercando di dire l'utente, allora indovina e rispondi. Quando devi chiedere chiarimenti, usa frasi colloquiali appropriate per la lingua italiana (ad esempio, "non ho capito").
- [Attieniti sempre al tuo ruolo] Pensa a cosa può e non può fare il tuo ruolo. Se il tuo ruolo non può fare qualcosa, cerca di riportare la conversazione all'obiettivo della conversazione e al tuo ruolo. Non ripeterti nel farlo. Dovresti comunque essere creativo, simile a un umano e vivace.
- [Crea una conversazione fluida] La tua risposta dovrebbe adattarsi sia al tuo ruolo che alla sessione di chiamata in diretta per creare una conversazione simile a quella umana. Rispondi direttamente a ciò che l'utente ha appena detto.

## Guardrail stilistici

- [Sii conciso] Mantieni la tua risposta succinta, breve e vai al punto rapidamente. Affronta una domanda o un elemento d'azione alla volta. Non comprimere tutto ciò che vuoi dire in un'unica espressione.
- [Non ripetere] Non ripetere ciò che c'è nella trascrizione. Riformula se devi reiterare un punto. Usa strutture di frasi e vocabolario variati per garantire che ogni risposta sia unica e personalizzata.
- [Sii conversazionale] Parla come un umano come se stessi parlando con un amico stretto -- usa un linguaggio quotidiano e mantienilo simile a quello umano. Occasionalmente aggiungi parole di riempimento, mantenendo la prosa breve. Evita di usare paroloni o di suonare troppo formale.
- [Rispondi con emozioni]: Hai emozioni, atteggiamenti e disposizioni simili a quelle umane. Quando appropriato: usa tono e stile per creare risposte più coinvolgenti e personalizzate; incorpora umorismo o arguzia; diventa emotivo o empatico; applica elementi di sorpresa o suspense per mantenere l'utente coinvolto. Non essere arrendevole.
- [Usa un linguaggio appropriato]: Rispondi sempre in italiano, a meno che l'utente non chieda esplicitamente di passare all'inglese.

Inoltre, se l'utente dice "arrivederci" o "addio", termina educatamente la conversazione.

IMPORTANTE: Rispondi SEMPRE in italiano, indipendentemente dalla lingua dell'input dell'utente, a meno che l'utente non richieda esplicitamente l'inglese.
"""

def generate_ai_response(user_input):
    """Generate AI response using OpenAI"""
    try:
        conversation_memory.append({"role": "user", "content": user_input.strip()})
        messages = [
            {"role": "system", "content": prompt},
            {"role": "system", "content": "Rispondi sempre in italiano."},
        ]
        messages.extend(conversation_memory)
        chat_completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        ai_response = chat_completion.choices[0].message.content.strip()
        conversation_memory.append({"role": "assistant", "content": ai_response})
        return ai_response
    except Exception as e:
        logger.error(f"Errore nella generazione della risposta AI: {e}")
        return "Mi dispiace, ma sto avendo problemi a generare una risposta al momento. Potresti riprovare?"

def generate_audio(text):
    """Generate audio using Eleven Labs TTS"""
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVEN_LABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    response = requests.post(ELEVEN_LABS_TTS_URL, json=data, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        logger.error(f"Error in Eleven Labs TTS: {response.text}")
        return None

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Handle incoming voice calls"""
    response = VoiceResponse()
    gather = Gather(input='speech', action='/process_speech', language='it-IT', speechTimeout='auto')
    
    # Generate and store the welcome message audio
    welcome_message = "Ciao, sono Voyxa, il tuo assistente AI per l'helpdesk. Come posso aiutarti oggi?"
    audio_content = generate_audio(welcome_message)
    if audio_content:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            temp_audio.write(audio_content)
            temp_audio_path = temp_audio.name
        
        audio_url = request.url_root + f'audio/{os.path.basename(temp_audio_path)}'
        gather.play(audio_url)
    else:
        # Fallback to Twilio TTS if Eleven Labs fails
        gather.say(welcome_message, voice='Carla', language='it-IT')
    
    response.append(gather)
    return str(response)

@app.route("/process_speech", methods=['POST'])
def process_speech():
    """Process speech input and generate response"""
    user_speech = request.form.get('SpeechResult', '').lower()
    
    if not user_speech:
        response = VoiceResponse()
        response.say("Mi dispiace, non ho capito. Puoi ripetere per favore?", voice='Carla', language='it-IT')
        return gather_speech(response)
    
    logger.info(f"Discorso utente: {user_speech}")
    
    if "arrivederci" in user_speech or "addio" in user_speech:
        return end_conversation()
    
    # Generate AI response
    ai_response = generate_ai_response(user_speech)
    logger.info(f"Risposta AI: {ai_response}")
    
    response = VoiceResponse()
    
    # Generate and store the AI response audio
    audio_content = generate_audio(ai_response)
    if audio_content:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            temp_audio.write(audio_content)
            temp_audio_path = temp_audio.name
        
        audio_url = request.url_root + f'audio/{os.path.basename(temp_audio_path)}'
        response.play(audio_url)
    else:
        # Fallback to Twilio TTS if Eleven Labs fails
        response.say(ai_response, voice='Carla', language='it-IT')
    
    return gather_speech(response)

def gather_speech(response):
    """Add a Gather verb to the response to continue the conversation"""
    gather = Gather(input='speech', action='/process_speech', language='it-IT', speechTimeout='auto')
    response.append(gather)
    return str(response)

def end_conversation():
    """End the conversation when the user says goodbye"""
    response = VoiceResponse()
    farewell_message = "Grazie per aver utilizzato il nostro helpdesk AI. Buona giornata!"
    
    audio_content = generate_audio(farewell_message)
    if audio_content:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            temp_audio.write(audio_content)
            temp_audio_path = temp_audio.name
        
        audio_url = request.url_root + f'audio/{os.path.basename(temp_audio_path)}'
        response.play(audio_url)
    else:
        # Fallback to Twilio TTS if Eleven Labs fails
        response.say(farewell_message, voice='Carla', language='it-IT')
    
    response.hangup()
    return str(response)

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve the temporary audio file"""
    return send_file(os.path.join(tempfile.gettempdir(), filename), mimetype='audio/mpeg')

if __name__ == "__main__":
    app.run(debug=True)
