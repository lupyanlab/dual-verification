from psychopy import visual,core,event,data,info,sound
from psychopy.microphone import Speech2Text
import numpy
import sys
import pyaudio
import wave
import random

import pandas as pd

win = visual.Window([800,600], color="gray", units='pix',winType='pyglet')

status = visual.TextStim(win,text="")

playPic = visual.ImageStim(win,'pics/play.png')
stopPic = visual.ImageStim(win,'pics/stop.png')
recordPic = visual.ImageStim(win,'pics/record.png')
textToShow = visual.TextStim(win,text='',color="black",pos=(0,-200))
prompt = visual.TextStim(win,text='',color="black",pos=(0,-250))
postStartDelay=.5
postEndDelay=.25

def getFileReady(name):
	p = pyaudio.PyAudio()
	stream = p.open(format = pyaudio.paInt16,
		channels = 1,
		rate = 16000,
		input = True,
		frames_per_buffer = 1024)
	wf = wave.open('cues/'+name+'.wav', 'wb')
	wf.setnchannels(1)
	wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
	wf.setframerate(16000)
	return (p,stream,wf)


def	recordIt(whatToRecord, outfile, chunk=1024):
	textToShow.setText(whatToRecord)
	textToShow.draw()
	stopPic.draw()
	win.flip()
	soundStream = []
	recordingTimer = core.Clock()
	event.waitKeys(keyList=['space']) #wait for spacebar, then start recording but don't show the recording icon until a second in
	print 'starting to record'
	(p,stream,wf)=getFileReady(outfile)
	recordingTimer.reset()
	alreadyDrawn=responded=False
	while True: #recording

		if not alreadyDrawn and recordingTimer.getTime()>postStartDelay:
			recordPic.draw()
			textToShow.draw()
			win.flip()
			alreadyDrawn=True

		data = stream.read(chunk)
		soundStream.append(data)
		if event.getKeys(keyList=['space']):
			recordingTimer.reset()
			responded=True
		if responded and recordingTimer.getTime()>postEndDelay: #stop recording postEndDelay after spacebar pres
			stream.close()
			p.terminate()
			stopPic.draw()
			textToShow.draw()
			win.flip()
			break
	# write data to WAVE file
	data = ''.join(soundStream)
	wf.writeframes(data)
	wf.close()

	prompt.setText('Press "n" for next or "r" to re-record')
	textToShow.draw()
	prompt.draw()
	stopPic.draw()
	win.flip()

	response = event.waitKeys(keyList=['n', 'r', 'q'])[0]
	if response == 'r':
		return False
	elif response == 'n':
		return True
	else:
		raise Exception

if __name__ == '__main__':
	questions = pd.read_csv('_cue_info.csv')

	# indices = questions.index.tolist()
	# random.shuffle(indices)
	#
	# for ix in indices:
	# 	row = questions.ix[ix, ]
	# 	doneRecording = False
	# 	while not doneRecording:
	# 		doneRecording = recordIt(row['question'], row['question_slug'])
	#

	categories = questions.cue.unique()
	random.shuffle(categories)

	for cat in categories:
		doneRecording = False
		while not doneRecording:
			doneRecording = recordIt(cat, cat)
