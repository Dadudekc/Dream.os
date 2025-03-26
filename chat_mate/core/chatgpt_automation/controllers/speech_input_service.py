import logging

def listen_and_transcribe():
    """
    Captures audio from the microphone and returns the transcribed text.
    
    Priority:
      1. Whisper-based transcription (preferred for accuracy)
      2. Fallback to SpeechRecognition with Google API
    """
    logger = logging.getLogger(__name__)
    
    # Try Whisper-based transcription
    try:
        logger.info("Attempting Whisper-based transcription...")
        import whisper
        import sounddevice as sd
        import numpy as np

        # Parameters for audio recording
        fs = 16000  # sampling rate (Hz)
        duration = 5  # record for 5 seconds

        logger.info("Recording audio for Whisper transcription...")
        audio_data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait()  # Wait until recording is finished
        audio_data = np.squeeze(audio_data)

        # Load the Whisper model (using "base" model; adjust as needed)
        model = whisper.load_model("base")
        result = model.transcribe(audio_data)
        transcript = result.get("text", "").strip()
        if transcript:
            logger.info("Whisper transcription successful.")
            return transcript
        else:
            logger.warning("Whisper returned an empty transcript.")

    except Exception as e:
        logger.error(f"Whisper-based transcription failed: {e}")

    # Fallback: SpeechRecognition using Google API
    try:
        logger.info("Attempting SpeechRecognition fallback...")
        import speech_recognition as sr

        r = sr.Recognizer()
        with sr.Microphone() as source:
            logger.info("Listening via microphone (fallback)...")
            # Adjust timeout and phrase_time_limit as needed
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            transcript = r.recognize_google(audio)
            transcript = transcript.strip()
            if transcript:
                logger.info("SpeechRecognition transcription successful.")
                return transcript
            else:
                logger.warning("SpeechRecognition returned an empty transcript.")

    except Exception as ex:
        logger.error(f"SpeechRecognition fallback failed: {ex}")

    # If both methods fail, return None
    return None
