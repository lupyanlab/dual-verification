#!/usr/bin/env python
import argparse
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
    @property
    def data_file(self):
        data_file_fmt = '{subj_id}.csv'
        return unipath.Path('data', data_file_fmt.format(**self))

class Trials(UserList):
    _columns = [
        # Subject columns
        'subj_id',
        'date',

        # Stimuli columns
        'question_id',
        'question',
        'cue',
        'mask_type',
        'response_type',
        'pic',

        # Response columns
        'response',
        'rt',
        'is_correct',
    ]
    Trial = namedtuple('Trial', _columns)

    @classmethod
    def make(cls, **kwargs):
        # make trials here
        trials = []
        return cls(trials)

    def to_file(self, trials_csv):
        # write trials here

class Experiment(object):
    def __init__(self, exp_yaml):
        with open(exp_yaml, 'r') as f:
            exp_info = yaml.load(f)

        self.win = visual.Window(fullscr=True, units='pix')

        text_kwargs = dict(height=20, font='Consolas')
        self.fix = visual.TextStim(self.win, text='+', **text_kwargs)
        self.prompt = visual.TextStim(self.win, text='?', **text_kwargs)

        stim_dir = Path('stimuli')
        self.questions = load_sounds(Path(stim_dir, 'questions'), '*.wav')
        self.cues = load_sounds(Path(stim_dir, 'cues'), '*.wav')

        mask_dir = unipath.Path(stim_dir, 'dynamic_mask')
        self.mask = DynamicMask(mask_dir, 'colored', win=self.win,
                                pos=[0,100], size=[200,200])

        feedback_dir = unipath.Path(stim_dir, 'feedback')
        self.feedback[0] = sound.Sound(unipath.Path(feedback_dir, 'buzz.wav'))
        self.feedback[1] = sound.Sound(unipath.Path(feedback_dir, 'bleep.wav'))

    def run_trial(self, trial):
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

    def show_instructions(self):
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

def run_experiment():

    # Given a participant, determine if the data file exists
    check_exists = lambda subj_info: Participant(**subj_info).data_file.exists()

    participant = Participant(**get_subj_info('gui_info.yaml', check_exists))
    trials = Trials.make(**participant)
    experiment = Experiment('exp_info.yaml')

    with open(participant.data_file, 'w') as data_file:
        data_file.write(trials.columns)
        data_file.flush()

        block = 0
        for trial in trials:
            # Before starting new block, show the break screen
            if trial.block > block:
                if block == 0:
                    # Just finished the practice trials
                    experiment.show_end_of_practice_screen()
                else:
                    experiment.show_break_screen()
                block = trial.block
            trial_data = experiment.run_trial(trial)
            trial_str = ','.join(map(str, trial_data.values())) + '\n'
            data_file.write(trial_str)
            data_file.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', '-t', action='store_true', default=False)
    parser.add_argument('--instructions', '-i', action='store_true',
                        default=False)

    args = parser.parse_args()

    if args.trials:
        trials = Trials.make()
        trials.to_file('sample_trials.csv')
    elif args.instructions:
        experiment = Experiment('exp_info.yaml')
        experiment.show_instructions()
    else:
        run_experiment()
