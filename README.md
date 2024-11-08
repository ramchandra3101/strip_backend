module avail  python 
module load python/3.10.1
python3 -m venv pythonenv
source pythonenv/bin/activate
pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000
pythonenv/Scripts/activate
10.130.230.116
cd C:\Users\yerramsetti\Desktop\Ramachandra\Strip_backend
    