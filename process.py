import os
import shutil
from pathlib import Path
import json
import re
import ffmpeg
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

# ---------------- Config ----------------
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
WHISPER_MODEL_SIZE = "medium"  # tiny, base, small, medium, large-v2, large-v3
HUGGINGFACE_TOKEN = os.getenv("HF_TOKEN", "")  # Legge da variabile d'ambiente
DEVICE = "cpu"  # "cuda" se hai GPU NVIDIA
COMPUTE_TYPE = "int8"  # "float16" per GPU, "int8" per CPU

# ---------------- Setup cartelle ----------------
INPUT_DIR.mkdir(parents=True, exist_ok=True)
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- Funzioni ----------------
def extract_audio(file_path: Path, out_path: Path):
    """Estrai l'audio WAV dal MKV usando ffmpeg"""
    print(f"[INFO] Estraggo audio da {file_path.name} → {out_path.name}")
    try:
        (
            ffmpeg
            .input(str(file_path))
            .output(str(out_path), format='wav', acodec='pcm_s16le', ac=1, ar='16000')
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(f"[ERRORE] FFmpeg: {e.stderr.decode()}")
        raise

def transcribe(audio_path: Path):
    """Trascrizione con Faster Whisper"""
    print(f"[INFO] Trascrivo {audio_path.name}")
    model = WhisperModel(WHISPER_MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    segments, info = model.transcribe(
        str(audio_path),
        language="it",  # forza italiano, usa None per auto-detect
        beam_size=5,
        vad_filter=True,  # filtra il silenzio
        word_timestamps=False
    )
    
    result = []
    for segment in segments:
        result.append({
            "text": segment.text.strip(),
            "start": segment.start,
            "end": segment.end
        })
    
    print(f"[INFO] Lingua rilevata: {info.language} (confidenza: {info.language_probability:.2f})")
    print(f"[INFO] Trascritti {len(result)} segmenti")
    return result

def diarize(audio_path: Path):
    """Speaker diarization con pyannote.audio"""
    print(f"[INFO] Diarization in corso per {audio_path.name}")
    
    # Verifica che il token sia stato inserito
    if HUGGINGFACE_TOKEN == "INSERISCI_IL_TUO_TOKEN" or not HUGGINGFACE_TOKEN:
        raise ValueError(
            "ERRORE: Devi inserire il tuo HuggingFace token!\n"
            "1. Vai su https://huggingface.co/settings/tokens\n"
            "2. Crea un token\n"
            "3. Sostituisci HUGGINGFACE_TOKEN nel codice"
        )
    
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HUGGINGFACE_TOKEN
        )
    except Exception as e:
        print(f"[ERRORE] Impossibile caricare il modello: {e}")
        print("Assicurati di aver accettato i termini su:")
        print("- https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("- https://huggingface.co/pyannote/segmentation-3.0")
        raise
    
    diarization = pipeline(str(audio_path))
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": turn.start,
            "end": turn.end
        })
    print(f"[INFO] Identificati {len(set(s['speaker'] for s in segments))} speaker")
    return segments

def align_speakers(transcript, diarization):
    """Allinea segmenti trascritti con speaker"""
    print(f"[INFO] Allineamento speaker in corso...")
    aligned = []
    for t in transcript:
        midpoint = (t["start"] + t["end"]) / 2
        speaker_label = "Unknown"
        for d in diarization:
            if d["start"] <= midpoint <= d["end"]:
                speaker_label = d["speaker"]
                break
        aligned.append({
            "speaker": speaker_label,
            "text": t["text"],
            "start": t["start"],
            "end": t["end"]
        })
    return aligned

def clean_text(text: str) -> str:
    """
    Pulisce un testo trascritto:
    - rimuove filler comuni
    - rimuove ripetizioni semplici
    - sistema punteggiatura base
    """
    # Rimuovi filler comuni in italiano
    fillers = ["ehm", "uh", "uhm", "cioè", "mmm", "eh", "ah", "mah"]
    pattern_fillers = r"\b(" + "|".join(fillers) + r")\b"
    text = re.sub(pattern_fillers, "", text, flags=re.IGNORECASE)

    # Rimuovi spazi multipli
    text = re.sub(r"\s+", " ", text).strip()
    
    # Se il testo è vuoto dopo la pulizia, ritorna stringa vuota
    if not text:
        return ""

    # Aggiungi punto alla fine se manca
    if text[-1] not in ".!?":
        text += "."

    # Capitalizza la prima lettera
    text = text[0].upper() + text[1:]

    return text

def save_final(aligned_segments, output_file: Path):
    """Salva il transcript finale raggruppando per speaker e pulendo il testo"""
    print(f"[INFO] Scrivo transcript finale → {output_file.name}")
    with open(output_file, "w", encoding="utf-8") as f:
        current_speaker = None
        buffer = []
        for seg in aligned_segments:
            cleaned_text = clean_text(seg["text"])
            
            # Salta segmenti vuoti dopo la pulizia
            if not cleaned_text:
                continue
                
            if seg["speaker"] != current_speaker:
                # Scrivi il buffer dello speaker precedente
                if buffer:
                    f.write(" ".join(buffer) + "\n\n")
                    buffer = []
                current_speaker = seg["speaker"]
                f.write(f"{current_speaker}:\n")
            
            buffer.append(cleaned_text)
        
        # Scrivi l'ultimo buffer
        if buffer:
            f.write(" ".join(buffer) + "\n")

# ---------------- Main ----------------
if __name__ == "__main__":
    print(f"[INFO] Cerco file MKV in {INPUT_DIR.absolute()}")
    mkv_files = list(INPUT_DIR.glob("*.mkv"))
    
    if not mkv_files:
        print(f"[WARN] Nessun file .mkv trovato in {INPUT_DIR}")
        exit(0)
    
    print(f"[INFO] Trovati {len(mkv_files)} file da elaborare")
    
    for mkv_file in mkv_files:
        print(f"\n{'='*60}")
        print(f"[INFO] Elaborazione: {mkv_file.name}")
        print(f"{'='*60}")
        
        audio_file = OUTPUT_DIR / (mkv_file.stem + ".wav")
        extract_audio(mkv_file, audio_file)

        transcript = transcribe(audio_file)
        diarization = diarize(audio_file)
        
        # Salva output intermedi
        with open(OUTPUT_DIR / f"{mkv_file.stem}_transcript.json", "w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)
        with open(OUTPUT_DIR / f"{mkv_file.stem}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization, f, indent=2, ensure_ascii=False)

        aligned = align_speakers(transcript, diarization)
        save_final(aligned, OUTPUT_DIR / f"{mkv_file.stem}_final.txt")
        
        print(f"[OK] {mkv_file.name} completato!")

    print(f"\n{'='*60}")
    print("[INFO] Tutto completato!")
    print(f"{'='*60}")