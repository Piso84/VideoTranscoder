----- istruzioni installazione su Linux (seguire un passo alla volta) -----

setopt interactive_comments

sudo pacman -S uv ffmpeg

cd ~/Scrivania/CallTranscoder

# Tutto resta dentro la cartella di progetto
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
export UV_CACHE_DIR="$PWD/.uv-cache"

# Scarica Python 3.11 in ./.python
uv python install 3.11

# Crea il venv usando quell'interprete
sudo uv venv --python 3.11 .venv

# Attivalo
source .venv/bin/activate

# Installa le dipendenze
sudo uv pip install -r requirements.txt

#Per non riesportare le variabili a ogni sessione, crea un env.sh:
cat > env.sh << 'EOF'
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
export UV_CACHE_DIR="$PWD/.uv-cache"
source .venv/bin/activate
EOF

#Evita di versionare le cartelle generate:
printf '.python/\n.venv/\n.uv-cache/\n' >> .gitignore

sudo uv pip list | grep -i onnxruntime
sudo uv pip install -U onnxruntime

sudo uv pip install "numpy<2"

python -c "import numpy; print(numpy.__version__)"
python -c "import onnxruntime; print(onnxruntime.__version__)"

---

ad ogni avvio:

set HF_TOKEN=v. LastPass
source env.sh
python process.py


---- istruzioni Windows (x Simona) ----

1) Scaricare e unzippare il file, in qualsiasi cartella

2) Scaricare Python 3.11 (serve questa versione per questioni di compatibilità fra le librerie) da
https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
e installarlo; durante la procedura di installazione, scegliere come cartella di destinazione una cartella Python creata dentro CallTranscoder.

3) Scaricare ffmpeg per Windows dal seguente link:
https://www.gyan.dev/ffmpeg/builds
Scompattarlo dove vuoi (anche sotto la stessa cartella CallTranscoder);
aprire le variabili d'ambiente di Windows (o della tua utenza) e aggiungere alla variabile Path il percorso completo di ffmpeg/bin

4) Aprire un terminale e posizionarsi dentro la cartella CallTranscoder ("cd" ecc.)
Eseguire in serie i seguenti comandi:

Python\python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

5) Se tutto è andato a buon fine, si è pronti per lanciare una trascrizione.
Occorre inserire un file .mkv nella cartella input e poi eseguire il file run.bat.
Al termine dell'operazione, sotto la cartella output, troverai tutti i file prodotti (v. in particolare la versione "final").


N.B. Come anticipato, poiché non ho una scheda video particolarmente moderna, sono costretto a lanciare lo script in modalità "cpu" (più lenta).
Se vuoi fare un tentativo con la tua, basta intervieni nel file process.py. In alto trovi la seguente riga:
DEVICE = "cpu"  # "cuda" se hai GPU NVIDIA
Devi semplicemente sostituire "cpu" con "cuda".

