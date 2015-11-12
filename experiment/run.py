#!/usr/bin/env python
import argparse
import copy
import yaml
from UserDict import UserDict
from UserList import UserList

import pandas as pd
from unipath import Path

from psychopy import prefs
prefs.general.audioLib = ['pyo', ]
from psychopy import visual, core, event, sound

from labtools.psychopy_helper import get_subj_info, load_sounds, load_images
from labtools.dynamic_mask import DynamicMask
from labtools.trials_functions import (counterbalance, expand, extend,
                                       add_block, smart_shuffle)


class Participant(UserDict):
    """ Store participant data and provide helper functions.

    >>> participant = Participant(subj_id=100, seed=539,
                                  _order=['subj_id', 'seed'])
    >>> participants.data_file
    # data/100.csv
    >>> participant.write_header(['trial', 'is_correct'])
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

        correct_len = len(self._order) == len(kwargs)
        kwargs_in_order = all([kwg in self._order for kwg in kwargs])
        assert correct_len & kwargs_in_order, "_order doesn't match kwargs"

        self.data = dict(**kwargs)

    def keys(self):
        return self._order

    @property
    def data_file(self):
        if not Path(self.DATA_DIR).exists():
            Path(self.DATA_DIR).mkdir()

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
        self._write_line(self.DATA_DELIMITER.join(row_data))

    def _write_line(self, row):
        with open(self.data_file, 'a') as f:
            f.write(row + '\n')


class Trials(UserList):
    STIM_DIR = Path('stimuli')
    COLUMNS = [
        # Trial columns
        'block',
        'block_type',
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
        ratio_yes_correct_responses=0.75,
        ratio_prompt_response_type=0.75,
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
                        ratio=settings['ratio_prompt_response_type'],
                        seed=seed)

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

        # Add practice trials
        num_practice = 8
        practice_ix = prng.choice(trials.index, num_practice)
        practice_trials = trials.ix[practice_ix, ]
        practice_trials['block'] = 0
        practice_trials['block_type'] = 'practice'
        trials.drop(practice_ix, inplace=True)

        # Finishing touches
        trials = add_block(trials, 50, name='block', start=1, groupby='cue',
                           seed=seed)
        trials = smart_shuffle(trials, col='cue', block='block', seed=seed)
        trials['block_type'] = 'test'

        # Merge practice trials
        trials = pd.concat([practice_trials, trials])

        # Label trial
        trials['trial'] = range(len(trials))

        # Reorcder columns
        trials = trials[cls.COLUMNS]

        return cls(trials.to_dict('record'))

    def write_trials(self, trials_csv):
        trials = pd.DataFrame.from_records(self)
        trials = trials[self.COLUMNS]
        trials.to_csv(trials_csv, index=False)

    def iter_blocks(self, key='block'):
        """ Yield blocks of trials. """
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

    def __init__(self, settings_yaml, texts_yaml):
        with open(settings_yaml, 'r') as f:
            exp_info = yaml.load(f)

        self.waits = exp_info.pop('waits')
        self.response_keys = exp_info.pop('response_keys')
        self.survey_url = exp_info.pop('survey_url')

        with open(texts_yaml, 'r') as f:
            self.texts = yaml.load(f)

        self.win = visual.Window(fullscr=True, units='pix')

        text_kwargs = dict(height=60, font='Consolas', color='black')
        self.fix = visual.TextStim(self.win, text='+', **text_kwargs)
        self.prompt = visual.TextStim(self.win, text='Yes or No?',
                                      **text_kwargs)

        self.questions = load_sounds(Path(self.STIM_DIR, 'questions'))
        self.cues = load_sounds(Path(self.STIM_DIR, 'cues'))

        size = [400, 400]
        image_kwargs = dict(win=self.win, size=size)
        self.mask = DynamicMask(Path(self.STIM_DIR, 'dynamic_mask'),
                                **image_kwargs)
        self.pics = load_images(Path(self.STIM_DIR, 'pics'), **image_kwargs)
        frame_buffer = 20
        self.frame = visual.Rect(self.win, width=size[0]+20, height=size[1]+20,
                                 lineColor='black')

        feedback_dir = Path(self.STIM_DIR, 'feedback')
        self.feedback = {}
        self.feedback[0] = sound.Sound(Path(feedback_dir, 'buzz.wav'))
        self.feedback[1] = sound.Sound(Path(feedback_dir, 'bleep.wav'))

        self.timer = core.Clock()

    def run_trial(self, trial):
        """ Run a trial using a dict of settings. """
        question = self.questions[trial['question_slug']]
        cue = self.cues[trial['cue']]

        question_dur = question.getDuration()
        cue_dur = question.getDuration()

        stim_during_audio = [self.fix, ]
        if trial['mask_type'] == 'mask':
            stim_during_audio.insert(0, self.mask)

        if trial['response_type'] == 'prompt':
            response_stim = self.prompt
        else:
            response_stim = self.pics[trial['pic']]

        self.frame.autoDraw = True

        # Start trial presentation
        # ------------------------
        self.timer.reset()
        self.fix.draw()
        self.win.flip()
        core.wait(self.waits['fix_duration'])

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
        self.frame.autoDraw = False
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

        if trial['block_type'] == 'practice':
            self.feedback[is_correct].play()

        if response == 'timeout':
            self.show_timeout_screen()

        core.wait(self.waits['iti'])

        return trial

    def show_instructions(self):
        introduction = sorted(self.texts['introduction'].items())

        text_kwargs = dict(wrapWidth=1000, color='black', font='Consolas')
        main = visual.TextStim(self.win, pos=[0, 200], **text_kwargs)
        example = visual.TextStim(self.win, pos=[0, -50], **text_kwargs)
        example.setHeight(30)

        for i, block in introduction:
            # For logic continent on block kwargs:
            tag = block.pop('tag', None)
            example_txt = block.pop('example', None)
            advance_keys = [block.get('advance', 'space'), 'q']

            # Draw main
            main.setText(block['main'])
            if tag == 'title':
                main.setHeight(50)
            else:
                main.setHeight(20)
            main.draw()

            # Draw example
            if example_txt:
                example.setText(example_txt)
                example.draw()

            if tag == 'pic_apple':
                img_path = str(Path('stimuli', 'pics', 'apple.bmp'))
                apple = visual.ImageStim(self.win, img_path, pos=[0, -100])
                apple.draw()
            elif tag == 'mask':
                img_path = str(Path('stimuli', 'dynamic_mask', 'colored_1.png'))
                mask = visual.ImageStim(self.win, img_path, pos=[0, -100])
                mask.draw()

            self.win.flip()
            key = event.waitKeys(keyList=advance_keys)[0]

            if key == 'q':
                core.quit()

            if key in ['up', 'down']:
                self.feedback[1].play()

    def show_end_of_practice_screen(self):
        visual.TextStim(self.win, text=self.texts['end_of_practice'],
                        height=30, wrapWidth=600, color='black',
                        font='Consolas').draw()
        self.win.flip()
        event.waitKeys(keyList=['space', ])

    def show_timeout_screen(self):
        visual.TextStim(self.win, text=self.texts['timeout'],
                        height=30, wrapWidth=600, color='black',
                        font='Consolas').draw()
        self.win.flip()
        event.waitKeys(keyList=['space', ])

    def show_break_screen(self):
        visual.TextStim(self.win, text=self.texts['break_screen'],
                        height=30, wrapWidth=600, color='black',
                        font='Consolas').draw()
        self.win.flip()
        event.waitKeys(keyList=['space', ])

    def show_end_of_experiment_screen(self):
        visual.TextStim(self.win, text=self.texts['end_of_experiment'],
                        height=30, wrapWidth=600, color='black',
                        font='Consolas').draw()
        self.win.flip()
        event.waitKeys(keyList=['space', ])


def main():
    participant_data = get_subj_info(
        'gui.yaml',
        # check_exists is a simple function to determine if the data file
        # exists, provided subj_info data. Here it's used to check for
        # uniqueness in subj_ids when getting info from gui.
        check_exists=lambda subj_info:
            Participant(**subj_info).data_file.exists()
    )

    participant = Participant(**participant_data)
    trials = Trials.make(**participant)

    # Start of experiment
    experiment = Experiment('settings.yaml', 'texts.yaml')
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

    import webbrowser
    webbrowser.open(experiment.survey_url.format(**participant))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run', 'trials', 'instructions', 'test', 'survey'],
                        nargs='?', default='run')
    parser.add_argument('--output', '-o', help='Name of output file')

    args = parser.parse_args()

    if args.command == 'trials':
        trials = Trials.make()
        trials.write_trials(args.output or 'sample_trials.csv')
    elif args.command == 'instructions':
        experiment = Experiment('settings.yaml', 'texts.yaml')
        experiment.show_instructions()
    elif args.command == 'test':
        trial_settings = dict(
            block_type = 'practice',
            question_slug='is-it-used-in-circuses',
            cue='elephant',
            mask_type='mask',
            response_type='pic',
            pic='elephant',
            correct_response='yes'
        )

        experiment = Experiment('settings.yaml', 'texts.yaml')
        trial_data = experiment.run_trial(trial_settings)
        import pprint
        pprint.pprint(trial_data)
    elif args.command == 'survey':
        experiment = Experiment('settings.yaml', 'texts.yaml')
        import webbrowser
        webbrowser.open(experiment.survey_url.format(subj_id='TEST_SUBJ', computer='TEST_COMPUTER'))
    else:
        main()
