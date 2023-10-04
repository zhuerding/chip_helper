import hashlib
import pandas as pd
import sys
import os
import subprocess
import glob
import argparse
import time
import threading
import datetime


# 用于加载爱心进度条的类
class LoadingAnimation(threading.Thread):
    def __init__(self, process):
        super(LoadingAnimation, self).__init__()
        self.running = True
        self.process = process

    def run(self):
        heart_symbols = ['❤️ ', '💓 ', '💔 ', '💕 ', '💖 ', '💗 ', '💘 ', '💙 ', '💚 ', '💛 ', '💜 ', '🖤 ', '💝 ',
                         '💞 ',
                         '💟 ']
        while self.running:
            for symbol in heart_symbols:
                sys.stdout.write('\r' + f'{self.process}' + " " + symbol)
                sys.stdout.flush()
                time.sleep(0.2)

    def stop(self):
        self.running = False


# 用于运行shell脚本并获得实时输出后打印、输出至日志
class CMDProcess(threading.Thread):
    def __init__(self, args, callback, argument):
        threading.Thread.__init__(self)
        self.args = args
        self.argument = argument
        self.callback = callback
        self.cwd = './'

    def run(self):
        self.proc = subprocess.Popen(
            str(self.args),
            bufsize=1,  # bufsize=0时，为不缓存；bufsize=1时，按行缓存；bufsize为其他正整数时，为按照近似该正整数的字节数缓存
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 这里可以显示yolov5训练过程中出现的进度条等信息
            text=True,  # 缓存内容为文本，避免后续编码显示问题
            cwd=self.cwd  # 这个参数意思是，当前子进程结束后，其结果保存地址，比如yolov5训练进程结束后会输出模型、检测图片等，可在cwd中找到
        )
        while self.proc.poll() is None:
            line = self.proc.stdout.readline()
            self.proc.stdout.flush()  # 刷新缓存，防止缓存过多造成卡死
            # line = line.decode("utf8")
            if self.callback:
                self.callback(line, self.argument)
        self.proc.flush()


# 用于将输出信息打印或写入日志
def getSubInfo(text, argument):
    print(text + "")
    log(argument, text + '\n')


# 获取当前目录下所有SRR开头文件夹的程序
def get_srr_dirs():
    current_dir = os.getcwd()
    all_dirs = [d for d in os.listdir(current_dir) if
                os.path.isdir(os.path.join(current_dir, d)) and d.startswith("SRR")]
    return all_dirs


# 获取当前目录下所有FASTQ结尾文件的程序
def get_fastq_files(current_dir):
    all_files = glob.glob(os.path.join(current_dir, '*.fastq'))
    return all_files


# 程序运行参数配置函数
def args(parser):
    parser.add_argument('-r', type=str, default="../../hg38", help='参考基因组位置')
    parser.add_argument('-t', type=int, default="8", help='您选择的进程数')
    parser.add_argument('-s', type=int, default="./Sample list.csv", help='样品表的位置')
    parser.add_argument('-l', action='store_true', help='是否生成日志')
    parser.add_argument('-sra', type=str, default="/root/SRA_Toolkit/sratoolkit.3.0.7-centos_linux64/bin/",
                        help='SRA toolkit bin目录的位置')
    parser.add_argument('-q', type=str, default="0.01", help='call peak时的置信区间（须小于0.05）')
    parser.add_argument('-n', type=str, default='chip-seq_program', help='本次运行的程序名')
    parser.add_argument('-k', type=str, help='chip.py的密钥', required=True)
    argument = parser.parse_args()
    return argument


# 日志函数
def log(argument, msg):
    if argument.l is True:
        with open(f"{argument.n}.log", 'a', encoding="utf-8") as f:
            f.write(msg + '')
            f.close()
    else:
        pass


# 加载函数开始
def loading_begin(process):
    t = LoadingAnimation(process)
    t.start()
    return t


# 加载函数结束
def loading_stop(a):
    a.stop()
    a.join()


