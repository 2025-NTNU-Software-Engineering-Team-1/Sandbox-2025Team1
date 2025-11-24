from dispatcher.dispatcher import Dispatcher
from dispatcher.exception import *
from tests.submission_generator import SubmissionGenerator
import dispatcher.pipeline


def test_create_dispatcher():
    docker_dispatcher = Dispatcher()
    assert docker_dispatcher is not None


def test_start_dispatcher(docker_dispatcher: Dispatcher):
    docker_dispatcher.start()


def test_normal_submission(
    docker_dispatcher: Dispatcher,
    submission_generator,
    monkeypatch,
):
    monkeypatch.setattr(dispatcher.pipeline, "fetch_problem_rules",
                        lambda *args, **kwargs: None)

    docker_dispatcher.start()
    _ids = []
    for _id, prob in submission_generator.submission_ids.items():
        if prob == "normal-submission":
            _ids.append((_id, prob))

    assert len(_ids) != 0

    for _id, prob in _ids:
        docker_dispatcher.handle(_id, 1)


def test_duplicated_submission(
    docker_dispatcher: Dispatcher,
    submission_generator,
    monkeypatch,
):
    monkeypatch.setattr(dispatcher.pipeline, "fetch_problem_rules",
                        lambda *args, **kwargs: None)
    import random

    docker_dispatcher.start()

    _id, prob = random.choice(list(
        submission_generator.submission_ids.items()))

    assert _id is not None
    assert prob is not None

    docker_dispatcher.handle(_id, 1)

    try:
        docker_dispatcher.handle(_id, 1)
    except DuplicatedSubmissionIdError:
        return
    assert False
