#!/usr/bin/env python3
# Environment Division
# max_block_size = 1024*1024*256 # 256mb probably
max_block_size = 1024*1024*128
base_tmp = "/tmp/"
# Procedure Division
import subprocess, os, glob, sys, getpass, queue, threading, copy
import traceback
def human_readable_size(size):
    units = ["Bytes", "Kilobytes", "Megabytes", "Gigabytes", "Terabytes"]
    unit = 0
    size = float(size)
    while size > 1000:
        if unit < len(units):
            size /= 1024
            unit += 1
        else: break
    return str(size)[:5] + " " + units[unit]
passphrase = getpass.getpass("Passphrase: ")
assert(passphrase == getpass.getpass("Confirm passphrase: "))
# Creates a randomly named directory in base_tmp
tmp = subprocess.check_output(["mktemp", "-d",base_tmp + "backup.XXXXX"]).decode("utf-8").strip() + "/"
# Backup ID is the current unix epoch (THIS WILL CHANGE LATER IN THE PROGRAM)
backup_id = subprocess.check_output(["date", "+%s"]).decode("utf-8").strip()
restore = False
#restore = "1469608577 all"
if not restore:
    print("Calculating files to be backed up for backup ID " + str(backup_id))
    last_backup_time = False
    if len(sys.argv) > 3: # If we were passed the epoch of the last backup
        last_backup_time = sys.argv[3]
        # I originally tried to use the -mtime argument, but it only counts back to files modified before (Arg) days, no way to specify seconds
        # Solution, make a temporary file, then set its mtime manually, then tell find to only list files newer than that file
        temp_newer = subprocess.check_output(["mktemp", base_tmp + "backup.XXXXX"]).decode("utf-8").strip()
        subprocess.call(["touch","-d","-" + str(int(backup_id) - int(last_backup_time)) + " seconds", temp_newer])
        mtime_arg = ["-newer", temp_newer]
    else:
        mtime_arg = []
    excludes = []
    excludes_dict = {}
    if len(sys.argv) > 4:
        for exclude in sys.argv[4:]:
            excludes.append(exclude.replace("--exclude=",""))
    for exclude in excludes:
        excludes_dict[exclude] = 0
# We need the [:-1] because there's a trailing null byte at the end of find's output, leading to an empty string in the list
    files = subprocess.check_output(["find", sys.argv[1], "-type","f",*mtime_arg,"-print0"]).decode("utf-8").split("\0")[:-1]
    if sys.argv[1][-1] == "/": sys.argv[1] = sys.argv[1][:-1]
    before_len_files = len(files)
    for f in copy.deepcopy(files):
        for exclude in excludes:
            if f[:len(exclude) + len(sys.argv[1]) + 2] == sys.argv[1] + "/" + exclude + "/":
                excludes_dict[exclude] += 1
                del files[files.index(f)]
else:
    backup_id = restore
blocks = []
null = open(os.devnull, "w") # We will redirect the output of tar and other command to this later
# Ordinarily we would redirect to something like subprocess.PIPE but if the pipe fills up the process will deadlock, and we're not reading from it at all, so that could be a problem
a = queue.Queue()
b = queue.Queue()
# If we were passed a backup name, use that in the backup id, otherwise use the folder
if not restore:
    if len(sys.argv) >= 3:
        backup_id += " " + sys.argv[2]
    else:
        backup_id += " " + sys.argv[1]
block_index = 0
block = []
block_size = 0
total_size = 0
if not restore:
    for file in files:
        try:
            new_file_size = os.stat(file).st_size
        except:
            if not os.path.exists(file):
                continue
            print(traceback.format_exc())
            sys.exit(1)
        total_size += new_file_size
        # If the new block size would be less than the maximum, or the block is empty, add it to the current block and continue.
        # If it's the last file in the list, jump straight to the else
        if (block_size + new_file_size < max_block_size or len(block) == 0) and file != files[-1]:
            block.append(file)
            block_size += new_file_size
        else:
            # This code will be reached if the current file plus the existing block would be too large (or it's the last file)
            # We want to complete the current block then make a new block that starts out with the current file
            if file == files[-1]: # However, if this is the last file, the loop will never be run again, and the block we start now will never be added to blocks, so we need to either add it to the current block and finish it up, or make a new block with just the last file.
                if block_size + new_file_size > max_block_size: 
                    blocks.append([block_index + 1, [file]])
                else:
                    block.append(file)
            blocks.append([block_index, block])
            block_index += 1
            block = [file]
            block_size = new_file_size
    for exclude, excluded in excludes_dict.items():
        print(exclude + ": excluded " + str(excluded) + " files")
    if len(excludes) > 0:
        print(str(-len(files) + before_len_files) + " files were excluded in total")
        print(str(len(files)) + " files to be backed up")
