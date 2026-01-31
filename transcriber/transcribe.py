import whisper

model = whisper.load_model("base")
print("Model loaded.")


def transcribe_audio(file_path: str) -> str:
    print("Transcribing...")
    result = model.transcribe(file_path)
    return result["text"].strip()
