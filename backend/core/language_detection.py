from langdetect import detect, LangDetectException

def ensure_french(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return True
    
    try:
        detected_lang = detect(text)
        return detected_lang == 'fr'
    except LangDetectException:
        return True