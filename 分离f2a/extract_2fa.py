def extract_2fa(input_file, output_file, column_index=5, delimiter=None):
    """
    从输入文件中提取2FA密钥并保存到输出文件
    
    :param input_file: 输入文件路径
    :param output_file: 输出文件路径
    :param column_index: 2FA密钥所在的列索引（默认为5，即第6列）
    :param delimiter: 分隔符，可以是':', '|', ' '等，若为None则自动检测常见分隔符
    """
    try:
        common_delimiters = [':', '|', ' ', '\t', ',']
        
        with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
            for line_num, line in enumerate(infile, 1):
                # 移除行尾的空白字符
                line = line.strip()
                if not line:
                    continue
                
                # 如果未指定分隔符，则尝试检测
                if delimiter is None:
                    # 检测这一行中哪个分隔符出现最多
                    max_count = 0
                    detected_delimiter = ':'  # 默认使用冒号
                    
                    for delim in common_delimiters:
                        count = line.count(delim)
                        if count > max_count:
                            max_count = count
                            detected_delimiter = delim
                    
                    parts = line.split(detected_delimiter)
                else:
                    parts = line.split(delimiter)
                
                # 检查是否有足够的部分
                if len(parts) > column_index and parts[column_index]:
                    outfile.write(f"{parts[column_index]}\n")
                else:
                    print(f"警告: 第{line_num}行没有足够的列或指定列为空")
        
        print(f"2FA密钥已成功提取到 {output_file}")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")

if __name__ == "__main__":
    import sys
    import argparse
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='从文本文件中提取2FA密钥')
    parser.add_argument('input_file', help='输入文件路径')
    parser.add_argument('output_file', help='输出文件路径')
    parser.add_argument('-c', '--column', type=int, default=5, 
                        help='2FA密钥所在的列索引（从0开始，默认为5，即第6列）')
    parser.add_argument('-d', '--delimiter', 
                        help='分隔符，例如":", "|", " "等。若不指定则自动检测')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 执行提取操作
    extract_2fa(args.input_file, args.output_file, args.column, args.delimiter)