# 主程序开始
current_datetime = datetime.datetime.now()  # 获得当前时间戳
all_start_time = time.time()
formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
# 加载程序参数
parser = argparse.ArgumentParser(description="This is a chip-seq analysis helper. The program's key is 'puman', "
                                             "and please enter the key to ensure the program running normally."
                                             "This program can be used for free, but commercial charging is prohibited")
arguments = args(parser)
# 创建日志文件
if arguments.l is True:
    f = open(f"{arguments.n}.log", 'w', encoding="utf-8")
    f.write(formatted_datetime + '')
    f.write('Program is beginning')
    f.close()
print("--------------------------------------------------\n")
print("\033[1m" + "Welcome use the program designed by zhuerding\n" + "\033[0m")
print("--------------------------------------------------\n")
# 检测密码
# psw = input("Please input your access key")
hashed_psw = hashlib.sha256(arguments.k.encode()).hexdigest()  # 对密钥进行哈希加密
if hashed_psw == "b5f0a3bc3ee3ca246a764cbf3274a3c3a1a5fa64a35354a7bb90dfd564e2f0f3":
    print("Access\n")
    log(arguments, "Identity authentication passed\n")
else:
    log(arguments, "Identity authentication passed\n")
    print('Identity authentication failed. Program will be stopped in 5 seconds.')
    log(arguments, "Identity authentication failed.\n")
    stop_datetime = datetime.datetime.now()
    formatted_stop_datetime = stop_datetime.strftime("%Y-%m-%d %H:%M:%S")
    log(arguments, "\n--------------------------------------------------\n")
    log(arguments, f"Program stopped in {formatted_stop_datetime}\n")
    log(arguments, f"unsuccessfully.Reason for closure is identity authentication failed\n")
    time.sleep(5)
    sys.exit()
process = 'reading sample list……'
start_time = time.time()
log(arguments, "reading and verifying sample list……\n")
t = loading_begin(process)
# 读取样品表
df = pd.read_csv(arguments.s)
name_list = []
sample_list = []
sample_array = {}
# 比对样品表
curr = get_srr_dirs()
for i in df["sample_name"]:
    request_list = ''
    treatment = ""
    group = ""
    if i in curr:
        request_list = i
        name_list.append(request_list)
        sample_list.append(request_list)
        group = str(df.loc[df['sample_name'] == i, 'treatment'].values[0]) + "_" + \
                str(df.loc[df['sample_name'] == i, 'rep'].values[0])
        treatment = df.loc[df['sample_name'] == i, 'treatment'].values[0]
        sample_array[request_list] = {"group": group, "treatment": treatment}
name_list = tuple(name_list)
for i in name_list:
    for filename in os.listdir(f'./{i}/'):
        if filename.endswith('.bw'):
            sample_list.remove(i)
            log(arguments, f"!The .bw file about {i} may be existed. The program will not analyse {i}. !\n")
loading_stop(t)
stop_time = time.time()
used_time = stop_time - start_time
print("\n--------------------------------------------------\n")
print(f"\nReading is completed! Used:{used_time} sec. Start to analyse.")
print(f"Effective Task List is {','.join(name_list)}.")
log(arguments, "--------------------------------------------------\n")
log(arguments, f"Reading is completed! Used:{used_time} sec. Start to analyse.\n")
log(arguments, f"Effective Task List is {','.join(name_list)}.\n")
if sample_list:
    print(f"And I will analyse {','.join(sample_list)}")
    log(arguments, f"And I will analyse {','.join(sample_list)}\n")
else:
    print("\n! I have nothing to analyse. !")
    log(arguments, f"Nothing to analyse.\n")
