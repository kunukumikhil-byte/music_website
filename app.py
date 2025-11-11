from flask import Flask, render_template, request, redirect, session, send_from_directory
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "SECRET_KEY_CHANGE_IT"

# Folder for uploads
UPLOAD_FOLDER_SONGS = "static/songs"
UPLOAD_FOLDER_IMAGES = "static/images"

os.makedirs(UPLOAD_FOLDER_SONGS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_IMAGES, exist_ok=True)


# ✅ Initialize Database Automatically
def init_db():
    conn = sqlite3.connect("music.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT,
        image TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        user_id INTEGER
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS playlist_songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER,
        song_id INTEGER
    )""")

    conn.commit()
    conn.close()


init_db()  # ✅ Create tables if not exists


# ✅ Home Page (Songs Display)
@app.route("/")
def home():
    q = request.args.get("q", "")  # ✅ read search query from URL

    conn = sqlite3.connect("music.db")
    cur = conn.cursor()

    if q:
        cur.execute("SELECT * FROM songs WHERE title LIKE ?", ("%" + q + "%",))
    else:
        cur.execute("SELECT * FROM songs")

    songs = cur.fetchall()

    playlists = []
    if "user_id" in session:
        cur.execute("SELECT id, name FROM playlists WHERE user_id = ?", (session["user_id"],))
        playlists = cur.fetchall()

    conn.close()
    return render_template("index.html", songs=songs, playlists=playlists, q=q)

# ✅ Admin Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Hardcoded admin
        if username == "jupiter" and password == "jupiter17072007":
            session["admin"] = True
            return redirect("/admin")

        return "Invalid admin credentials!"

    return render_template("login.html")


# ✅ Admin Panel (Upload Song + Image)
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        song_file = request.files["song"]
        image_file = request.files["image"]

        song_filename = song_file.filename
        image_filename = image_file.filename

        song_file.save(os.path.join(UPLOAD_FOLDER_SONGS, song_filename))
        image_file.save(os.path.join(UPLOAD_FOLDER_IMAGES, image_filename))

        conn = sqlite3.connect("music.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO songs (title, filename, image) VALUES (?, ?, ?)",
            (title, song_filename, image_filename)
        )
        conn.commit()
        conn.close()

        return redirect("/admin")

    conn = sqlite3.connect("music.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM songs")
    songs = cur.fetchall()
    conn.close()

    return render_template("admin.html", songs=songs)


# ✅ Delete Song (Admin Only)
@app.route("/delete/<int:id>")
def delete_song(id):
    if "admin" not in session:
        return redirect("/login")

    conn = sqlite3.connect("music.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM songs WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


# ✅ User Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("music.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        return redirect("/login_user")

    return render_template("signup.html")


# ✅ User Login
@app.route("/login_user", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("music.db")
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["username"] = username
            session["user_id"] = user[0]
            return redirect("/")

        return "Invalid user login!"

    return render_template("login_user.html")


# ✅ Logout (User / Admin)
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ✅ CREATE Playlist
@app.route("/playlist/create", methods=["POST"])
def playlist_create():
    playlist_name = request.form.get("playlist_name")
    user_id = session["user_id"]

    conn = sqlite3.connect("music.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO playlists (name, user_id) VALUES (?, ?)", (playlist_name, user_id))
    conn.commit()
    conn.close()

    return redirect("/")


# ✅ ADD Song to Playlist
@app.route("/playlist/add/<int:song_id>", methods=["POST"])
def add_to_playlist(song_id):
    playlist_id = request.form.get("playlist_id")

    conn = sqlite3.connect("music.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO playlist_songs (playlist_id, song_id) VALUES (?, ?)",
                (playlist_id, song_id))
    conn.commit()
    conn.close()

    return redirect("/")


# ✅ View My Playlists
@app.route("/playlists")
def playlists():
    conn = sqlite3.connect("music.db")
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM playlists WHERE user_id = ?", (session["user_id"],))
    playlists = cur.fetchall()

    conn.close()
    return render_template("playlist_list.html", playlists=playlists)


# ✅ Open a playlist (show songs)
@app.route("/playlist/<int:id>")
def playlist_view(id):
    conn = sqlite3.connect("music.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT songs.id, songs.title, songs.filename, songs.image, playlist_songs.id
    FROM playlist_songs
    JOIN songs ON songs.id = playlist_songs.song_id
    WHERE playlist_songs.playlist_id = ?
    """, (id,))
    songs = cur.fetchall()

    cur.execute("SELECT name FROM playlists WHERE id = ?", (id,))
    playlist_name = cur.fetchone()[0]

    conn.close()

    return render_template("playlist_view.html", songs=songs, playlist_name=playlist_name)


# ✅ Remove song from playlist
@app.route("/playlist/remove/<int:id>")
def remove_from_playlist(id):
    conn = sqlite3.connect("music.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM playlist_songs WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/playlists")


# ✅ Download Song
@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER_SONGS, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
