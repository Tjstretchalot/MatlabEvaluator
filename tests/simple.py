"""Simple test"""

import json
import os
import datetime
import time
import logging
with open('conf/database.json', 'r') as infile:
    SETTINGS = json.load(infile)

if 'test' not in SETTINGS['file']:
    raise RuntimeError(f'cannot run test against database without test in the name')

if os.path.exists(SETTINGS['file']):
    os.remove(SETTINGS['file'])

from main import load_logging
from models import *
import grader

def main():
    """Runs the test"""

    univ_wash = Institution.create(name='University of Washington')
    sasha = Person.create(name='Aleksandr Aravkin')
    timothy = Person.create(name='Timothy Moore')

    InstitutionPerson.create(institution=univ_wash, person=sasha)
    InstitutionPerson.create(institution=univ_wash, person=timothy)

    amath352 = Group.create(institution=univ_wash, name='AMATH 352 Spring 2019', active=True)

    PersonGroup.create(person=sasha, group=amath352, leader=True)
    PersonGroup.create(person=timothy, group=amath352, leader=False)

    assignment = Assignment.create(name='HW 1', group=amath352, creator=sasha, created_at=datetime.datetime.now(),
                                   visible_at=datetime.datetime.now(), late_at=datetime.datetime.fromtimestamp(time.time() + 600),
                                   late_penalty=0.2, closed_at=datetime.datetime.fromtimestamp(time.time() + 1200))

    p1_verfile = MatlabFile.create(name='problem1.m', contents='disp(\'problem1.m\'); points = 5;')
    Problem.create(assignment=assignment, points_out_of=5, verification_entry_file=p1_verfile)

    p1_submfile = MatlabFile.create(name='problem1.m', contents='a1 = 3')
    submission = Submission.create(assignment=assignment, submittor=timothy, submitted_at=datetime.datetime.now(),
                                   submission_entry_file=p1_submfile)
    grader.grade(submission)

if __name__ == '__main__':
    load_logging('conf/logging.json')
    main()