import os
import shutil

# Directories to delete
DELETE_DIRS = [
    "core",
    "infrastructure",
    "interfaces",
    "archive",
    "reports",
    "exports",
    "logs"
]

# Files to delete
DELETE_FILES = [
    "main.py",
     "CampScheduler_BeforeContextRestructuring.code-workspace"
]

def main():
    base_dir = os.getcwd()
    print(f"Cleaning up directories in {base_dir}...")
    
    # Delete directories
    for dir_name in DELETE_DIRS:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"Deleted directory: {dir_name}")
            except Exception as e:
                print(f"Error deleting directory {dir_name}: {e}")
        else:
            print(f"Directory not found (already deleted?): {dir_name}")

    # Delete files
    for file_name in DELETE_FILES:
        file_path = os.path.join(base_dir, file_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_name}")
            except Exception as e:
                print(f"Error deleting file {file_name}: {e}")
        else:
            print(f"File not found: {file_name}")

    print("\nCleanup clean sweep complete.")

if __name__ == "__main__":
    main()
