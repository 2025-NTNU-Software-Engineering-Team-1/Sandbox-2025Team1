import os
import logging
import queue
import secrets
from flask import Flask, request, jsonify
from dispatcher.constant import Language
from dispatcher.dispatcher import Dispatcher
from dispatcher.testdata import (
    ensure_testdata,
    get_problem_meta,
    get_problem_root,
    # Trial Mode support
    ensure_public_testdata,
    get_public_testdata_root,
    get_custom_testdata_root,
    scan_and_generate_tasks,
)
from dispatcher.trial_testdata import prepare_custom_testdata
from dispatcher.config import SANDBOX_TOKEN, SUBMISSION_DIR

logging.basicConfig(
    filename="logs/sandbox.log",
    level=logging.DEBUG,
)
app = Flask(__name__)
if __name__ != "__main__":
    # let flask app use gunicorn's logger
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logging.getLogger().setLevel(gunicorn_logger.level)

    # Allow overriding log level via environment variable
    if os.getenv("NOJ_DEBUG", "").lower() == "true":
        app.logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
logger = app.logger

# setup dispatcher
DISPATCHER_CONFIG = os.getenv(
    "DISPATCHER_CONFIG",
    ".config/dispatcher.json.example",
)
DISPATCHER = Dispatcher(DISPATCHER_CONFIG)
DISPATCHER.start()


@app.post("/submit/<submission_id>")
def submit(submission_id: str):
    token = request.values.get("token", "")
    if not secrets.compare_digest(token, SANDBOX_TOKEN):
        logger.debug(f"get invalid token: {token}")
        return "invalid token", 403

    # Get problem_id and language
    problem_id = request.form.get("problem_id", type=int)
    if problem_id is None:
        return "missing problem id", 400
    language = Language(request.form.get("language", type=int))

    # === Trial Submission Support ===
    # submission_type: "normal" (default) or "trial"
    submission_type = request.form.get("submission_type", "normal")
    is_trial = submission_type == "trial"

    # Select testdata path based on submission type
    if is_trial:
        use_default_case = request.form.get("use_default_case",
                                            "true").lower() == "true"

        if use_default_case:
            # Trial with public test cases
            # Note: Public test data should already contain both .in and .out files
            # No need to generate .out files using AC code
            try:
                ensure_public_testdata(problem_id)
                testdata_path = get_public_testdata_root(problem_id)
            except Exception as e:
                logger.error(f"Failed to fetch public testdata: {e}")
                return f"Failed to fetch public testdata: {e}", 500
        else:
            # Trial with custom test cases
            custom_testcases_path = request.form.get("custom_testcases_path")
            if not custom_testcases_path:
                return "missing custom_testcases_path for custom test cases", 400
            try:
                meta = get_problem_meta(problem_id, language)
                testdata_path = prepare_custom_testdata(
                    problem_id=problem_id,
                    submission_id=submission_id,
                    custom_testcases_path=custom_testcases_path,
                    meta=meta,
                )
            except Exception as e:
                logger.error(f"Failed to prepare custom testdata: {e}")
                return f"Failed to prepare custom testdata: {e}", 500
    else:
        # Normal submission
        ensure_testdata(problem_id)
        testdata_path = get_problem_root(problem_id)

    # Get meta and optionally override tasks for Trial
    meta = get_problem_meta(problem_id, language)
    if is_trial:
        # Dynamically generate tasks from actual test files
        trial_tasks = scan_and_generate_tasks(testdata_path)
        if trial_tasks:
            # Override meta.tasks with scanned tasks
            # Note: We need to convert to proper Task objects
            from dispatcher.meta import Task
            meta.tasks = [Task(**t) for t in trial_tasks]
            logger.debug(f"Trial tasks generated: {len(meta.tasks)} tasks")

    try:
        DISPATCHER.prepare_submission_dir(
            root_dir=SUBMISSION_DIR,
            submission_id=submission_id,
            meta=meta,
            source=request.files["src"],
            testdata=testdata_path,
        )
    except ValueError as e:
        return str(e), 400

    logger.debug(
        f"send submission {submission_id} to dispatcher (trial={is_trial})")
    try:
        DISPATCHER.handle(submission_id, problem_id, is_trial=is_trial)
    except ValueError as e:
        return str(e), 400
    except queue.Full:
        return (
            jsonify({
                "status": "err",
                "msg": "task queue is full now.\n"
                "please wait a moment and re-send the submission.",
                "data": None,
            }),
            500,
        )
    return jsonify({
        "status": "ok",
        "msg": "ok",
        "data": "ok",
    })


@app.get("/status")
def status():
    ret = {
        "load": DISPATCHER.queue.qsize() / DISPATCHER.MAX_TASK_COUNT,
    }
    # if token is provided
    if secrets.compare_digest(SANDBOX_TOKEN, request.args.get("token", "")):
        ret.update({
            "queueSize": DISPATCHER.queue.qsize(),
            "maxTaskCount": DISPATCHER.MAX_TASK_COUNT,
            "containerCount": DISPATCHER.container_count,
            "maxContainerCount": DISPATCHER.MAX_TASK_COUNT,
            "submissions": [*DISPATCHER.result.keys()],
            "running": DISPATCHER.do_run,
        })
    return jsonify(ret), 200


# for local debug
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)
