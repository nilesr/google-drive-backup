Depends on gsync

# Usage

The first time you run it, it needs you to sign in to google drive. Do this by following steps 1 and 2 [here](https://developers.google.com/drive/v3/web/quickstart/python), then running `python3 sample.py`

To make a backup, run it like this

`python3 backup.py {filename} [name of backup] [epoch of the last backup] [--exclude=folder_name [--exclude=folder_two_name [...]]]`

Only the filename is required to make a backup, a name just makes it easier to identify which folder you backed up on the server

It will prompt for a passcode which will be used to encrypt the files before uploading

The epoch of each backup is stored in the folder it's put in on the server, partially to allow you to grab it easily, and partially so the backups will display in chronological order in the web client

Note that excludes are relative to the filename passed as the first argument, so if the first argument is `/home/niles/`, then `--exclude=Documents/projects` would be a valid argument, however `--exclude=/home/niles/Documents/projects` would not be.

# Google drive backup

When I was first admitted to Virginia Tech, one of the many exciting things I learned was that they were going to give me an institution-registered google drive account, which Google gives unlimited space for instructional institutions. VT not only lets you but recommends that you backup to google drive to keep all your files on hand in case of a failure. I set out to do this immediately, and I tried out five different programs. Duplicati and one other program tried to load my entire backup into ram, gdfs would refuse to transfer at faster than 4kb/s, gsync would always re-upload files overwriting what was on the server without regard for whether it had been changed since the last backup or not, and the last one I tried had not been updated to a recent version of the drive API. I decided to write my own. To eliminate the problems that duplicati has, I realized I had to break it into chunks and upload them sequentially. However, as my tmpfs maxes out at 4gb I cannot simply generate the blocks and then upload them, I have to generate one and then upload it, delete the local copy of the uploaded version and begin generation of the next chunk. This works, but leaves downtime where either a block is being generated but not uploaded, or a block is being uploaded but not generated. To solve this, I used multithreading. 
There is currently no automated way to restore backed up files but it could be done in like four lines of code (or manually, it's easy)

# Planned updates

- Splitting files larger than the maximum block size using `split`
