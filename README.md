# Google drive backup

When I was first admitted to Virginia Tech, one of the many exciting things I learned was that they were going to give me an institution-registered google drive account, which Google gives unlimited space for instructional institutions. VT not only lets you but recommends that you backup to google drive to keep all your files on hand in case of a failure. I set out to do this immediately, and I tried out five different programs. Duplicati and one other program tried to load my entire backup into ram, gdfs would refuse to transfer at faster than 4kb/s, gsync would always re-upload files overwriting what was on the server without regard for whether it had been changed since the last backup or not, and the last one I tried had not been updated to a recent version of the drive API. I decided to write my own. To eliminate the problems that duplicati has, I realized I had to break it into chunks and upload them sequentially. However, as my tmpfs maxes out at 4gb I cannot simply generate the blocks and then upload them, I have to generate one and then upload it, delete the local copy of the uploaded version and begin generation of the next chunk. This works, but leaves downtime where either a block is being generated but not uploaded, or a block is being uploaded but not generated. To solve this, I used multithreading. 

# Planned updates

- Delta backups with -mtime
- Remembering the last time you backed up a directory and automatically generating the correct argument to -mtime
