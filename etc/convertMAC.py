import os

def remove_leading_zeros_from_mac(mac):
    # 각 옥텟을 ':'로 나눈 뒤 int로 변환 → 다시 hex string(앞자리 0 제거)
    return ':'.join(str(int(part, 16)) for part in mac.split(':'))

def process_file(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.read().strip().splitlines()

    processed_lines = [remove_leading_zeros_from_mac(line.strip()) for line in lines if line.strip()]

    with open(output_file, 'w') as f:
        f.write('\n'.join(processed_lines))
    print(f"변환 완료! 결과가 '{output_file}'에 저장되었습니다.")

if __name__ == "__main__":
    # 현재 폴더의 입력 파일 경로
    input_file = "smart3mini_0801_10.txt"
    output_file = "smart3mini_0801_10_converted.txt"

    if not os.path.exists(input_file):
        print(f"입력 파일 '{input_file}'이(가) 존재하지 않습니다.")
    else:
        process_file(input_file, output_file)
