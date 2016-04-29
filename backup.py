#!/usr/bin/env python3
import subprocess, os, glob, sys, getpass, queue, threading
passphrase = getpass.getpass("Passphrase: ")
passphrase2 = getpass.getpass("Confirm passphrase: ")
assert(passphrase == passphrase2)
max_block_size = 1024*1024*256 # 256mb probably
max_block_size = 1024*1024*128
base_tmp = "/tmp/"
tmp = subprocess.check_output(["mktemp", "-d",base_tmp + "backup.XXXXX"]).decode("utf-8").strip() + "/"
backup_id = subprocess.check_output(["date", "+%s"]).decode("utf-8").strip()
last_backup_time = False
if len(sys.argv) > 3:
    last_backup_time = sys.argv[3]
    temp_newer = subprocess.check_output(["mktemp", base_tmp + "backup.XXXXX"]).decode("utf-8").strip()
    print(["touch","-d","-" + str(int(backup_id) - int(last_backup_time)) + " seconds", temp_newer])
    subprocess.call(["touch","-d","-" + str(int(backup_id) - int(last_backup_time)) + " seconds", temp_newer])
    mtime_arg = ["-newer", temp_newer]
else:
    mtime_arg = []
files = subprocess.check_output(["find", sys.argv[1], "-type","f",*mtime_arg,"-print0"]).decode("utf-8").split("\0")[:-1]
blocks = []
a = queue.Queue()
b = queue.Queue()
if len(sys.argv) >= 3:
    backup_id += " " + sys.argv[2]
block_index = 0
block = []
block_size = 0
null = open(os.devnull, "w")
for file in files:
    # print("Handling file " + file)
    new_file_size = os.stat(file).st_size
    if (block_size + new_file_size < max_block_size or len(block) == 0) and file != files[-1]:
        block.append(file)
        block_size += new_file_size
    else:
        if file == files[-1]:
            blocks.append([block_index + 1, [file]])
        blocks.append([block_index, block])
        block_index += 1
        block = [file]
        block_size = new_file_size
    # print()
print(str(len(files)) + " files")
print(str(len(blocks)) + " blocks")
blocks.sort(key=lambda x: x[0]) # Totally unclear why this is needed but it is
input("Press a key to continue")

def generate(block_index, block):
    print("Generating block " + str(block_index))
    os.mkdir(tmp + str(block_index))
    f = open(tmp + str(block_index) + "/" + str(block_index) + "_metadata.txt", "w")
    f.write("\n".join(block))
    f.close()
    if len(block) > 1:
        subprocess.call(["tar", "-cjvf", tmp + str(block_index) + "/" + str(block_index) + ".tar.bz2", *block], stdout=null)
    else:
        subprocess.call(["cp", block[0], tmp + "/" + str(block_index) + "/" + str(block_index)])
    for old_file in glob.glob(tmp + str(block_index) + "/*"):
        # print("Encrypting " + old_file)
        subprocess.call(["gpg2", "-c", "--passphrase",passphrase,"--batch", "--yes", old_file], stdout=null)
        os.remove(old_file) # Remove the unencrypted ones
    print("Block " + str(block_index) + " generated")
def sync(block_index):
    print("Syncing block " + str(block_index))
    subprocess.call(["gsync", "-vrt", "--progress", tmp + str(block_index) + "/", "drive://Backup/" + backup_id], stdout=sys.stdout)
    for old_file in glob.glob(tmp + str(block_index) + "/*"):
        # print("Deleting " + old_file)
        os.remove(old_file)
    print("Block " + str(block_index) + " synced")
def generate_daemon(a,b):
    idx = 0
    generate(*blocks[idx])
    a.put(idx)
    while idx != len(blocks):
        if idx != len(blocks) - 1:
            generate(*blocks[idx+1])
        assert(b.get() == idx)
        a.put(idx + 1)
        idx += 1
def sync_daemon(a,b):
    while True:
        temp = a.get()
        sync(temp)
        b.put(temp)

generate_thread = threading.Thread(target=generate_daemon, args=(a, b))
generate_thread.start()
sync_thread = threading.Thread(target=sync_daemon, args=(a, b))
sync_thread.start()
