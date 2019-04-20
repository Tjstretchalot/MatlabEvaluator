"""Entry point in the evaluation program. Call with --help for details. Can push jobs via
the push_job.py and fetch jobs via fetch_job.py if that's easier than using persistqueue
directly"""

import argparse
import os
import time

import grader
import persistqueue
import logging
import logging.config
import json

from models import Submission

def verify_database_filepath(filepath):
    """Verifies the given path is a valid database folder"""
    ext = os.path.splitext(filepath)[1]
    if ext != '':
        raise ValueError(f'{filepath} is not a valid database file (has extension {ext} rather than a folder)')
    if os.path.exists(filepath) and not os.path.isdir(filepath):
        raise ValueError(f'{filepath} is not a valid database file (it exists but is not a directory)')

def load_logging(logging_conf):
    """Loads the logging configuration from the given json file that has the config
    """
    if not os.path.exists(logging_conf):
        raise ValueError(f'cannot load logging config from {logging_conf} (does not exist)')

    ext = os.path.splitext(logging_conf)[1]
    if ext != '.json':
        raise ValueError(f'expected logging config is json file but got {logging_conf}')

    with open(logging_conf, 'r') as infile:
        config = json.load(infile)
        logging.config.dictConfig(config)

def main():
    """Entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-database', action='store', help='The path to the folder which jobs are pushed to', default='in')
    parser.add_argument('--output-database', action='store', help='The path to the folder which evaluations are pushed to', default='out')
    parser.add_argument('--loop', action='store_true', help='Causes this to continuously read from the queue rather than terminate upon completion')
    parser.add_argument('--sleep-time', action='store', type=float, help='Only used if --loop is set: time to sleep in seconds while waiting for work', default=0.1)
    parser.add_argument('--logging-conf', action='store', help='The path to the json file from which we logging.config.dictConfig', default='conf/logging.json')
    parser.add_argument('--no-output', action='store_true', help='If set then this does not push completed jobs to the output queue')
    parser.add_argument('--skip-bad', action='store_true', help='If set then this skips bad entries instead of nacking and exitting')
    args = parser.parse_args()

    verify_database_filepath(args.input_database)
    verify_database_filepath(args.output_database)

    load_logging(args.logging_conf)
    logger = logging.getLogger(__name__)

    jobque = persistqueue.SQLiteAckQueue(args.input_database)
    if not args.no_output:
        outque = persistqueue.SQLiteAckQueue(args.output_database)
    stop = False
    while not stop:
        if jobque.size == 0:
            if not args.loop:
                return
            time.sleep(args.sleep_time)
            continue

        job = jobque.get()
        success = False
        try:
            if not isinstance(job, int):
                raise ValueError(f'expected job is int (id of submission to grade or regrade)')

            logger.info('Grading submission %s', job)
            grader.grade(Submission.get_by_id(job))
            success = True
        except:
            logger.error('failed to grade job', exc_info=1)
            if not args.skip_bad:
                raise
            else:
                logger.info('skipping failed job instead of erroring (skip_bad is True)')
        finally:
            if success or args.skip_bad:
                jobque.ack(job)
                if not args.no_output:
                    outque.put(job)
            else:
                logger.error('Failed to process job %s - nacking and terminating', job)
                jobque.nack(job)
                stop = True

if __name__ == '__main__':
    main()