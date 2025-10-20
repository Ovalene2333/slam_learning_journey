import os
import re
import sys
import textwrap

def convert_formula_in_file(file_path):
    """
    Opens a file, replaces all indented/non-indented $$...$$ blocks
    with ```math...```, preserving indentation, and writes back the changes.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 更新正则表达式以捕获三个部分：
        # 1. ^(\s*): 捕获行首的任意空白字符（即缩进）。必须使用 MULTILINE 模式。
        # 2. \$\$: 匹配 $$ 符号。
        # 3. (.*?): 非贪婪地捕获两个 $$ 之间的所有内容，包括换行符（需要 DOTALL 模式）。
        # 4. \$\$: 匹配结束的 $$ 符号。
        # 5. $: 匹配行尾，确保 $$ 后面没有其他字符（可选，但更严谨）。
        pattern = r'^(\s*)\$\$(.*?)\$\$$'

        # 使用 re.DOTALL 使 '.' 匹配换行符，re.MULTILINE 使 '^' 和 '$' 匹配行的开头和结尾
        new_content, num_replacements = re.subn(
            pattern,
            replace_with_indented_math_block,
            content,
            flags=re.DOTALL | re.MULTILINE
        )

        if num_replacements > 0:
            print(f"  -> 找到并转换了 {num_replacements} 个公式块。")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return num_replacements > 0

    except Exception as e:
        print(f"  -> 处理文件时出错: {e}")
        return False

def replace_with_indented_math_block(match):
    """
    This function is called for every match found by re.sub.
    It formats the replacement string while preserving indentation.
    """
    # group(1) 是行首的缩进
    indentation = match.group(1)
    
    # group(2) 是 $$ 之间的原始公式内容
    formula_content_raw = match.group(2)
    
    # 1. textwrap.dedent() 会移除整个代码块的公共前导空白
    #    这对于处理多行、且内部有缩进的公式至关重要
    dedented_content = textwrap.dedent(formula_content_raw)
    
    # 2. .strip() 会移除 dedent 后可能残留的、位于开头和结尾的空行
    cleaned_content = dedented_content.strip()
    
    # 3. 构建新的代码块，将原始缩进应用到 ```math 的开头和结尾
    #    公式内容本身则不再需要额外缩进
    return f"{indentation}```math\n{indentation}{cleaned_content}\n{indentation}```"

def process_directory(target_dir):
    """
    Recursively walks through the target directory and processes all markdown files.
    """
    if not os.path.isdir(target_dir):
        print(f"错误: 目录 '{target_dir}' 不存在。")
        return

    print(f"\n开始扫描目录: {target_dir}\n")
    
    processed_files_count = 0
    changed_files_count = 0

    for root, _, files in os.walk(target_dir):
        for filename in files:
            if filename.lower().endswith(('.md', '.markdown')):
                file_path = os.path.join(root, filename)
                print(f"正在处理: {file_path}")
                processed_files_count += 1
                if convert_formula_in_file(file_path):
                    changed_files_count += 1

    print("\n--------------------")
    print("扫描完成！")
    print(f"总共检查了 {processed_files_count} 个 Markdown 文件。")
    print(f"总共修改了 {changed_files_count} 个文件。")
    print("--------------------")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("请输入要转换的 Markdown 文件所在的目录路径 (默认为当前目录 '.'): ")
        if not directory:
            directory = '.'

    print("\n**重要提示**: 此脚本会直接修改原始文件。")
    print("**建议在运行前备份您的目录。**")
    
    confirm = input("您确定要继续吗? (y/n): ")

    if confirm.lower() == 'y':
        process_directory(directory)
    else:
        print("操作已取消。")