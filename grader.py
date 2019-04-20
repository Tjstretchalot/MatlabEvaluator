"""This file actually performs grading for submissions"""

import matlab.engine

from models import *
import os
import tempfile
import io

import logging
import time

MAX_TIME = 30
LOG = logging.getLogger(__name__)
ENGINE = matlab.engine.start_matlab()

def _run_by_fname(fname, report):
    print(f'Running {fname}', file=report)
    engerr = io.StringIO()
    engout = io.StringIO()
    target = getattr(ENGINE, os.path.splitext(fname)[0])
    future = target(nargout=0, stdout=engout, stderr=engerr, background=True)
    starttime = time.time()
    while not future.done():
        if time.time() - starttime > MAX_TIME:
            future.cancel()
        time.sleep(0.1)
    if not future.cancelled():
        future.result()
    print('--STDOUT--', file=report)
    print(engout.getvalue(), file=report)
    print('--STDERR--', file=report)
    print(engerr.getvalue(), file=report)
    return future

class _WrappedContextManager:
    def __init__(self, ctxt_manager):
        self.ctxt_manager = ctxt_manager
        self.oldpath = None

    def __enter__(self):
        self.oldpath = ENGINE.cd('.')
        return self.ctxt_manager.__enter__()

    def __exit__(self, *args):
        ENGINE.cd(self.oldpath)
        return self.ctxt_manager.__exit__(*args)

def _wrap(ctxt_manager):
    return _WrappedContextManager(ctxt_manager)

def grade(submission: Submission) -> bool:
    """Grades the specified submission, returning True on success and False on failure"""
    assignment = submission.assignment
    oldpath = ENGINE.cd('.')

    report = io.StringIO()
    print(f'Evaluating submission id={submission.id} by {submission.submittor.name}', file=report)
    try:
        with _wrap(tempfile.TemporaryDirectory()) as submdir:
            entry_problem = submission.submission_entry_file
            with open(os.path.join(submdir, entry_problem.name), 'w') as outfile:
                outfile.write(entry_problem.contents)

            for auxfile in submission.auxilary_files.join(MatlabFile):
                with open(os.path.join(submdir, auxfile.auxfile.name), 'w') as outfile:
                    outfile.write(auxfile.auxfile.contents)

            ENGINE.cd(submdir)
            future = _run_by_fname(entry_problem.name, report)
            if future.cancelled():
                print('Operation cancelled due to timeout -> not grading', file=report)
                return True
            del future

            with _wrap(tempfile.TemporaryDirectory()) as evaldir:
                missing_prod_files = []
                for prod_file in assignment.produced_files:
                    if not os.path.exists(os.path.join(submdir, prod_file.filename)):
                        missing_prod_files.append(prod_file.filename)
                    elif not missing_prod_files:
                        os.rename(os.path.join(submdir, prod_file.filename), os.path.join(evaldir, prod_file.filename))

                if missing_prod_files:
                    print('Failed to find the following files after evaluating: ' + ', '.join(missing_prod_files), file=report)
                    return True

                assign_entry_file = assignment.assignment_verification_entry_file

                if assign_entry_file is not None:
                    with open(os.path.join(evaldir, assign_entry_file.name), 'w') as outfile:
                        outfile.write(assign_entry_file.contents)

                for verfile in assignment.auxilary_verification_files.join(MatlabFile):
                    with open(os.path.join(evaldir, verfile.auxfile.name), 'w') as outfile:
                        outfile.write(verfile.auxfile.contents)

                print("=======VERIFICATION=======", file=report)
                ENGINE.cd(evaldir)
                if assign_entry_file is not None:
                    print(f'Assignment entry file detected')
                    future = _run_by_fname(assign_entry_file.name, report)
                    if future.cancelled():
                        print('Operation cancelled due to timeout -> not grading', file=report)
                        return True
                    del future

                for problem in assignment.problems.join(MatlabFile):
                    verfiles = problem.auxilary_verification_files.join(MatlabFile)
                    for verfile in verfiles:
                        with open(os.path.join(evaldir, verfile.auxfile.name), 'w') as outfile:
                            outfile.write(verfile.auxfile.contents)

                    with open(os.path.join(evaldir, problem.verification_entry_file.name), 'w') as outfile:
                        outfile.write(problem.verification_entry_file.contents)

                    print(f'Grading problem {problem.id}', file=report)
                    future = _run_by_fname(problem.verification_entry_file.name, report)
                    if future.cancelled():
                        print('Operation cancelled due to timeout -> not grading', file=report)
                        return True
                    del future

                    points = float(ENGINE.workspace['points'])
                    print(f'Got {points}/{problem.points_out_of}', file=report)
                    subm_problem = submission.submission_problems.where(SubmissionProblem.problem == problem).first()
                    if subm_problem is None:
                        subm_problem = SubmissionProblem.create(submission=submission, problem=problem, points_out_of=problem.points_out_of, points=points)
                    else:
                        subm_problem.points = points
                        subm_problem.points_out_of = problem.points_out_of
                        subm_problem.save()

                    for verfile in verfiles:
                        os.remove(os.path.join(evaldir, verfile.auxfile.name))
                    os.remove(os.path.join(evaldir, problem.verification_entry_file.name))
                ENGINE.cd(oldpath)
        print('Grading finished successfully', file=report)
        return True
    except:
        LOG.error('Exception occurred while grading submission %s', str(submission.id), exc_info=1)
        raise
    finally:
        LOG.debug(report.getvalue())
        ENGINE.cd(oldpath)
        submission.report = report.getvalue()
        submission.graded_at = time.time()
        submission.save()
    return False
