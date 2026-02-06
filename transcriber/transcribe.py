import whisper
from tenacity import retry, stop_after_attempt, wait_exponential


class Transcriber:
    def __init__(self) -> None:
        print("Loading Whisper model...")
        self.model = whisper.load_model("base")
        print("Model loaded.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def transcribe_audio(self, file_path: str) -> str:
        print("Transcribing...")
        result = self.model.transcribe(file_path)
        return result["text"].strip()