os.environ["PATH"] += os.pathsep + arguments.sra
for i in sample_list:
    print(f"{i} is being analysed")
    process = ".fastq files is being created……"
    log(arguments, "\n--------------------------------------------------\n")
    log(arguments, f"{i} is being analysed\n")
    path = f'./{i}/'
    # 将.SRA文件转化为.fastq文件
    if len(get_fastq_files(path)) >= 1:
        print(f"{i}.fastq is existed. Jumped the process.")
        log(arguments, f"{i}.fastq is existed. Jumped the process.")
    else:
        start_time = time.time()
        print(".fastq files is being created")
        log(arguments, 'Begin to create .fastq files\n')
        t = loading_begin(process)
        cmd = f"fastq-dump -split-3 {i} -O {path}"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\nAll .sra files are converted to .fastq files. Used:{used_time} sec.")
        log(arguments, f"{i}_1.fastq and {i}_2.fastq are created.\n")
        log(arguments, f'.fastq files are created. Used:{used_time} sec. Start to trim adapter.\n')
    # 判断目录下FASTQ文件数目确定是否为双端测序
    if f'{i}_1.fastq' in os.listdir(path):
        # 去接头
        if f"{i}_n.fastq" not in os.listdir(path):
            start_time = time.time()
            process = "adapter trimming……"
            print("\nStart to trim adapter.")
            t = loading_begin(process)
            log(arguments, "\nadapter trimming\n")
            cmd = f'fastp -i {path}{i}_1.fastq -I {path}{i}_2.fastq -o {path}_1_n.fastq -O {path}{i}_2_n.fastq'
            ps = CMDProcess(cmd, getSubInfo, arguments)
            ps.start()
            ps.join()
            log(arguments, f"{i}_1_n.fastq and {i}_2_n.fastq are created.\n")
            cmd = f"rm -rf {path}{i}_1.fastq {path}{i}_2.fastq"
            ps = CMDProcess(cmd, getSubInfo, arguments)
            ps.start()
            ps.join()
            log(arguments, f"{i}_1.fastq and {i}_2.fastq are removed.\n")
            loading_stop(t)
            stop_time = time.time()
            used_time = stop_time - start_time
            print(f"\nAll .fastq files are trimmed adapter. Used: {used_time} sec. Start to quality control.")
            log(arguments, f"All .fastq files are trimmed adapter. Used: {used_time} sec. Start to quality control.\n")
        # 进行QC检测
        start_time = time.time()
        process = "quality controling……"
        print("\nBegin to trim adapter.")
        log(arguments, "\nBegin to trim adapter.\n")
        t = loading_begin(process)
        cmd = f"fastqc -t {arguments.t} {path}{i}_1_n.fastq {path}{i}_2_n.fastq"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\nquality control is completed. Used: {used_time} sec. Start to genome map.\n")
        log(arguments, f"quality control is completed. Used: {used_time} sec. Start to genome map.\n")
        # 进行参考基因组比对
        start_time = time.time()
        print("\nBegin to genome map.")
        log(arguments, "\nBegin to genome map.\n")
        process = "genome mapping……"
        t = loading_begin(process)
        cmd = rf'bwa mem -t {arguments.t} -M -R "@RG\tID:${sample_array[i]["group"]}\
                tLB:${sample_array[i]["group"]}\tPL:ILLUMINA\tSM:${sample_array[i]["group"]}" {arguments.r} ' \
              rf'{path}{i}_1_n.fastq {path}{i}_2_n.fastq > {path}{i}.sam'
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        cmd = f"samtools view -bS {path}{i}.sam > {path}{i}.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\nGenome is mapped. Used: {used_time} sec. Start to index .bam file.")
        log(arguments, f"{i}.bam is created.\n")
        log(arguments, f"Genome is mapped. Used: {used_time} sec. Start to index .bam file.\n")
        # 进行排序
        process = 'indexing……'
        start_time = time.time()
        print("\nBegin to index .bam file.\n")
        log(arguments, "\nBegin to index .bam file.\n")
        t = loading_begin(process)
        cmd = f"samtools sort {path}{i}.bam -o {path}{i}.sort.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        print("\n.bam file is sorted.")
        log(arguments, ".bam file is sorted.\n")
        log(arguments, f"{i}.sort.bam is created.\n")
        t = loading_begin(process)
        cmd = f"samtools index {path}{i}.sort.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        print("\nIndex is created.")
        log(arguments, "Index is created.\n")
        log(arguments, f"{i}.sort.bam.bai is created.\n")
        cmd = f"rm -rf {path}{i}.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        log(arguments, f"{i}.bam is removed.\n")
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f".bam file is indexed. Used: {used_time} sec. Start to create .bw file.")
        log(arguments, f".bam file is indexed. Used: {used_time} sec. Start to create .bw file.\n")
        # 生成.bw文件
        process = 'creating .bw files……'
        start_time = time.time()
        print("\nBegin to create .bw files.")
        log(arguments, "\nBegin to create .bw files.\n")
        t = loading_begin(process)
        cmd = f'bamCoverage -p {arguments.t} -v -b {path}{i}.sort.bam -o {path}{sample_array[i]["group"]}_{i}.sort' \
              f'.bam.bw '
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\n.bw file is created. Used: {used_time} sec.")
        log(arguments, f".bw file is created. Used: {used_time} sec.\n")
        log(arguments, f'{sample_array[i]["group"]}_{i}.sort.bam.bw is created.\n')
    elif len(get_fastq_files(path)) > 2:
        print("! The number of .fastq files are error. Begin to the next sample. !")
        log(arguments, f"! {i} analysing is failed. Begin to the next sample. !\n")
        continue
    else:
        # 去接头
        if f"{i}_n.fastq" not in os.listdir(path):
            start_time = time.time()
            process = "adapter trimming……"
            print("\nStart to trim adapter.")
            t = loading_begin(process)
            log(arguments, "\nadapter trimming\n")
            cmd = f'fastp -i {path}{i}.fastq -o {path}{i}_n.fastq'
            ps = CMDProcess(cmd, getSubInfo, arguments)
            ps.start()
            ps.join()
            log(arguments, f"{i}_n.fastq is created.\n")
            cmd = f"rm -rf {path}{i}.fastq"
            ps = CMDProcess(cmd, getSubInfo, arguments)
            ps.start()
            ps.join()
            log(arguments, f"{i}.fastq is removed.\n")
            loading_stop(t)
            stop_time = time.time()
            used_time = stop_time - start_time
            print(f"\nAll .fastq file is trimmed adapter. Used: {used_time} sec. Start to quality control.")
            log(arguments, f"All .fastq file is trimmed adapter. Used: {used_time} sec. Start to quality control.\n")
        # 进行QC检测
        start_time = time.time()
        process = "quality controling……"
        print("\nBegin to trim adapter.\n")
        log(arguments, "\nBegin to trim adapter.\n")
        t = loading_begin(process)
        cmd = f"fastqc -t {arguments.t} {path}{i}_n.fastq"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\nquality control is completed. Used: {used_time} sec. Start to genome map.")
        log(arguments, f"quality control is completed. Used: {used_time} sec. Start to genome map.\n")
        # 进行参考基因组比对
        start_time = time.time()
        print("\nBegin to genome map.")
        log(arguments, "\nBegin to genome map.\n")
        process = "genome mapping……"
        t = loading_begin(process)
        cmd = rf'bwa mem -t {arguments.t} -M -R "@RG\tID:${sample_array[i]["group"]}\
                        tLB:${sample_array[i]["group"]}\tPL:ILLUMINA\tSM:${sample_array[i]["group"]}" {arguments.r} ' \
              rf'{path}{i}_n.fastq > {path}{i}.sam'
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        cmd = f"samtools view -bS {path}{i}.sam > {path}{i}.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\nGenome is mapped. Used: {used_time} sec. Start to index .bam file.")
        log(arguments, f"{i}.bam is created.\n")
        log(arguments, f"Genome is mapped. Used: {used_time} sec. Start to index .bam file.\n")
        # 进行排序
        process = 'indexing……'
        start_time = time.time()
        print("\nBegin to index .bam file.")
        log(arguments, "\nBegin to index .bam file.\n")
        t = loading_begin(process)
        cmd = f"samtools sort {path}{i}.bam -o {path}{i}.sort.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        print("\n.bam file is sorted.")
        log(arguments, ".bam file is sorted.\n")
        log(arguments, f"{i}.sort.bam is created.\n")
        t = loading_begin(process)
        cmd = f"samtools index {path}{i}.sort.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        print("\nIndex is created.")
        log(arguments, "Index is created.\n")
        log(arguments, f"{i}.sort.bam.bai is created.\n")
        cmd = f"rm -rf {path}{i}.bam"
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        log(arguments, f"{i}.bam is removed.\n")
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f".bam file is indexed. Used: {used_time} sec. Start to create .bw file.")
        log(arguments, f".bam file is indexed. Used: {used_time} sec. Start to create .bw file.\n")
        # 生成.bw文件
        process = 'creating .bw files……'
        start_time = time.time()
        print("\nBegin to create .bw files.")
        log(arguments, "\nBegin to create .bw files.\n")
        t = loading_begin(process)
        cmd = f'bamCoverage -p {arguments.t} -v -b {path}{i}.sort.bam -o {path}{sample_array[i]["group"]}_{i}.sort' \
              f'.bam.bw '
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"\n.bw file is created. Used: {used_time} sec.")
        log(arguments, f".bw file is created. Used: {used_time} sec.\n")
        log(arguments, f'{sample_array[i]["group"]}_{i}.sort.bam.bw is created.\n')
