from logging import Logger
import os
from typing import Tuple

import numpy as np

from .run_finetuning import run_finetuning
from chemprop.args import TrainArgs
from chemprop.data.utils import get_task_names
from chemprop.utils import makedirs, save_results


def finetune_cross_validate(args: TrainArgs, logger: Logger = None) -> Tuple[float, float]:
    """k-fold cross validation"""
    info = logger.info if logger is not None else print

    if args.seeds and (args.num_folds != len(args.seeds)):
        raise ValueError("Num seeds doesn't match num folds")
    # Initialize relevant variables
    init_seed = args.seed
    save_dir = args.save_dir
    task_names = args.target_columns or get_task_names(args.data_path)

    # Run training on different random seeds for each fold
    all_scores = []
    best_epochs = []
    for fold_num in range(args.num_folds):
        info(f'Fold {fold_num}')
        if args.seeds:
            args.seed = args.seeds[fold_num]
        else:
            args.seed = init_seed + fold_num
        args.save_dir = os.path.join(save_dir, f'fold_{fold_num}')
        makedirs(args.save_dir)
        model_scores, best_epoch = run_finetuning(args, logger) # best VALIDATION scores
        all_scores.append(model_scores)
        best_epochs.append(best_epoch)
    all_scores = np.array(all_scores)

    # Report results
    info(f'{args.num_folds}-fold cross validation')

    # Report scores for each fold
    for fold_num, scores in enumerate(all_scores):
        info(f'Seed {init_seed + fold_num} ==> test {args.metric} = {np.nanmean(scores):.6f}')

        if args.show_individual_scores:
            for task_name, score in zip(task_names, scores):
                info(f'Seed {init_seed + fold_num} ==> test {task_name} {args.metric} = {score:.6f}')

    # Report scores across models
    avg_scores = np.nanmean(all_scores, axis=1)  # average score for each model across tasks
    mean_score, std_score = np.nanmean(avg_scores), np.nanstd(avg_scores)
    info(f'Overall test {args.metric} = {mean_score:.6f} +/- {std_score:.6f}')

    if args.show_individual_scores:
        for task_num, task_name in enumerate(task_names):
            info(f'Overall test {task_name} {args.metric} = '
                 f'{np.nanmean(all_scores[:, task_num]):.6f} +/- {np.nanstd(all_scores[:, task_num]):.6f}')

    save_results(all_scores, best_epochs, task_names, args)
    
    return mean_score, std_score