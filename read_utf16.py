
import sys

def convert_utf16_to_utf8(input_path, output_path):
    try:
        with open(input_path, 'r', encoding='utf-16-le') as f:
            content = f.read()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Successfully converted {input_path} to {output_path}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    convert_utf16_to_utf8("regression_run_output.txt", "regression_output_utf8.txt")
