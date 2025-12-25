import os
import json
import pathlib


class ProblemParser:

    def __init__(self, data_path='problem'):
        super().__init__()

        if not os.path.exists(data_path):
            raise FileNotFoundError(data_path)
        if not os.path.isdir(data_path):
            raise NotADirectoryError(f'{data_path} is not a directory')

        self.data_path = pathlib.Path(data_path)
        # Dict[problem_name, problem_data]
        self.problem = {}

    def parse(self):
        for prob in os.listdir(self.data_path):
            prob_base_dir = self.data_path / prob
            meta_path = prob_base_dir / "meta.json"
            src_dir = prob_base_dir / "src"
            testcase_dir = prob_base_dir / "testcase"
            if not meta_path.is_file() or not src_dir.is_dir(
            ) or not testcase_dir.is_dir():
                continue

            self.problem[prob] = {}
            prob_data = self.problem[prob]

            # read metadata
            with open(meta_path) as f:
                prob_data['meta'] = json.load(f)

            # parse source code
            prob_data['source'] = {}
            for src in os.listdir(src_dir):
                with open(src_dir / src) as f:
                    prob_data['source'][src] = f.read()

            # read testcase
            prob_data['testcase'] = []
            total_tasks = len(prob_data['meta']['tasks'])
            for i, task in enumerate(prob_data['meta']['tasks']):
                prob_data['testcase'].append([])
                for j in range(task['caseCount']):
                    t_in = self._read_case_file(testcase_dir, i, j, ".in",
                                                total_tasks)
                    t_out = self._read_case_file(testcase_dir, i, j, ".out",
                                                 total_tasks)
                    prob_data['testcase'][i].append({
                        'in': t_in,
                        'out': t_out,
                    })
        return self.problem

    def _read_case_file(self, testcase_dir: pathlib.Path, task_idx: int,
                        case_idx: int, suffix: str, total_tasks: int) -> str:
        candidates = [
            testcase_dir / f'{task_idx:02d}{case_idx:02d}{suffix}',
            testcase_dir / f'{task_idx}' / f'{case_idx}{suffix}',
            testcase_dir / f'{task_idx:02d}' / f'{case_idx:02d}{suffix}',
        ]
        if total_tasks == 1:
            candidates.append(testcase_dir / f'{case_idx}' /
                              f'{case_idx}{suffix}')
        for path in candidates:
            if path.is_file():
                return path.read_text()
        expected = ", ".join(str(p) for p in candidates)
        raise FileNotFoundError(
            f"missing testcase file for task={task_idx} case={case_idx}: {expected}"
        )
