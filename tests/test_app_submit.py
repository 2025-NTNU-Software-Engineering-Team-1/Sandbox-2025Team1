import importlib
import io
import zipfile

from dispatcher import dispatcher as dispatcher_module
from dispatcher.exception import DuplicatedSubmissionIdError


def _load_sandbox_app(monkeypatch):
    monkeypatch.setattr(dispatcher_module.Dispatcher, "start",
                        lambda self: None)
    import app as sandbox_app
    return importlib.reload(sandbox_app)


def test_sandbox_duplicate_id_returns_409(monkeypatch):
    sandbox_app = _load_sandbox_app(monkeypatch)

    monkeypatch.setattr(sandbox_app, "ensure_testdata",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(sandbox_app, "get_problem_meta",
                        lambda *args, **kwargs: object())
    monkeypatch.setattr(sandbox_app.DISPATCHER, "prepare_submission_dir",
                        lambda *args, **kwargs: None)

    def raise_dup(*args, **kwargs):
        raise DuplicatedSubmissionIdError("duplicated submission")

    monkeypatch.setattr(sandbox_app.DISPATCHER, "handle", raise_dup)

    client = sandbox_app.app.test_client()
    code_buffer = io.BytesIO()
    with zipfile.ZipFile(code_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('main.py', 'print("ok")')
    code_buffer.seek(0)

    rv = client.post('/submit/dup-id',
                     data={
                         'token': sandbox_app.SANDBOX_TOKEN,
                         'problem_id': 1,
                         'language': 0,
                         'src': (code_buffer, 'src.zip'),
                     },
                     content_type='multipart/form-data')

    assert rv.status_code == 409
    payload = rv.get_json()
    assert payload['status'] == 'err'
    assert payload['message']
