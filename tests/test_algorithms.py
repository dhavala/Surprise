"""
Module for testing prediction algorithms.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os

import pytest

from idly import NormalPredictor
from idly import BaselineOnly
from idly import KNNBasic
from idly import KNNWithMeans
from idly import KNNBaseline
from idly import SVD
from idly import SVDpp
from idly import NMF
from idly import SlopeOne
from idly import CoClustering
from idly import Dataset
from idly import Reader
from idly import KNNWithZScore
from idly.model_selection import PredefinedKFold
from idly.model_selection import train_test_split


def test_unknown_user_or_item():
    """Ensure that all algorithms act gracefully when asked to predict a rating
    of an unknown user, an unknown item, and when both are unknown.
    """

    reader = Reader(line_format='user item rating', sep=' ', skip_lines=3,
                    rating_scale=(1, 5))

    file_path = os.path.dirname(os.path.realpath(__file__)) + '/custom_dataset'

    data = Dataset.load_from_file(file_path=file_path, reader=reader)
    trainset = data.build_full_trainset()

    klasses = (NormalPredictor, BaselineOnly, KNNBasic, KNNWithMeans,
               KNNBaseline, SVD, SVDpp, NMF, SlopeOne, CoClustering,
               KNNWithZScore)
    for klass in klasses:
        algo = klass()
        algo.fit(trainset)
        algo.predict('user0', 'unknown_item', None)
        algo.predict('unkown_user', 'item0', None)
        algo.predict('unkown_user', 'unknown_item', None)

    # unrelated, but test the fit().test() one-liner:
    trainset, testset = train_test_split(data, test_size=2)
    for klass in klasses:
        algo = klass()
        algo.fit(trainset).test(testset)
        with pytest.warns(UserWarning):
            algo.train(trainset).test(testset)


def test_knns():
    """Ensure the k and min_k parameters are effective for knn algorithms."""

    # the test and train files are from the ml-100k dataset (10% of u1.base and
    # 10 % of u1.test)
    train_file = os.path.join(os.path.dirname(__file__), './u1_ml100k_train')
    test_file = os.path.join(os.path.dirname(__file__), './u1_ml100k_test')
    data = Dataset.load_from_folds([(train_file, test_file)],
                                   Reader('ml-100k'))
    pkf = PredefinedKFold()

    # Actually, as KNNWithMeans and KNNBaseline have back up solutions for when
    # there are not enough neighbors, we can't really test them...
    klasses = (KNNBasic, )  # KNNWithMeans, KNNBaseline)

    k, min_k = 20, 5
    for klass in klasses:
        algo = klass(k=k, min_k=min_k)
        for trainset, testset in pkf.split(data):
            algo.fit(trainset)
            predictions = algo.test(testset)
            for pred in predictions:
                if not pred.details['was_impossible']:
                    assert min_k <= pred.details['actual_k'] <= k


def test_nearest_neighbors():
    """Ensure the nearest neighbors are different when using user-user
    similarity vs item-item."""

    reader = Reader(line_format='user item rating', sep=' ', skip_lines=3,
                    rating_scale=(1, 5))

    data_file = os.path.dirname(os.path.realpath(__file__)) + '/custom_train'
    data = Dataset.load_from_file(data_file, reader)
    trainset = data.build_full_trainset()

    algo_ub = KNNBasic(sim_options={'user_based': True})
    algo_ub.fit(trainset)
    algo_ib = KNNBasic(sim_options={'user_based': False})
    algo_ib.fit(trainset)
    assert algo_ub.get_neighbors(0, k=10) != algo_ib.get_neighbors(0, k=10)
