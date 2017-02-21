"""Various utilities.

"""

import os
import sys
import copy
import numpy as np
import logging
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from metrics import Metrics
from tqdm import tqdm

def generate_noise(opts, num=100):
    """Generate latent noise.

    """
    noise = None
    if opts['latent_space_distr'] == 'uniform':
        noise = np.random.uniform(
            -1, 1, [num, opts["latent_space_dim"]]).astype(np.float32)
    elif opts['latent_space_distr'] == 'normal':
        mean = np.zeros(opts["latent_space_dim"])
        cov = np.identity(opts["latent_space_dim"])
        noise = np.random.multivariate_normal(
            mean, cov, num).astype(np.float32)
    return noise

class ArraySaver(object):
    """A simple class helping with saving/loading numpy arrays from files.

    This class allows to save / load numpy arrays, while storing them either
    on disk or in memory.
    """

    def __init__(self, mode='ram', workdir=None):
        self._mode = mode
        self._workdir = workdir
        self._global_arrays = {}

    def save(self, name, array):
        if self._mode == 'ram':
            self._global_arrays[name] = copy.deepcopy(array)
        elif self._mode == 'disk':
            create_dir(self._workdir)
            np.save(os.path.join(self._workdir, name), array)
        else:
            assert False, 'Unknown save / load mode'

    def load(self, name):
        if self._mode == 'ram':
            return self._global_arrays[name]
        elif self._mode == 'disk':
            return np.load(os.path.join(self._workdir, name))
        else:
            assert False, 'Unknown save / load mode'

class ProgressBar(object):
    """Super-simple progress bar.

    Thanks to http://stackoverflow.com/questions/3160699/python-progress-bar
    """
    def __init__(self, verbose, iter_num):
        self._width = iter_num
        self.verbose = verbose
        if self.verbose:
            sys.stdout.write("[%s]" % (" " * self._width))
            sys.stdout.flush()
            sys.stdout.write("\b" * (self._width + 1))

    def bam(self):
        if self.verbose:
            sys.stdout.write("*")
            sys.stdout.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.verbose:
            sys.stdout.write("\n")

def TQDM(opts, myRange, *args, **kwargs):
    if opts['verbose']:
        return tqdm(myRange, *args, ncols=80, smoothing=0.,  **kwargs)
    else:
        return myRange

def create_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

def js_div_uniform(p, num_cat=1000):
    """ Computes the JS-divergence between p and the uniform distribution.

    """
    phat = np.bincount(p, minlength=num_cat)
    phat = (phat + 0.0) / np.sum(phat)
    pu = (phat * .0 + 1.) / num_cat
    pref = (phat + pu) / 2.
    JS = np.sum(np.log(pu / pref) * pu)
    JS += np.sum(np.log(pref / pu) * pref)
    JS = JS / 2.

    return JS

def debug_mixture_classifier(opts, step, probs, points, num_plot=64, real=True):
    """Small debugger for the mixture classifier's output.

    """
    num = len(points)
    if len(probs) != num:
        return
    if num < 2 * num_plot:
        return
    sorted_vals_and_ids = sorted(zip(probs, range(num)))
    if real:
        correct = sorted_vals_and_ids[-num_plot:]
        wrong = sorted_vals_and_ids[:num_plot]
    else:
        correct = sorted_vals_and_ids[:num_plot]
        wrong = sorted_vals_and_ids[-num_plot:]
    correct_ids = [_id for val, _id in correct]
    wrong_ids = [_id for val, _id in wrong]
    idstring = 'real' if real else 'fake'
    logging.debug('Correctly classified %s points probs:' %\
                  idstring)
    logging.debug([val[0] for val, _id in correct])
    logging.debug('Incorrectly classified %s points probs:' %\
                  idstring)
    logging.debug([val[0] for val, _id in wrong])
    metrics = Metrics()
    metrics.make_plots(opts, step,
                       None, points[correct_ids],
                       prefix='c_%s_correct_' % idstring)
    metrics.make_plots(opts, step,
                       None, points[wrong_ids],
                       prefix='c_%s_wrong_' % idstring)

def debug_updated_weights(opts, steps, weights, data):
    """ Various debug plots for updated weights of training points.

    """
    # assert len(data) == len(weights), 'Length mismatch'
    assert data.num_points == len(weights), 'Length mismatch'
    ws_and_ids = sorted(zip(weights,
                        range(len(weights))))
    plt.figure()
    ax1 = plt.subplot(211)
    ax1.set_title('Weights over data points')
    plt.scatter(range(len(weights)), weights, s=30)
    num_plot = 4 * 16
    if num_plot > len(weights):
        return
    ids = [_id for w, _id in ws_and_ids[:num_plot]]
    plot_points = data.data[ids]
    metrics = Metrics()
    metrics.make_plots(opts, steps,
                       None, plot_points,
                       prefix='d_least_')
    ids = [_id for w, _id in ws_and_ids[-num_plot:]]
    plot_points = data.data[ids]
    metrics = Metrics()
    metrics.make_plots(opts, steps,
                       None, plot_points,
                       prefix='d_most_')
    if data.labels is not None:
        all_labels = np.unique(data.labels)
        w_per_label = -1. * np.ones(len(all_labels))
        for _id, y in enumerate(all_labels):
            w_per_label[_id] = np.sum(
                    weights[np.where(data.labels == y)[0]])
        ax2 = plt.subplot(212)
        ax2.set_title('Weights over labels')
        plt.scatter(range(len(all_labels)), w_per_label, s=30)
        filename = 'data_w{:02d}.png'.format(steps)
        create_dir(opts['work_dir'])
        plt.savefig(os.path.join(opts["work_dir"], filename))
