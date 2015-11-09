#!/usr/bin/env python
import argparse
import os
import yaml
from UserDict import UserDict
from UserList import UserList
import socket
import webbrowser

import pandas as pd

# must be done *before* loading psychopy.sound
from labtools import pyo_sound
pyo_sound.init_pyo()

from unipath import Path
from psychopy import visual, core, event, sound

from labtools.psychopy_helper import *
from labtools.dynamic_mask import DynamicMask
from labtools.trials_functions import *

class Participant(UserDict):
    """ Store participant data and provide helper functions.

    >>> participant = Participant(subj_id=100, seed=539)

    >>> participants.data_file
    # data/100.csv

    >>> participant.write_header(['subj_id', 'seed', 'trial', 'is_correct'])
    # writes "subj_id,seed,trial,is_correct\n" to the data file
    # and saves input as the order of columns in the output

    >>> participant.write_trial({'trial': 1, 'is_correct': 1})
    # writes "100,539,1,1\n" to the data file
    """
    DATA_DIR = 'data'
    DATA_DELIMITER = ','

    def __init__(self, **kwargs):
        """ Standard dict constructor.

        Saves _order if provided. Raises an AssertionError if _order
        isn't exhaustive of kwargs.
        """
        self._data_file = None
        self._order = kwargs.pop('_order', kwargs.keys())
        assert len(self._order) == len(kwargs) & \
               all([kwg in self._order for kwg in kwargs]), \
               "_order doesn't match kwargs.keys()"
        return super(Participant, self).__init__(**kwargs)

    def keys(self):
        return self._order

    @property
    def data_file(self):
        if not self._data_file:
            data_file_name = '{subj_id}.csv'.format(**self)
            self._data_file = Path(self.DATA_DIR, data_file_name)
        return self._data_file

    def write_header(self, trial_col_names):
        """ Writes the names of the columns and saves the order. """
        self._col_names = self._order + trial_col_names
        self._write_line(self.DATA_DELIMITER.join(self._col_names))

    def write_trial(self, trial):
        assert self._col_names, 'write header first to save column order'
        trial_data = dict(self)
        trial_data.update(trial)
        row_data = [str(trial_data[key]) for key in self._col_names]
        self._write_line(self.DATA_DELIMITER.join(trial_data))

    def _write_line(self, row):
        with open(self.data_file, 'r') as f:
            f.write(row + '\n')


class Trials(UserList):
    STIM_DIR = Path('stimuli')
    COLUMNS = [
        # Trial columns
        'block',
        'trial',

        # Stimuli columns
        'proposition_id',
        'question_slug',
        'cue',
        'mask_type',
        'response_type',
        'pic',
        'correct_response',

        # Response columns
        'response',
        'rt',
        'is_correct',
    ]
    DEFAULTS = dict(
        ratio_yes_correct_responses = 0.75,
        ratio_prompt_response_type = 0.75,
    )


    @classmethod
    def make(cls, **kwargs):
        """ Create a list of trials.

        Each trial is a dict with values for all keys in self.COLUMNS.
        """
        settings = dict(cls.DEFAULTS)
        settings.update(kwargs)

        seed = settings.get('seed')
        prng = pd.np.random.RandomState(seed)

        # Balance within subject variables
        trials = counterbalance({'feat_type': ['visual', 'nonvisual'],
                                 'mask_type': ['mask', 'nomask']})
        trials = expand(trials, name='correct_response', values=['yes', 'no'],
                        ratio=settings['ratio_yes_correct_responses'],
                        seed=seed)
        trials = expand(trials, name='response_type', values=['prompt', 'pic'],
                        ratio=settings['ratio_prompt_response_type'], seed=seed)

        # Extend the trials to final length
        trials = extend(trials, reps=4)

        # Read proposition info
        propositions_csv = Path(cls.STIM_DIR, 'propositions.csv')
        propositions = pd.read_csv(propositions_csv)

        # Add cue
        categories = propositions.cue.unique()
        trials['cue'] = prng.choice(categories, len(trials), replace=True)

        _propositions = propositions.copy()

        def determine_question(row):
            is_cue = (_propositions.cue == row['cue'])
            is_feat_type = (_propositions.feat_type == row['feat_type'])
            is_correct_response = (_propositions.correct_response ==
                                   row['correct_response'])

            valid_propositions = (is_cue & is_feat_type & is_correct_response)

            if valid_propositions.sum() == 0:
                trials.ix[row.name, 'cue'] = prng.choice(categories)
                return determine_question(trials.ix[row.name, ])

            options = _propositions.ix[valid_propositions, ]
            selected_ix = prng.choice(options.index)
            selected_proposition_id = options.ix[selected_ix, 'proposition_id']
            _propositions.drop(selected_ix, inplace=True)

            return selected_proposition_id

        trials['proposition_id'] = trials.apply(determine_question, axis=1)

        # Merge in question
        trials = trials.merge(propositions)

        # Add in picture
        def determine_pic(row):
            if row['response_type'] != 'pic':
                return ''
            elif row['correct_response'] == 'yes':
                return row['cue']
            else:
                distractors = list(categories)
                distractors.remove(row['cue'])
                return prng.choice(distractors)

        trials['pic'] = trials.apply(determine_pic, axis=1)

        # Add columns for response variables
        for col in ['response', 'rt', 'is_correct']:
            trials[col] = ''

        # Finishing touches
        trials = add_block(trials, 50, name='block', start=1, groupby='cue',
                           seed=seed)
        trials = smart_shuffle(trials, col='cue', block='block', seed=seed)
        trials['trial'] = range(len(trials))

        # Reorcder columns
        trials = trials[cls.COLUMNS]

        return cls(trials.to_dict('record'))

    def write_trials(self, trials_csv):
        trials = pd.DataFrame.from_records(self)
        trials = trials[self.COLUMNS]
        trials.to_csv(trials_csv, index=False)

	def iter_blocks(self, key='block'):
		""" Return trials in blocks. """
		block = self[0][key]
		trials_in_block = []
		for trial in self:
			if trial[key] == block:
				trials_in_block.append(trial)
			else:
				yield trials_in_block
				block = trial[key]
				trials_in_block = []


