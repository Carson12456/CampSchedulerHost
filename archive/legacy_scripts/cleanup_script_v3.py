import os
import shutil
import stat

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

def handle_remove_readonly(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == 13: # EACCES
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise

def main():
    base_dir = os.getcwd()
    print(f"Force cleaning directories in {base_dir}...")
    
    # Delete directories
    for dir_name in DELETE_DIRS:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path, ignore_errors=False, onerror=handle_remove_readonly)
                print(f"Deleted directory: {dir_name}")
            except Exception as e:
                print(f"Error deleting directory {dir_name}: {e}")
        else:
             # Check if it was actually deleted or just not found
             if not os.path.exists(dir_path):
                 print(f"Directory gone: {dir_name}")
             else:
                 print(f"Directory exists but not isdir?: {dir_name}")

    print("\nForce cleanup complete.")

if __name__ == "__main__":
    main()
