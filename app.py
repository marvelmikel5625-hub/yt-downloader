import os, re, tempfile, threading, uuid
from flask import Flask, request, jsonify, send_file, send_from_directory
import yt_dlp

app = Flask(__name__)
JOBS = {}
RE = re.compile(r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w-]+')

def worker(job_id, url, fmt, tmp):
    def hook(d):
        j = JOBS[job_id]
        if d['status'] == 'downloading':
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            j['progress'] = int(d.get('downloaded_bytes', 0) / tot * 100) if tot else 0
        elif d['status'] == 'finished':
            j['progress'] = 100; j['status'] = 'ready'
    try:
        with yt_dlp.YoutubeDL({
            'format': fmt or 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(tmp, '%(title).80s.%(ext)s'),
            'merge_output_format': 'mp4', 'progress_hooks': [hook],
            'quiet': True, 'noplaylist': True, 'restrictfilenames': True,
        }) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                base = os.path.splitext(path)[0]
                for e in ('.mp4', '.mkv', '.webm'):
                    if os.path.exists(base + e): path = base + e; break
            JOBS[job_id].update(status='ready', filepath=path)
    except Exception as e:
        JOBS[job_id].update(status='error', error=str(e))

@app.route('/')
def index(): return send_from_directory('.', 'index.html')

@app.route('/api/info', methods=['POST'])
def info():
    url = (request.json or {}).get('url', '').strip()
    if not RE.match(url): return jsonify(error='Invalid YouTube URL'), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            i = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify(error=str(e)), 400
    fmts, seen = [], set()
    for f in i.get('formats', []):
        if f.get('vcodec') == 'none' or not f.get('height'): continue
        if f['height'] in seen: continue
        seen.add(f['height'])
        fmts.append({'id': f['format_id'], 'label': f"{f['height']}p", 'ext': f.get('ext')})
    fmts.sort(key=lambda x: int(x['label'][:-1]), reverse=True)
    return jsonify(title=i.get('title'), thumbnail=i.get('thumbnail'),
                   formats=fmts[:6], duration=i.get('duration'))

@app.route('/api/download', methods=['POST'])
def dl():
    d = request.json or {}
    url, fmt = d.get('url', '').strip(), d.get('format_id')
    if not RE.match(url): return jsonify(error='Invalid URL'), 400
    jid = uuid.uuid4().hex
    tmp = tempfile.mkdtemp(prefix='ytdl_')
    JOBS[jid] = {'status': 'downloading', 'progress': 0, 'tmpdir': tmp}
    threading.Thread(target=worker, args=(jid, url, fmt, tmp), daemon=True).start()
    return jsonify(job_id=jid)

@app.route('/api/progress/<jid>')
def prog(jid):
    j = JOBS.get(jid)
    if not j: return jsonify(error='not found'), 404
    return jsonify(status=j['status'], progress=j.get('progress', 0), error=j.get('error'))

@app.route('/api/file/<jid>')
def f(jid):
    j = JOBS.get(jid)
    if not j or j['status'] != 'ready': return jsonify(error='not ready'), 400
    r = send_file(j['filepath'], as_attachment=True,
                  download_name=os.path.basename(j['filepath']))
    @r.call_on_close
    def cleanup():
        try: os.remove(j['filepath']); os.rmdir(j['tmpdir'])
        except OSError: pass
        JOBS.pop(jid, None)
    return r

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, threaded=True)