class Experiment(object):
    STIM_DIR = Path('stimuli')

    def __init__(self, settings_yaml):
        with open(settings_yaml, 'r') as f:
            exp_info = yaml.load(f)

        self.waits = exp_info.pop('waits')
        self.response_keys = exp_info.pop('response_keys')

        self.win = visual.Window(fullscr=True, units='pix')

        text_kwargs = dict(height=20, font='Consolas')
        self.ready = visual.TextStim(self.win, text='+', **text_kwargs)
        self.prompt = visual.TextStim(self.win, text='?', **text_kwargs)

        self.questions = load_sounds(Path(self.STIM_DIR, 'questions'))
        self.cues = load_sounds(Path(self.STIM_DIR, 'cues'))

        image_kwargs = dict(win=self.win, pos=[0,100], size=[200,200])
        self.mask = DynamicMask(Path(self.STIM_DIR, 'dynamic_mask'),
                                **image_kwargs)
        self.pics = load_images(Path(self.STIM_DIR, 'pics'), **image_kwargs)

        feedback_dir = Path(stim_dir, 'feedback')
        self.feedback[0] = sound.Sound(Path(feedback_dir, 'buzz.wav'))
        self.feedback[1] = sound.Sound(Path(feedback_dir, 'bleep.wav'))

        self.timer = core.Clock()


    def run_trial(self, trial=None):
        """ Run a trial using a dict of settings.

        If trial settings are not provided, defaults will be used.
        """
        if trial is None:
            trial = dict(
                question_slug='is-it-used-in-circuses',
                cue='elephant',
                mask_type='mask',
                response_type='prompt',
                pic='',
                correct_response='yes'
            )

        question = self.questions[trial['question_slug']]
        cue = self.cues[trial['cue']]

        question_dur = question.getDuration()
        cue_dur = question.getDuration()

        stim_during_audio = []
        if trial['mask_type'] == 'mask':
            stim_during_audio.append(self.mask)

        if trial['response_type'] == 'prompt':
            response_stim = self.prompt
        else:
            response_stim = self.pics[trial['pic']]

        # Start trial presentation
        # ------------------------
        self.timer.reset()
        self.ready.draw()
        self.win.flip()
        core.wait(self.waits['ready_duration'])

        # Play the question
        self.timer.reset()
        question.play()
        while self.timer.getTime() < question_dur:
            [stim.draw() for stim in stim_during_audio]
            self.win.flip()
            core.wait(self.waits['mask_refresh'])

        # Delay between question offset and cue onset
        self.timer.reset()
        while self.timer.getTime() < self.waits['question_offset_to_cue_onset']:
            [stim.draw() for stim in stim_during_audio]
            self.win.flip()
            core.wait(self.waits['mask_refresh'])

        # Play the cue
        self.timer.reset()
        cue.play()
        while self.timer.getTime() < cue_dur:
            [stim.draw() for stim in stim_during_audio]
            self.win.flip()
            core.wait(self.waits['mask_refresh'])

        # Cue offset to response onset
        self.win.flip()
        core.wait(self.waits['cue_offset_to_response_onset'])

        # Show the response prompt
        self.timer.reset()
        response_stim.draw()
        self.win.flip()
        response = event.waitKeys(maxWait=self.waits['max_wait'],
                                  keyList=self.response_keys.keys(),
                                  timeStamped=self.timer)
        self.win.flip()
        # ----------------------
        # End trial presentation

        try:
            key, rt = response[0]
        except TypeError:
            rt = self.waits['max_wait']
            response = 'timeout'
        else:
            response = self.response_keys[key]

        is_correct = int(response == trial['correct_response'])

        trial['response'] = response
        trial['rt'] = rt * 1000
        trial['is_correct'] = is_correct

        self.feedback[is_correct].play()
        self.core.wait(self.waits['iti'])

        return trial

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

    def show_end_of_practice_screen(self):
        pass

    def show_break_screen(self):
        pass

    def show_end_of_experiment_screen(self):
        pass

def main():
    participant_data = get_subj_info(
        'gui_info.yaml',
        # A simple function to determine if the data file exists, provided
        # subj_info data. Used to check for uniqueness in subj_ids when
        # getting info from gui.
        check_exists = lambda subj_info: Participant(**subj_info).data_file.exists()
    )

    participant = Participant(**participant_data)
    trials = Trials.make(**participant)

    # Start of experiment
    experiment = Experiment('settings.yaml')
    experiment.show_instructions()

    participant.write_header(trials.COLUMNS)

    for block in trials.iter_blocks():
        block_type = block[0]['block_type']

        for trial in block:
            trial_data = experiment.run_trial(trial)
            participant.write_trial(trial_data)

        if block_type == 'practice':
            experiment.show_end_of_practice_screen()
        else:
            experiment.show_break_screen()

    experiment.show_end_of_experiment_screen()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run', 'trials', 'instructons'],
                        default='run')

    args = parser.parse_args()

    if args.command == 'trials':
        trials = Trials.make()
        trials.write_trials('sample_trials.csv')
    elif args.command == 'instructions':
        experiment = Experiment('settings.yaml')
        experiment.show_instructions()
    else:
        main()
