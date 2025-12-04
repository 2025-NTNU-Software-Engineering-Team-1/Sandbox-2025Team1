import pytest
import pathlib
import os
from dispatcher.dispatcher import Dispatcher
from runner.submission import SubmissionRunner
from tests.submission_generator import SubmissionGenerator

TEST_CONFIG_PATH = '.config/dispatcher.test.json'


@pytest.fixture
def docker_dispatcher(tmp_path):
    # create a dispatcer in test config
    d = Dispatcher(TEST_CONFIG_PATH)
    d.SUBMISSION_DIR = tmp_path / d.SUBMISSION_DIR
    d.testing = True
    yield d
    # ensure we stop the dispatcher after every function call
    d.stop()


@pytest.fixture
def submission_generator(tmp_path):
    generator = SubmissionGenerator(submission_path=tmp_path / 'submissions')
    generator.gen_all()

    yield generator

    generator.clear()


@pytest.fixture
def TestSubmissionRunner(tmp_path):

    os.environ["SUBMISSION_CONFIG"] = str(
        pathlib.Path(__file__).resolve().parents[1] / ".config" /
        "submission.json")

    class TestSubmissionRunner(SubmissionRunner):

        def __init__(
            self,
            submission_id,
            time_limit,
            mem_limit,
            testdata_input_path,
            testdata_output_path,
            special_judge=False,
            lang=None,
        ):
            base_workdir = tmp_path / "submissions"
            super().__init__(
                submission_id,
                time_limit,
                mem_limit,
                testdata_input_path,
                testdata_output_path,
                special_judge=special_judge,
                lang=lang,
                common_dir=str(base_workdir / submission_id / "src" /
                               "common"),
                case_dir=str(base_workdir / submission_id / "src" / "common"),
            )
            self.working_dir = str(base_workdir)

    return TestSubmissionRunner
