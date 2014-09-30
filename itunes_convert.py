#! /usr/env python
# Author:         Aaron Levie (levies@gmail.com)
# Version:        2013.05.29.1
# Purpose:        Converts iTunes libraries (m4a or mp3) into mp3s at the
#                 bitrate specified and puts them in a new folder on the
#                 desktop. Original files are not affected.
# Tested:         Mac OSX (10.8) and Linux (Ubuntu 12.04)
# Requirements:   ffmpeg (http://ffmpeg.org)
#                 libmp3lame codec
# Execution:      Run with -h for help (Run as the user with the iTunes library)

import os
import Queue
import subprocess
import threading
import time
from optparse import OptionParser


def get_options(): # parses options and arguments from the command line
  parser = OptionParser()
  parser.add_option("-b", "--bitrate", dest="bitrate", default="160", help="Destination bitrate (integer likely in range 64 - 320)")
  parser.add_option("-t", "--threads", dest="threadcount", default="10", help="Threads to use (Default 10)")
  parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False, help="Quiet mode")
  options, args = parser.parse_args()
  options.bitrate = int(options.bitrate)
  options.threadcount = int(options.threadcount)
  return options

def preexec(): # prevents signals sent to main app from forwarding to subprocess
  os.setpgrp()

def makemp3(file_src, file_dst, bitrate): # performs the actual encoding
  newpath = os.path.split(file_dst)[0]
  if not os.path.isdir(newpath):
    try:
      os.makedirs(newpath)
    except:
      return False
  args = ['ffmpeg', '-i', file_src, '-acodec', 'libmp3lame', '-ab', '%sk' % bitrate, '-map_metadata', '0', file_dst]
  returncode = subprocess.call(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=preexec)
  if returncode == 0:
    return True
  else:
    try:
      os.remove(file_dst)
    except:
      pass
    return False


class ConvertThread(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.daemon = False

  def run(self):
    global WORKERS
    while KEEPALIVE == True:
      try:
        file_src, file_dst = QUEUE.get(False)
      except:
        break
      else:
        if makemp3(file_src, file_dst, OPTS.bitrate) == True:
          puke('MP3 CONVERTED: %s' % os.path.split(file_dst)[1])
        else:
          puke('MP3 CONVERSION FAILED: %s' % os.path.split(file_dst)[1])
    WORKERS -= 1

def puke(*text):
  if len(text) == 1:
    print(text[0])
  else:
    text = ' '.join(map(str,text))
    print(text)

def main():
  global QUEUE, OPTS, WORKERS, KEEPALIVE
  KEEPALIVE = True
  OPTS = get_options() # get command line options
  home_dir = os.path.expanduser('~') #expand ~ to home directory abs path
  dir_src = os.path.join(home_dir, 'Music/iTunes/iTunes Media/Music')
  dir_dst = os.path.join(home_dir, 'Desktop/music_mp3_%s/' % OPTS.bitrate)
  if not os.path.isdir(dir_src):
    print 'Source directory, %s, not found' % dir_src
    exit()
  # find music files and add them to the queue
  QUEUE = Queue.Queue() # initialize the queue
  for dirname, dirs, files in os.walk(dir_src):
    relative = os.path.relpath(dirname,dir_src)
    for filename in files:
      if filename[-3:] in ['m4a','mp3','MP3']:
        fullpath_src = os.path.join(dirname,filename)
        fullpath_dst = os.path.join(dir_dst,relative,filename[:-4]+'.mp3')
        if not os.path.isfile(fullpath_dst):
          QUEUE.put([fullpath_src,fullpath_dst])
  print 'New files to convert: %s' % QUEUE.qsize()
  # don't start more workers than objects in queue
  if QUEUE.qsize() < OPTS.threadcount:
    WORKERS = QUEUE.qsize()
  else:
    WORKERS = OPTS.threadcount
  # start worker threads
  for i in range(WORKERS):
    ConvertThread().start()
  # wait for thread completion or keyboard interrupt
  while WORKERS > 0:
    try:
      time.sleep(.5)
    except KeyboardInterrupt:
      KEEPALIVE = False
      puke("\nKILLING ALL THREADS")

if __name__ == "__main__":
    main()

