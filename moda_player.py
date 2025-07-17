import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import struct
import json
import os
import tempfile
from PIL import Image, ImageTk
import pygame
from pygame import mixer
import threading
import time

MODA_MAGIC = b'MODA'

class ModaPlayer:
    def __init__(self):
        pygame.init()
        mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        self.temp_dir = None
        self.current_track = 0
        self.is_playing = False
        self.tracks_meta = []
        self.play_mode = ""
        self.thumbnail_path = None
        self.audio_threads = []
        self.sound_objects = []

    def load_moda(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(4)
                if magic != MODA_MAGIC:
                    raise ValueError("Not a valid MODA file")
                
                # Read JSON metadata
                json_len = struct.unpack(">I", f.read(4))[0]
                meta_json = f.read(json_len).decode('utf-8')
                meta = json.loads(meta_json)
                self.play_mode = meta.get("play_mode", "sequential")
                self.tracks_meta = meta.get("tracks", [])
                
                # Read thumbnail
                thumb_name_len = struct.unpack(">H", f.read(2))[0]
                if thumb_name_len > 0:
                    thumb_name = f.read(thumb_name_len).decode('utf-8')
                    thumb_size = struct.unpack(">I", f.read(4))[0]
                    thumb_data = f.read(thumb_size)
                    self.thumbnail_path = os.path.join(tempfile.gettempdir(), thumb_name)
                    with open(self.thumbnail_path, 'wb') as thumb_file:
                        thumb_file.write(thumb_data)
                
                # Create temp dir for audio files
                self.temp_dir = tempfile.mkdtemp(prefix="moda_")
                
                # Read tracks
                track_count = struct.unpack(">H", f.read(2))[0]
                for _ in range(track_count):
                    track_name_len = struct.unpack(">H", f.read(2))[0]
                    track_name = f.read(track_name_len).decode('utf-8')
                    track_size = struct.unpack(">I", f.read(4))[0]
                    track_data = f.read(track_size)
                    
                    track_path = os.path.join(self.temp_dir, track_name)
                    with open(track_path, 'wb') as track_file:
                        track_file.write(track_data)
                
                return meta
        except Exception as e:
            raise ValueError(f"Error loading MODA file: {str(e)}")

    def play_parallel(self):
        """Play all tracks simultaneously using multi-threading"""
        self.stop()  # Stop any currently playing audio
        
        # Pre-load all sounds
        self.sound_objects = []
        for track in self.tracks_meta:
            track_path = os.path.join(self.temp_dir, track["file"])
            try:
                sound = mixer.Sound(track_path)
                self.sound_objects.append(sound)
            except Exception as e:
                print(f"Error loading track {track['file']}: {e}")
                continue
        
        # Create and start threads for each track
        self.audio_threads = []
        for sound in self.sound_objects:
            thread = threading.Thread(target=self._play_sound, args=(sound,))
            thread.daemon = True
            self.audio_threads.append(thread)
        
        # Start all threads at the same time
        for thread in self.audio_threads:
            thread.start()
        
        self.is_playing = True

    def _play_sound(self, sound):
        """Thread target function to play a sound"""
        channel = mixer.find_channel()
        if channel:
            channel.play(sound)
            while channel.get_busy():
                time.sleep(0.1)

    def play_sequential(self):
        """Play tracks one by one"""
        if self.current_track < len(self.tracks_meta):
            track = self.tracks_meta[self.current_track]
            track_path = os.path.join(self.temp_dir, track["file"])
            try:
                sound = mixer.Sound(track_path)
                self.sound_objects = [sound]  # Keep reference to avoid garbage collection
                channel = mixer.find_channel()
                if channel:
                    channel.play(sound)
                    channel.set_endevent(pygame.USEREVENT)
                    self.is_playing = True
            except Exception as e:
                print(f"Error playing track {track['file']}: {e}")
                self.current_track += 1
                self.play_sequential()

    def play(self):
        if not self.tracks_meta:
            return
            
        if self.play_mode == "parallel":
            self.play_parallel()
        else:  # sequential
            self.play_sequential()
    
    def stop(self):
        mixer.stop()
        self.is_playing = False
        self.current_track = 0
        self.sound_objects = []  # Clear sound references
    
    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:
                self.current_track += 1
                if self.current_track < len(self.tracks_meta):
                    self.play_sequential()
                else:
                    self.is_playing = False
                    self.current_track = 0
        return self.is_playing

    def cleanup(self):
        self.stop()
        if self.temp_dir and os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
            os.remove(self.thumbnail_path)

class ModaPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MODA Player 🔊")
        self.root.geometry("500x600")
        
        self.player = ModaPlayer()
        self.current_file = None
        self.thumbnail_img = None
        
        style = ttk.Style()
        style.configure('TButton', font=('Helvetica', 10))
        style.configure('TLabel', font=('Helvetica', 10))
        
        # Main Frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File Section
        file_frame = ttk.LabelFrame(main_frame, text="📁 MODA File", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="📂 Open .moda File", command=self.open_file).pack(fill=tk.X)
        self.file_label = ttk.Label(file_frame, text="No file loaded", wraplength=400)
        self.file_label.pack(pady=5)
        
        # Thumbnail Section
        self.thumb_frame = ttk.LabelFrame(main_frame, text="🖼️ Thumbnail", padding="10")
        self.thumb_frame.pack(fill=tk.X, pady=5)
        self.thumb_label = ttk.Label(self.thumb_frame)
        self.thumb_label.pack()
        
        # Info Section
        info_frame = ttk.LabelFrame(main_frame, text="ℹ️ File Info", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.mode_label = ttk.Label(info_frame, text="Play Mode: -")
        self.mode_label.pack(anchor=tk.W)
        
        self.tracks_label = ttk.Label(info_frame, text="Tracks: 0")
        self.tracks_label.pack(anchor=tk.W)
        
        # Controls
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.play_btn = ttk.Button(control_frame, text="▶️ Play", command=self.play, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, expand=True)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Stop", command=self.stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True)
        
        # Track List
        track_frame = ttk.LabelFrame(main_frame, text="🎵 Tracks", padding="10")
        track_frame.pack(fill=tk.BOTH, expand=True)
        
        self.track_list = tk.Listbox(track_frame)
        self.track_list.pack(fill=tk.BOTH, expand=True)
        
        # Update player events periodically
        self.update_player()
    
    def open_file(self):
        file = filedialog.askopenfilename(
            title="Open MODA File",
            filetypes=[("MODA Files", "*.moda")]
        )
        if file:
            try:
                self.player.cleanup()
                meta = self.player.load_moda(file)
                self.current_file = file
                
                # Update UI
                self.file_label.config(text=os.path.basename(file))
                self.mode_label.config(text=f"Play Mode: {meta.get('play_mode', 'unknown')}")
                self.tracks_label.config(text=f"Tracks: {len(meta.get('tracks', []))}")
                
                # Load thumbnail
                if self.player.thumbnail_path:
                    try:
                        img = Image.open(self.player.thumbnail_path)
                        img.thumbnail((300, 300))
                        self.thumbnail_img = ImageTk.PhotoImage(img)
                        self.thumb_label.config(image=self.thumbnail_img)
                    except Exception as e:
                        print(f"Error loading thumbnail: {e}")
                        self.thumb_label.config(image='', text="No thumbnail")
                else:
                    self.thumb_label.config(image='', text="No thumbnail")
                
                # Populate track list
                self.track_list.delete(0, tk.END)
                for track in meta.get('tracks', []):
                    self.track_list.insert(tk.END, f"{track['order']}. {track['file']}")
                
                self.play_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.NORMAL)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load MODA file:\n{str(e)}")
    
    def play(self):
        if self.current_file:
            self.player.play()
            self.play_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
    
    def stop(self):
        self.player.stop()
        self.play_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def update_player(self):
        if self.player.is_playing:
            self.player.check_events()
        self.root.after(100, self.update_player)
    
    def on_close(self):
        self.player.cleanup()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModaPlayerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()