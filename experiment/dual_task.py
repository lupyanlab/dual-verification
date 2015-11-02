#!/usr/bin/env python
import os
import yaml

from UserDict import UserDict
from UserList import UserList

import socket
import webbrowser

from psychopy import visual, core, event, sound

from labtools.psychopy_helper import *
from labtools.dynamic_mask import DynamicMask
from labtools.experiment import get_subj_info, load_sounds

from trial_list import write_trials

class Participant(UserDict):
    pass

class Trials(UserList):
    @classmethod
    def make(cls, **kwargs):
        # make trials here


class Experiment(object):
    def __init__(self, exp_dir, version_file):
        """
        Start the experiment by saving the experiment directory and loading the
        version parameters stored in .yaml format.
        """
        self.win = visual.Window(fullscr=True, units='pix')

        text_kwargs = dict(height=20, font='Consolas')
        self.fix = visual.TextStim(self.win, **text_kwargs)

        stim_dir = Path('stimuli')
        self.questions = load_sounds(Path(stim_dir, 'questions'), '*.wav')
        self.cues = load_sounds(Path(stim_dir, 'cues'), '*.wav')

        self.mask = DynamicMask()



        self.exp_dir = exp_dir

        version_file_with_path = os.path.join(exp_dir, version_file)
        self.version = yaml.load(open(version_file_with_path, 'r'))

        self.version_name = self.version['version_name']
        self.version_dir = os.path.join(self.exp_dir, self.version_name)
        if not os.path.isdir(self.version_dir):
            os.mkdir(self.version_dir)

        self._get_session_info()
        self._initialize_display()
        self._load_trials_and_stims()

    def run(self, trial):
        question = self.questions[trial['question_file']]
        cue = self.cues[trial['cue_file']]

        stim_during_audio = []
        if trial['mask_type'] == 'mask':
            stim_during_audio.extend(self.mask)

        response_type = trial['response_type']
        if response_type == 'prompt':
            pass
        elif response_type == 'picture':
            pass
        else:
            raise NotImplementedError

        # Start trial presentation
        # ------------------------
        self.fix.draw()
        self.win.flip()
        core.wait(self.waits['fixation_duration'])

        # Play the question

        # Play the cue

        # Show the response prompt





        # ----------------------
        # End trial presentation

    def _get_session_info(self):
        """
        Pop up a GUI to get session variables, such as the subject code,
        randomization seed, and experimenter initials.
        """
        subj_info = {'1':  {  'name':'subj_id',
                            'prompt':'EXP_XXX',
                           'options':'any',
                           'default': self.version_name+'101'},
                     '2':  {  'name':'seed',
                            'prompt':'Seed: ',
                           'options':'any',
                           'default': 101},
                     '3' : {  'name':'initials',
                            'prompt':'Experimenter initials',
                           'options':'any',
                           'default':''}}

        data_dir = os.path.join(self.version_dir, 'data')
        if not os.path.isdir(data_dir):
            os.mkdir(data_dir)

        received = False
        file_opened = False

        while not file_opened:
            received, self.subj_vars = enter_subj_info(self.version_name,
                                                       exp_dir=self.exp_dir,
                                                       options=subj_info)
            if self.subj_vars['subj_id'] == 'test':
                data_file = os.path.join(self.version_dir, 'sample_data.txt')
                try:
                    os.remove(data_file)
                except OSError:
                    pass
            else:
                data_file = os.path.join(data_dir,
                                         self.subj_vars['subj_id']+'.txt')

            if not received:
                popup_error(self.subj_vars)
            elif not os.path.isfile(data_file):
                file_opened = True
                self.data_file = open(data_file, 'w')
            else:
                popup_error('That subject code already exists!')

        self.subj_vars['room'] = socket.gethostname() # record experiment comp.
        self.subj_vars['seed'] = int(self.subj_vars['seed'])

        # save order of subject variables in the data file
        self.subj_vars_fields = ['subj_id', 'seed', 'initials',
                                 'date', 'exp_name', 'room']

    def _initialize_display(self):
        """
        Make the window and all static objects to be used in the experiment.
        """
        self.win = visual.Window(fullscr=True,
                                 color=[.6,.6,.6],
                                 allowGUI=False,
                                 monitor=self.subj_vars['room']+'-Monitor',
                                 units='pix',
                                 winType='pyglet')

        self.stim = {} # store static objects

        self.stim['ready'] = visual.TextStim(self.win, text='READY', height=40,
                                           pos=[0,100], color='black',
                                           font='Consolas')
        self.stim['question'] = visual.TextStim(self.win, height=40, pos=[0,100],
                                            color='black', font='Consolas',
                                            wrapWidth=int(self.win.size[0]*.8))
        self.stim['instr'] = visual.TextStim(self.win, height=30, pos=[0,350],
                                           color='black',
                                           wrapWidth=int(self.win.size[0]*.8))
        self.stim['prompt'] = visual.TextStim(self.win, text="?", height=100,
                                              pos=[0,100], color='black',
                                              font='Consolas')

        feedback_dir = os.path.join(self.exp_dir, 'stimuli', 'feedback')
        self.feedback = {}
        self.feedback[0] = sound.Sound(os.path.join(feedback_dir, 'buzz.wav'))
        self.feedback[1] = sound.Sound(os.path.join(feedback_dir, 'bleep.wav'))

        mask_params = {}
        mask_params['win'] = self.win
        mask_params['size'] = self.version['task']['mask_size']
        mask_params['pos'] = [0,100]

        mask_dir = os.path.join(self.exp_dir, 'stimuli', 'dynamic_mask')
        self.mask = DynamicMask(mask_dir, 'colored', **mask_params)

    def _load_trials_and_stims(self):
        """
        Load the trials and stimuli from external files.
        """
        show_text(self.win, 'Loading...', color='black', waitForKey=False)

        trials_dir = os.path.join(self.version_dir, 'trials')
        if not os.path.isdir(trials_dir):
            os.mkdir(trials_dir)

        if self.subj_vars['subj_id'] == 'test':
            trials_file = os.path.join(self.version_dir, 'sample_trials.csv')
            try:
                os.remove(trials_file)
            except OSError:
                pass
        else:
            trials_file = 'seed_{0}.csv'.format(self.subj_vars['seed'])
            trials_file = os.path.join(trials_dir, trials_file)

        if not os.path.isfile(trials_file):
            write_trials(trials_file, exp_dir=self.exp_dir,
                         trial_params=self.version['trials'],
                         seed=self.subj_vars['seed'])

        (self.trials, self.trials_fields) = import_trials(trials_file,
                                                          method='sequential')

        cue_dir = os.path.join(self.exp_dir, 'stimuli', 'cues')
        self.cues = load_sounds(cue_dir, 'wav')

    def _show_instructions(self):
        instructions = self.version['instructions']

        for page in instructions['pages']:
            self.stim['instr'].setText(instructions['text'][page])
            self.stim['instr'].draw()

            if page == 4:
                self.stim['question'].setText('Does it have a seat? --> pineapple')
                self.stim['question'].draw()
                advance_keys = ['n',]

            elif page == 5:
                self.stim['question'].setText('Is it green? --> apple')
                self.stim['question'].draw()
                advance_keys = ['y',]

            elif page == 6:
                self.mask.setPos([0,-100])
                self.mask.draw()
                advance_keys = ['space',]
                self.mask.setPos([0,100])

            else:
                advance_keys = ['space',]

            self.win.flip()
            event.waitKeys(keyList = advance_keys)

            if page == 4 or page == 5:
                self.feedback[1].play()

    def run(self):
        """
        Run through text screens and trials.
        """
        self._show_instructions()

        self.exp_timer = core.Clock()
        self.resp_keys = self.version['task']['resp_keys']

        # save columns for the DVs in the data file
        self.resp_fields = ['exp_timer','response','rt','is_correct']

        header_pth = os.path.join(self.version_dir, 'data', '_header.txt')
        if not os.path.isfile(header_pth):
            header = self.subj_vars_fields+self.trials_fields+self.resp_fields
            header_file = open(header_pth, 'w')
            write_list_to_file(header, header_file, close=True)

        cur_block_ix = -1
        for cur_trial in self.trials:
            if cur_trial['block_ix'] > cur_block_ix:
                self._break_for_new_block(cur_block_ix)
                cur_block_ix += 1

            self._present_trial(cur_trial)

        self.data_file.close()

    def _break_for_new_block(self, prev_block_ix):
        """ Show text screens between blocks """
        if prev_block_ix == -1:
            end_practice_txt = self.version['end_of_practice']
            for page in end_practice_txt['pages']:
                show_text(self.win, end_practice_txt['text'][page], color='black')
        else:
            break_txt = self.version['break_text']
            show_text(self.win, break_txt, color='black')

    def _give_feedback(self, is_correct):
        self.feedback[is_correct].play()

    def _present_trial(self, trial):
        """ Present a single trial """
        cue = self.cues[trial['cue_file']]
        cue_dur = cue.getDuration()

        self.stim['question'].setText(trial['question'])

        stims_during_cue = []

        if trial['cue_mask'] == 'mask':
            stims_during_cue.append(self.mask)

        ############################
        # BEGIN TRIAL PRESENTATION #
        ############################

        # show fixation cross
        self.stim['ready'].draw()
        self.win.flip()
        core.wait(self.version['task']['ready_dur'])

        # show frames
        self.win.flip()
        core.wait(self.version['task']['ready_offset_to_question_onset'])

        # show question
        self.stim['question'].draw()
        self.win.flip()
        core.wait(self.version['task']['question_dur'])

        self.win.flip()
        core.wait(self.version['task']['question_offset_to_cue_onset'])

        # play cue and show mask
        cue_timer = core.Clock()
        cue.play()
        while cue_timer.getTime() < cue_dur:
            [stim.draw() for stim in stims_during_cue]
            self.win.flip()
            core.wait(0.01)

        event.clearEvents()
        rt_timer = core.Clock()
        self.stim['prompt'].draw()
        self.win.flip()
        response = event.waitKeys(maxWait = self.version['task']['max_wait'],
                                  keyList = self.resp_keys.keys(),
                                  timeStamped = rt_timer)
        try:
            key, rt = response[0]
            response = self.resp_keys[key]
        except TypeError:
            rt = self.version['task']['max_wait']
            response = 'timeout'

        is_correct = int(response == trial['response'])

        # end trial
        self.win.flip()

        #if trial['block_ix'] == -1:
        #    self._give_feedback(is_correct)
        self._give_feedback(is_correct)

        if response == 'timeout':
            show_text(self.win, self.version['timeout_text'], color='black')
        else:
            left_over_time = self.version['task']['max_wait'] - rt
            core.wait(left_over_time + self.version['task']['iti'])

        ##########################
        # END TRIAL PRESENTATION #
        ##########################

        # record response variables
        resp = {}
        resp['exp_timer'] = self.exp_timer.getTime()
        resp['response'] = response
        resp['rt'] = rt*1000.0
        resp['is_correct'] = is_correct

        # write trial data to file
        trial_data = []
        [trial_data.append(self.subj_vars[v]) for v in self.subj_vars_fields]
        [trial_data.append(trial[v]) for v in self.trials_fields]
        [trial_data.append(resp[v]) for v in self.resp_fields]
        write_list_to_file(trial_data, self.data_file)

    def end(self):
        end_txt = self.version['end_text']
        show_text(self.win, end_txt, color='black')

        #core.quit()

        surveyURL = self.version['survey_url']
        surveyURL += '&subj_id={0}&room={1}&version={2}'.format(
            self.subj_vars['subj_id'], self.subj_vars['room'], self.version_name
        )
        webbrowser.open(surveyURL)

if __name__ == '__main__':
    participant = Participant()
    participant.update(get_subject_info('gui_info.yaml'))

    trials = Trials.make(participant)

    experiment = Experiment('exp_info.yaml')