print("--------------------------------------------------\n")
print("all analysing are completed.")
log(arguments, "\n--------------------------------------------------\n")
log(arguments, "all analysing are completed.\n")
print('Begin to call peak.')
log(arguments, "Begin to call peak.")
# 获得实验组信息
peak_type = []
rep_max = df["rep"].max()
for i in df["treatment"]:
    if i not in peak_type and i != 'input':
        peak_type.append(i)
for i in peak_type:
    for n in range(rep_max + 1):
        start_time = time.time()
        print(f"\nBegin to analyse {i}_{n}_vs_input_{n} group.")
        test = df[(df['rep'] == n) & (df['treatment'] == i)]['sample_name'].values[0]
        ctrl = df[(df['rep'] == n) & (df['treatment'] == 'input')]['sample_name'].values[0]
        print(f"Test group name is {test}. Ctrl group name is {ctrl}.")
        log(arguments, f'\nBegin to analyse {i}_{n}_vs_input_{n} group.\n')
        log(arguments, f"Test group name is {test}. Ctrl group name is {ctrl}.\n")
        process = "Calling peak……"
        name = f"{i}_vs_input"
        cmd = f'macs2 callpeak -t ./{test}/{test}.sort.bam -c ./{ctrl}/{ctrl}.sort.bam -f BAM -g hs --outdir ' \
              f'./result/{arguments.n}/{name}/{i}_{n}_vs_input_{n}/ -n {name} -B -q {arguments.q}'
        t = loading_begin(process)
        ps = CMDProcess(cmd, getSubInfo, arguments)
        ps.start()
        ps.join()
        loading_stop(t)
        stop_time = time.time()
        used_time = stop_time - start_time
        print(f"{name}_{n} process is complete! Begin to analyse the next process.")
        print(f'Relative files are in ./result/{arguments.n}/{name}/{i}_{n}_vs_input_{n}/. Used: {used_time} sec.')
        log(arguments, f"{name}_{n} process is complete! Begin to analyse the next process.\n")
        log(arguments, f'Relative files are in ./result/{arguments.n}/{name}/{i}_{n}_vs_input_{n}/. Used: {used_time} sec.\n')
print("--------------------------------------------------\n")
print("all calling peak processes are completed.")
log(arguments, "\n--------------------------------------------------\n")
log(arguments, "all calling peak processes are completed.\n")
all_stop_time = time.time()
all_used_time = all_stop_time - all_start_time
print(f'All missions are completed! Used: {all_used_time} sec. Welcome back!')
log(arguments, f'All missions are completed! Used: {all_used_time} sec. Welcome back!')