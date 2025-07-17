import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import struct
import os
from PIL import Image, ImageTk

MODA_MAGIC = b'MODA'

class ModaCompiler:
    @staticmethod
    def build_moda_file(tracks, play_mode, thumbnail_path, output_path):
        meta = {
            "play_mode": play_mode,
            "tracks": [{"file": os.path.basename(t), "order": i+1} for i, t in enumerate(tracks)],
            "thumbnail": os.path.basename(thumbnail_path) if thumbnail_path else None
        }
        meta_json = json.dumps(meta, indent=2).encode('utf-8')
        
        moda_data = bytearray()
        moda_data += MODA_MAGIC
        moda_data += struct.pack(">I", len(meta_json))  # JSON length (4 bytes)
        moda_data += meta_json

        # Add thumbnail
        if thumbnail_path:
            with open(thumbnail_path, 'rb') as f:
                thumb_data = f.read()
            thumb_name = os.path.basename(thumbnail_path).encode('utf-8')
            moda_data += struct.pack(">H", len(thumb_name))  # Name length (2 bytes)
            moda_data += thumb_name
            moda_data += struct.pack(">I", len(thumb_data))  # Data length (4 bytes)
            moda_data += thumb_data
        else:
            moda_data += struct.pack(">H", 0)  # No thumbnail

        # Add tracks
        moda_data += struct.pack(">H", len(tracks))  # Track count (2 bytes)
        for tpath in tracks:
            with open(tpath, 'rb') as f:
                tdata = f.read()
            tname = os.path.basename(tpath).encode('utf-8')
            moda_data += struct.pack(">H", len(tname))  # Name length (2 bytes)
            moda_data += tname
            moda_data += struct.pack(">I", len(tdata))  # Data length (4 bytes)
            moda_data += tdata

        with open(output_path, 'wb') as f:
            f.write(moda_data)

class ModaCompilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MODA Compiler 🔊")
        self.root.geometry("600x500")
        
        style = ttk.Style()
        style.configure('TButton', font=('Helvetica', 10))
        style.configure('TLabel', font=('Helvetica', 10))

        self.tracks = []
        self.thumbnail = None
        self.play_mode = tk.StringVar(value="sequential")
        self.thumbnail_preview = None

        # Main Frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Track Section
        track_frame = ttk.LabelFrame(main_frame, text="🎵 Audio Tracks", padding="10")
        track_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(track_frame, text="➕ Add Audio Tracks", command=self.add_tracks).pack(fill=tk.X)
        
        self.track_list = tk.Listbox(track_frame, height=5)
        self.track_list.pack(fill=tk.X, pady=5)
        ttk.Button(track_frame, text="❌ Remove Selected", command=self.remove_track).pack(fill=tk.X)

        # Play Mode
        mode_frame = ttk.LabelFrame(main_frame, text="🔁 Play Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(mode_frame, text="Sequential (play one by one)", variable=self.play_mode, value="sequential").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Parallel (play all together)", variable=self.play_mode, value="parallel").pack(anchor=tk.W)

        # Thumbnail Section
        thumb_frame = ttk.LabelFrame(main_frame, text="🖼️ Thumbnail", padding="10")
        thumb_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(thumb_frame, text="📁 Choose Thumbnail", command=self.choose_thumbnail).pack(fill=tk.X)
        self.thumb_label = ttk.Label(thumb_frame)
        self.thumb_label.pack(pady=5)

        # Save Button
        ttk.Button(main_frame, text="💾 Save as .moda", command=self.save_moda, style='Accent.TButton').pack(fill=tk.X, pady=10)

    def add_tracks(self):
        files = filedialog.askopenfilenames(
            title="Select Audio Files",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac")]
        )
        if files:
            self.tracks.extend(files)
            for f in files:
                self.track_list.insert(tk.END, os.path.basename(f))

    def remove_track(self):
        selection = self.track_list.curselection()
        if selection:
            index = selection[0]
            self.track_list.delete(index)
            del self.tracks[index]

    def choose_thumbnail(self):
        file = filedialog.askopenfilename(
            title="Select Thumbnail",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif")]
        )
        if file:
            self.thumbnail = file
            try:
                img = Image.open(file)
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
                self.thumb_label.config(image=photo)
                self.thumb_label.image = photo
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

    def save_moda(self):
        if not self.tracks:
            messagebox.showerror("Error", "Please add at least one audio track!")
            return
            
        file = filedialog.asksaveasfilename(
            defaultextension=".moda",
            filetypes=[("MODA Files", "*.moda")],
            title="Save MODA File"
        )
        if file:
            try:
                ModaCompiler.build_moda_file(
                    self.tracks,
                    self.play_mode.get(),
                    self.thumbnail,
                    file
                )
                messagebox.showinfo("Success", f"MODA file saved successfully:\n{file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save MODA file:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModaCompilerApp(root)
    root.mainloop()