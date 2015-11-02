#!/usr/bin/env python
import os
import yaml

import pandas as pd
import numpy as np

from resources.trials_functions import *
from resources.generator_functions import *

def load_stim_info(stim_dir):
    """ Load all the `_[stim]_info.csv` files as pd.DataFrames """
    stim_info = {}

    cue_info_pth = os.path.join(stim_dir, 'cues', '_cue_info.csv')
    stim_info['cue'] = pd.read_csv(cue_info_pth)

    questions_pth = os.path.join(stim_dir, 'questions', 'questions2.csv')
    stim_info['questions'] = pd.read_csv(questions_pth)

    return stim_info

def select_categories(stim_info, trial_params, seed):
    """ Select a random subset of all possible pics and cues """
    all_categories = stim_info['cue']['cue'].unique()
    num_categories = trial_params['num_categories']

    prng = np.random.RandomState(seed)
    selected = prng.choice(all_categories, num_categories, replace=False)

    questions = stim_info['questions'][:]
    keep_questions = [qcat in selected for qcat in questions['cue'].values]
    stim_info['questions'] = questions[keep_questions].reset_index(drop = True)

    return stim_info

def add_question_types(df):
    df['qtype'] = '*'
    df['qtype'][((df.ftype == 'visual') & \
                 (df.response == 'yes'))] = 'visual-yes'
    df['qtype'][((df.ftype == 'visual') & \
                 (df.response == 'no'))] = 'visual-no'
    df['qtype'][((df.ftype == 'nonvisual') & \
                 (df.response == 'yes'))] = 'nonvisual-yes'
    df['qtype'][((df.ftype == 'nonvisual') & \
                 (df.response == 'no'))] = 'nonvisual-no'
    return df

def balance_within_subj_vars(trial_parameters):
    """ Balance all within subject variables without any stimuli information """
    trials = pd.DataFrame({'ftype':['visual','nonvisual']})
    trials = expand(trials, name = 'cue_mask', values = ['mask','nomask'],
                    ratio = trial_parameters['ratio_masked_cue'],
                    sample = False)
    trials = expand(trials, name = 'response', values = ['yes','no'],
                    ratio = trial_parameters['ratio_yes_resp'],
                    sample = False)
    return trials

def extend_trials(trials, q_info):
    visual_yes = (trials.qtype == 'visual-yes').sum()
    all_visual_yes = (q_info.qtype == 'visual-yes').sum()
    reps = all_visual_yes / visual_yes
    trials = extend(trials, reps = reps)
    return trials

def add_questions(trials, q_info, seed):
    qtypes = ['visual-yes', 'visual-no', 'nonvisual-yes', 'nonvisual-no']

    source_map = {}
    for typ in qtypes:
        source_map[typ] = q_info[q_info.qtype == typ].reset_index(drop = True)

    trials = generate_by_group(trials, by = 'qtype', source_map = source_map,
                               seed = seed)
    return trials

def add_cue_info(trials, cue_info, seed):
    """ Add cue information for valid, invalid, and no cue trials """
    trials = generate_matches(trials, cue_info, on = 'cue',
                              cols = 'cue_file', seed = seed)
    return trials

def add_practice_block(trials, seed):
    """ For the practice trials, show one trial from each pic category """
    prng = np.random.RandomState(seed)

    def get_practice_trial_ix(chunk):
        return prng.choice(chunk.index, 1)[0]

    practice_ixs = trials.groupby('cue').apply(get_practice_trial_ix)
    practice = trials.ix[practice_ixs].reset_index(drop=True)
    practice['block_ix'] = -1

    trials = pd.concat([practice, trials], ignore_index=True)
    return trials

def shuffle_and_enumerate(trials, seed):
    """
    Shuffle the trials so that the same picture does not appear twice in a row
    and enumerate the trials so that trial_ix == 0 is the first test trial.
    """
    trials = smart_shuffle(trials, col='cue', block='block_ix', seed=seed)
    num_practice_trials = len(trials[trials['block_ix'] == -1])
    trials['trial_ix'] = np.arange(len(trials)) - num_practice_trials
    return trials

def make_trials(exp_dir, trial_params, seed):
    stim_info = load_stim_info(os.path.join(exp_dir, 'stimuli'))
    stim_info = select_categories(stim_info, trial_params, seed = seed)
    stim_info['questions'] = add_question_types(stim_info['questions'][:])

    trials = balance_within_subj_vars(trial_params)
    trials = add_question_types(trials)
    trials = extend_trials(trials, stim_info['questions'])
    trials = add_questions(trials, stim_info['questions'], seed)

    trials = add_cue_info(trials, stim_info['cue'], seed)

    trials = add_block(trials, 60, name='block_ix', start=0, groupby='cue',
                       seed=seed)
    trials = add_practice_block(trials, seed=seed)
    trials = shuffle_and_enumerate(trials, seed)

    trials = trials[['block_ix','trial_ix',
                     'cue','cue_file','cue_mask',
                     'ftype','response','qtype',
                     'qid','question']]

    return trials

def write_trials(trials_pth, exp_dir, trial_params, seed):
    trials = make_trials(exp_dir, trial_params, seed)
    trials.to_csv(trials_pth, index=False)

if __name__ == '__main__':
    exp_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(exp_dir, 'question_first.yaml')
    trial_params = yaml.load(open(version_file, 'r'))['trials']
    seed = 105

    #stim_info = load_stim_info(os.path.join(exp_dir, 'stimuli'))
    #stim_info = select_categories(stim_info, trial_params, seed = seed)
    #stim_info['questions'] = add_question_types(stim_info['questions'][:])
    #
    #trials = balance_within_subj_vars(trial_params)
    #trials = add_question_types(trials)
    #trials = extend_trials(trials, stim_info['questions'])
    #trials = add_questions(trials, stim_info['questions'], seed)
    #
    #trials = add_cue_info(trials, stim_info['cue'], seed)
    #
    #trials = add_block(trials, 60, name='block_ix', start=0, groupby='cue',
    #                   seed=seed)
    #trials = add_practice_block(trials, seed=seed)
    #trials = shuffle_and_enumerate(trials, seed)

    trials = make_trials(exp_dir, trial_params, seed)
