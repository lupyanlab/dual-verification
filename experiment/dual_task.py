#!/usr/bin/env python
import argparse
import os
import yaml
from UserDict import UserDict
from UserList import UserList
import socket
import webbrowser

import pandas as pd
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
        self._data_file = None
        return super(Participant, self).__init__(**kwargs)

    @property
    def data_file(self):
        if not self._data_file:
            data_file_name = '{subj_id}.csv'.format(**self)
            self._data_file = unipath.Path(self.DATA_DIR, data_file_name)
        return self._data_file

    def write_header(self, col_names):
        self._col_names = col_names
        self._write_line(self.DATA_DELIMITER.join(col_names))

    def write_trial(self, trial):
        assert self._col_names, 'write header first to save column order'
        row_data = dict(self).update(trial)
        trial_data = [str(row_data[key]) for key in self._col_names]
        self._write_line(self.DATA_DELIMITER.join(trial_data))

    def _write_line(self, row):
        with open(self.data_file, 'r') as f:
            f.write(row + '\n')


class Trials(UserList):
    COLUMNS = [
        # Trial columns
        'block',
        'trial',

        # Stimuli columns
        'proposition_id',
        'question',
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
    STIM_DIR = unipath.Path('stimuli')

    @classmethod
    def make(cls, **kwargs):
        """ Create a list of trials.

        Each trial is a dict with values for all keys in self.COLUMNS.
        """
        seed = kwargs.get('seed')
        prng = pd.np.random.RandomState(seed)

        # Balance within subject variables
        trials = counterbalance({'feat_type': ['visual', 'nonvisual'],
                                 'mask_type': ['mask', 'nomask']})
        trials = expand(trials, name='correct_response', values=['yes', 'no'],
                        ratio=kwargs.get('ratio_yes_correct_responses', 0.75),
                        seed=seed)
        trials = expand(trials, name='response_type', values=['prompt', 'pic'],
                        ratio=kwargs.get('ratio_prompt_response_type', 0.75),
                        seed=seed)

        # Extend the trials to final length
        trials = extend(trials, reps=4)

        # Read proposition info
        propositions_csv = unipath.Path(cls.STIM_DIR, 'propositions.csv')
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
        trials.write_trials('sample_trials.csv')
    elif args.instructions:
        experiment = Experiment('exp_info.yaml')
        experiment.show_instructions()
    else:
        run_experiment()
