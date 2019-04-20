"""Describes the various models used in this program."""

from peewee import * # pylint: disable=unused-wildcard-import, wildcard-import
import datetime
import json

with open('conf/database.json', 'r') as infile:
    SETTINGS = json.load(infile)

DATABASE = SqliteDatabase(SETTINGS['file'])

MODELS = []
class BaseModel(Model):
    """Base model that attached the database"""
    class Meta:
        """The database attachment"""
        database = DATABASE

class MatlabFile(BaseModel):
    """Describes a matlab file

    Attributes:
        name (str): the name of the file, ending with '.m'
        contents (str): the contents of the file
    """
    name = CharField()
    contents = TextField()
MODELS.append(MatlabFile)

class Institution(BaseModel):
    """Describes an instution. People may belong to multiple institutions

    Attributes:
        name (str): a name for the institution
    """
    name = CharField()
MODELS.append(Institution)

class Person(BaseModel):
    """A person that we know about

    Attributes:
        name (str): the name of this person
    """
    name = CharField()
MODELS.append(Person)

class InstitutionPerson(BaseModel):
    """Many-many relationship between institutions and people"""
    institution = ForeignKeyField(Institution)
    person = ForeignKeyField(Person)
MODELS.append(InstitutionPerson)

class Group(BaseModel):
    """A group or class that can be given assignments. Belongs to an institution

    Attributes:
        institution_id (int): the id for the institution this group belongs to
        name (str): the name of the group, e.g. 'AMATH 352 Spring 2019'
        active (bool): true if this group is still active, false otherwise
    """
    institution = ForeignKeyField(Institution, backref='groups')
    name = CharField()
    active = BooleanField()
MODELS.append(Group)

class PersonGroup(BaseModel):
    """A many-to-many relationship between peole and groups. Has its own identifier to distinguish
    leaders (ie. professors) from non-leaders (ie. students)"""
    person = ForeignKeyField(Person)
    group = ForeignKeyField(Group)
    leader = BooleanField()
MODELS.append(PersonGroup)

class Assignment(BaseModel):
    """An assignment for a group. An assignment may have multiple parts to be evaluated.

    Attributes:
        name (str): the name of this assignment
        group (Group): the group the assignment is for
        creator (Person): the person which created this assignment
        created_at (datetime): when this assignment was created
        visible_at (datetime): when this assignment becomes visible to non-leaders
        late_at (datetime): when this assignment stops accepting 100% credit submissions
        late_penalty (float): the penalty to the assignment (i.e 0.2 for 20%) for late submissions
        closed_at (datetime): when this assignment stops accepting submissions

        assignment_verification_entry_file (MatlabFile): the file which we run to setup the workspace prior
            to verification
    """
    name = CharField()
    group = ForeignKeyField(Group, backref='assignments')
    creator = ForeignKeyField(Person, backref='authored_assignments')
    created_at = DateTimeField(default=datetime.datetime.now)
    visible_at = DateTimeField()
    late_at = DateTimeField()
    late_penalty = FloatField()
    closed_at = DateTimeField()

    assignment_verification_entry_file = ForeignKeyField(MatlabFile, null=True, default=None)
MODELS.append(Assignment)

class Problem(BaseModel):
    """A problem within an assignment. The file ought to set "points" to the number of points to award

    Attributes:
        assignment (Assignment): the assignment this problem is for
        points_out_of (float): the number of points this problem is out of. an extra credit problem is out of fewer than the maximum points
        verification_entry_file (MatlabFile): the file that is run to verify the result of this problem
    """
    assignment = ForeignKeyField(Assignment, backref='problems')
    points_out_of = FloatField()
    verification_entry_file = ForeignKeyField(MatlabFile)
MODELS.append(Problem)

class AssignmentProducedFile(BaseModel):
    """Describes a file which is outputted when running an assignment which will be copied over to the verification
    folder. All files produced which aren't in here will not be copied over. If the submission does not produce all
    the required files it will not be graded

    Attributes:
        assignment (Assignment): the assignment that produces the output file
        filename (str): the name of the file that is produced
    """
    assignment = ForeignKeyField(Assignment, backref='produced_files')
    filename = CharField()
MODELS.append(AssignmentProducedFile)

class AssignmentAuxilaryVerificationFiles(BaseModel):
    """Connects an assignment with additional matlab files required to verify it.

    Attributes:
        assignment (Assignmetn): the assignment this helps
        auxfile (MatlabFile): the file that should be attached
    """
    problem = ForeignKeyField(Assignment, backref='auxilary_verification_files')
    auxfile = ForeignKeyField(MatlabFile)
MODELS.append(AssignmentAuxilaryVerificationFiles)

class ProblemAuxilaryVerificationFiles(BaseModel):
    """Connects a problem with the additional matlab problems required to verify it. These
    will be deleted between problems to avoid name conflicts

    Attributes:
        problem (Problem): the problem which this helps verify
        auxfile (MatlabFile): the file that should be attached
    """
    problem = ForeignKeyField(Problem, backref='auxilary_verification_files')
    auxfile = ForeignKeyField(MatlabFile)
MODELS.append(ProblemAuxilaryVerificationFiles)

class Submission(BaseModel):
    """A submission for a single matlab assignment.

    Attributes:
        assignment (Assignment): the assignment this submission is for
        submittor (Person): the person who made this submission
        submitted_at (datetime): when this submission was uploaded
        graded_at (datetime): when this submission was graded or NULL if not graded yet
        report (str): the report that was generated while grading this submission

        submission_entry_file (MatlabFile): the file that is run to begin this submission
    """
    assignment = ForeignKeyField(Assignment, backref='submissions')
    submittor = ForeignKeyField(Person)
    submitted_at = DateTimeField()
    graded_at = DateTimeField(null=True, default=None)
    report = TextField(null=True, default=None)

    submission_entry_file = ForeignKeyField(MatlabFile)
MODELS.append(Submission)

class SubmissionAuxilaryFiles(BaseModel):
    """Connects a submission with auxilary files that are required to run it.

    Attributes:
        submission (Submission): the submission these files belong to
        auxfile (MatlabFile): the file that needs to be loaded
    """
    submission = ForeignKeyField(Submission, backref='auxilary_files')
    auxfile = ForeignKeyField(MatlabFile)
MODELS.append(SubmissionAuxilaryFiles)

class SubmissionProblem(BaseModel):
    """The submission for a particular problem as a part of a submission for an assignment

    Attributes:
        submission (Submission): the submission this was a part of
        problem (Problem): the problem that this submission was for
        points_out_of (float): the number of points this problem was out of at the time of grading
        points (float): the number of points received for this problem
    """
    submission = ForeignKeyField(Submission, backref='submission_problems')
    problem = ForeignKeyField(Problem)
    points_out_of = FloatField()
    points = FloatField(null=True, default=None)
MODELS.append(SubmissionProblem)

DATABASE.connect()
DATABASE.create_tables(MODELS)
