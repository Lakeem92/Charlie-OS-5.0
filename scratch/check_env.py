from pathlib import Path
import os

repo_root = Path(__file__).resolve().parents[1]
envp = repo_root / '.env'
print('env_exists', envp.exists())
found = {}
if envp.exists():
    text = envp.read_text(encoding='utf-8')
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        if k.startswith('ALPACA') or k.startswith('APCA'):
            found[k] = True
            # do not print values

print('keys_in_file:', sorted(found.keys()))

# Now load into process env (only allowed keys)
allowed = {'APCA_API_KEY_ID','APCA_API_SECRET_KEY','ALPACA_API_KEY','ALPACA_API_SECRET','APCA_API_BASE_URL','ALPACA_API_BASE_URL'}
if envp.exists():
    for line in envp.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v = line.split('=',1)
        k=k.strip(); v=v.strip().strip('"\'')
        if k in allowed and not os.getenv(k):
            os.environ[k]=v

print('env_set:', {k: bool(os.getenv(k)) for k in sorted(allowed)})
