import os
from flask import Flask, render_template, send_from_directory, request, jsonify

app = Flask(__name__)
DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "downloads")

def get_chapters():
    chapters = []
    if os.path.exists(DOWNLOADS_FOLDER):
        for d in os.listdir(DOWNLOADS_FOLDER):
            path = os.path.join(DOWNLOADS_FOLDER, d)
            if os.path.isdir(path):
                try: chapters.append(int(d))
                except ValueError: continue
    return sorted(chapters)

def get_images_in_chapter(chapter):
    chapter_dir = os.path.join(DOWNLOADS_FOLDER, str(chapter))
    return sorted([f for f in os.listdir(chapter_dir) if f.endswith('.png')]) if os.path.exists(chapter_dir) else []

@app.route('/')
def index():
    return render_template('index.html', chapters=get_chapters())

@app.route('/read/<int:chapter>')
def read_chapter(chapter):
    return render_template('read.html', chapter=chapter)

@app.route('/load_images')
def load_images():
    chapter = request.args.get('chapter', type=int)
    start = request.args.get('start', type=int)
    count = request.args.get('count', type=int)
    
    imgs = get_images_in_chapter(chapter)
    images = imgs[start:start+count]
    next_start = start + count if start + count < len(imgs) else None
    
    return jsonify({
        "images": [{"filename": f} for f in images],
        "next_start": next_start
    })

@app.route('/chapter_image/<int:chapter>/<filename>')
def chapter_image(chapter, filename):
    return send_from_directory(os.path.join(DOWNLOADS_FOLDER, str(chapter)), filename)

if __name__ == '__main__':
    app.run(debug=True ,host="0.0.0.0" , port="1234")
