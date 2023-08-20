import os
from utils.binary_matcher import BinaryMatcher
import tkinter as tk
from tkinter import filedialog

def select_folder(title=None):
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_path = filedialog.askdirectory(title=title)  # Show folder selection dialog
    return folder_path

# Select the source folder (the folder containing the target DL file)
source_folder = select_folder("検証したいDL対象ファイル本体と、DL元になったtorrentファイルが存在するフォルダを選択")
print("対象フォルダの一覧を作成しています……")

# List all sub-folders under the source folder which contain .bin files
sub_folders = [os.path.join(source_folder, d) for d in os.listdir(source_folder) if os.path.isdir(os.path.join(source_folder, d))]
piece_folders_list = [f for f in sub_folders if any(fn.endswith('.bin') for fn in os.listdir(f))]

# Initialize results dictionary
results = {}

print("バイナリマッチを試行中……")

# Iterate through each piece folder and .bin file
for piece_folder in piece_folders_list:
    # Create an instance of BinaryMatcher for each piece folder
    matcher = BinaryMatcher(source_folder, piece_folder)
    
    bin_files = [f for f in os.listdir(piece_folder) if f.endswith('.bin') and os.path.isfile(os.path.join(piece_folder, f))]
    for bin_file in bin_files:
        result = matcher.binary_match(bin_file)
        results[bin_file] = result

# Check the results
if not any(value == False for value in results.values()):
    print("すべてのピースが元ファイルの内容と一致しました。")
else:
    mismatched_pieces = [key for key, value in results.items() if value == False]
    print("次のピースが元ファイルの内容と一致しませんでした：")
    for piece in mismatched_pieces:
        print(piece)