import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import struct
import json
import os
import shutil
from PIL import Image, ImageTk

MODA_MAGIC = b'MODA'

class ModaDecompiler:
    @staticmethod
    def extract_moda(filepath, output_dir):
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(4)
                if magic != MODA_MAGIC:
                    raise ValueError("Not a valid MODA file")
                
                # Read JSON metadata
                json_len = struct.unpack(">I", f.read(4))[0]
                meta_json = f.read(json_len).decode('utf-8')
                meta = json.loads(meta_json)
                
                # Read thumbnail
                thumb_name_len = struct.unpack(">H", f.read(2))[0]
                if thumb_name_len > 0:
                    thumb_name = f.read(thumb_name_len).decode('utf-8')
                    thumb_size = struct.unpack(">I", f.read(4))[0]
                    thumb_data = f.read(thumb_size)
                    with open(os.path.join(output_dir, thumb_name), 'wb') as thumb_file:
                        thumb_file.write(thumb_data)
                
                # Read tracks
                track_count = struct.unpack(">H", f.read(2))[0]
                for _ in range(track_count):
                    track_name_len = struct.unpack(">H", f.read(2))[0]
                    track_name = f.read(track_name_len).decode('utf-8')
                    track_size = struct.unpack(">I", f.read(4))[0]
                    track_data = f.read(track_size)
                    
                    with open(os.path.join(output_dir, track_name), 'wb') as track_file:
                        track_file.write(track_data)
                
                # Save metadata as JSON
                with open(os.path.join(output_dir, "meta.json"), 'w') as meta_file:
                    json.dump(meta, meta_file, indent=2)
                
                return meta
        except Exception as e:
            raise ValueError(f"Error extracting MODA file: {str(e)}")

class ModaDecompilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MODA Decompiler 🛠️")
        self.root.geometry("500x400")
        
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
        self.file_label = ttk.Label(file_frame, text="No file selected", wraplength=400)
        self.file_label.pack(pady=5)
        
        # Output Section
        output_frame = ttk.LabelFrame(main_frame, text="📂 Output Folder", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(output_frame, text="📁 Choose Output Folder", command=self.choose_output).pack(fill=tk.X)
        self.output_label = ttk.Label(output_frame, text="No folder selected", wraplength=400)
        self.output_label.pack(pady=5)
        
        # Info Section
        info_frame = ttk.LabelFrame(main_frame, text="ℹ️ File Info", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.mode_label = ttk.Label(info_frame, text="Play Mode: -")
        self.mode_label.pack(anchor=tk.W)
        
        self.tracks_label = ttk.Label(info_frame, text="Tracks: 0")
        self.tracks_label.pack(anchor=tk.W)
        
        # Extract Button
        ttk.Button(main_frame, text="🛠️ Extract Files", command=self.extract_files, style='Accent.TButton').pack(fill=tk.X, pady=10)
        
        self.current_file = None
        self.output_dir = None
    
    def open_file(self):
        file = filedialog.askopenfilename(
            title="Open MODA File",
            filetypes=[("MODA Files", "*.moda")]
        )
        if file:
            self.current_file = file
            self.file_label.config(text=os.path.basename(file))
            
            # Try to read basic info without full extraction
            try:
                with open(file, 'rb') as f:
                    magic = f.read(4)
                    if magic != MODA_MAGIC:
                        raise ValueError("Not a valid MODA file")
                    
                    json_len = struct.unpack(">I", f.read(4))[0]
                    meta_json = f.read(json_len).decode('utf-8')
                    meta = json.loads(meta_json)
                    
                    self.mode_label.config(text=f"Play Mode: {meta.get('play_mode', 'unknown')}")
                    self.tracks_label.config(text=f"Tracks: {len(meta.get('tracks', []))}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read MODA file info:\n{str(e)}")
    
    def choose_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir = folder
            self.output_label.config(text=folder)
    
    def extract_files(self):
        if not self.current_file:
            messagebox.showerror("Error", "Please select a MODA file first!")
            return
        if not self.output_dir:
            messagebox.showerror("Error", "Please select an output folder!")
            return
            
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Extract files
            meta = ModaDecompiler.extract_moda(self.current_file, self.output_dir)
            
            messagebox.showinfo(
                "Success", 
                f"Extracted {len(meta.get('tracks', []))} tracks to:\n{self.output_dir}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract MODA file:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModaDecompilerApp(root)
    root.mainloop()