else:
    last_bid = int(open(".backup_restore_" + backup_id + "/last_successfully_synced_block_id").read())
    print(str(last_bid))
    for f in glob.glob(".backup_restore_" + backup_id + "/*_metadata.txt"):
        try:
            block = [int(f.split("/")[1].split("_")[0]), open(f, "r").read().split('\n')]
            if block[0] <= last_bid:
                continue
            blocks.append(block)
        except:
            continue
    blocks.sort(key = lambda x: x[0])
    print("Continuing with " + str(len(blocks)) + " to go")
print(str(len(blocks)) + " blocks")
print(human_readable_size(total_size))
blocks.sort(key=lambda x: x[0]) # The last two blocks will sometimes be out of order, this makes them sequential
input("Press enter to continue")

def generate_restorable_metadata(block_index, block):
    if not os.path.isdir(".backup_restore_" + backup_id): os.mkdir(".backup_restore_" + backup_id)
    f = open( ".backup_restore_"+backup_id+"/" + str(block_index) + "_metadata.txt", "w")
    f.write("\n".join(block))
    f.close()
def generate(block_index, block):
    print("Generating block " + str(block_index))
    # Make a temporary directory at (default) /tmp/backup.XXXXX/:block_index (the Xs are replaced with random characters)
    os.mkdir(tmp + str(block_index))
    # Put a list of what's in the tar (or the name of the file) so it can be restored later
    f = open(tmp + str(block_index) + "/" + str(block_index) + "_metadata.txt", "w")
    f.write("\n".join(block))
    f.close()
    if len(block) > 1:
        subprocess.call(["tar", "-cJvf", tmp + str(block_index) + "/" + str(block_index) + ".txz", *block], stdout=null) # The -v was for debug earlier, never bothered to remove it. It's not hurting anything
        # z -> gzip
        # j -> bzip2
        # J -> xz
    else:
        subprocess.call(["cp", *block, tmp + "/" + str(block_index) + "/" + str(block_index)]) # No point in taring if it's only one file
    # For all the files we just put in the temporary directory, encrypt them, then delete the unencrypted copies
    for old_file in glob.glob(tmp + str(block_index) + "/*"):
        subprocess.call(["gpg2", "-c", "--passphrase",passphrase,"--batch", "--yes", old_file], stdout=null)
        os.remove(old_file) # Remove the unencrypted ones
    print("Block " + str(block_index) + " generated")
def sync(block_index):
    # Just upload our temporary directory (default) /tmp/backup.XXXXX/:block_index to drive://Backup/:backup_id
    print("Syncing block " + str(block_index))
    while True:
        try:
            subprocess.check_call(["gsync", "-vrt", "--progress", tmp + str(block_index) + "/", "drive://Backup/" + backup_id], stdout=sys.stdout) # Change this to null to remove output
            break
        except:
            pass
    # Delete the files after upload
    for old_file in glob.glob(tmp + str(block_index) + "/*"):
        os.remove(old_file)
    f = open(".backup_restore_" + backup_id + "/last_successfully_synced_block_id", "w")
    f.write(str(block_index))
    f.close()
    print("Block " + str(block_index) + " synced")
def generate_daemon(a,b):
    # Relatively simple. First we generate block zero, then we tell the sync thread to upload it
    # After that we go into a while loop, generating the next block after the previous one has synced. If we have already synced all of them, tell the other thread to die, then die. This should hypothetically end the program, I think..
    for block in blocks:
        generate_restorable_metadata(*block)
    idx = 0
    generate(*blocks[idx])
    a.put(blocks[idx][0])
    while idx != len(blocks):
        if idx != len(blocks) - 1:
            generate(*blocks[idx+1])
        #assert(b.get() == blocks[idx][0]) # This will block until the sync is done
        b.get() # DEBUG
        if idx != len(blocks) - 1:
            a.put(blocks[idx+1][0])
        idx += 1
    a.put("die")
    import subprocess
    #subprocess.call(["rm", "-rf", ".backup_restore_" + backup_id])
    sys.exit(0)
def sync_daemon(a,b):
    # Sync what the cooler thread tells us to sync, then tell it when we're done
    while True:
        temp = a.get()
        if temp == "die":
            sys.exit(0)
        sync(temp)
        b.put(temp)
generate_thread = threading.Thread(target=generate_daemon, args=(a, b))
generate_thread.start()
sync_thread = threading.Thread(target=sync_daemon, args=(a, b))
sync_thread.start()
