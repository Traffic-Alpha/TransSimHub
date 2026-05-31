<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 10:57:30
 * @Description: TransSimHub README
 * @LastEditTime: 2026-06-01 00:14:00
-->
# TransSimHub

TransSimHub is a lightweight Python library for simulating and controlling transportation systems.

Get started at
[English Docs](https://transsimhub.readthedocs.io/en/latest/) |
[中文文档](https://transsimhub.readthedocs.io/en/latest/locales/zh_CN/index.html)

## Installation

TransSimHub requires Python ≥ 3.9 and [SUMO](https://www.eclipse.dev/sumo/). Install the package (editable, with all optional extras) from the project root:

```shell
pip install -e ".[all]"
```

The available extras are `rl`, `3D`, `scene`, and `doc`; use `all` to install everything, or pick the subset you need (e.g. `pip install -e ".[rl]"`).

## Test

1. **Run the Tests:** You can use Python's unittest discovery mode to automatically find and run tests. From the root directory of your project, run:

```shell
python -m unittest discover -s test
```

The `-s test` option tells unittest to start discovery in the `test` directory. Python will automatically find files named like `test*.py` and execute the test cases defined within them.

2. **Review the Test Results:**
- An `OK` output indicates all tests passed, confirming the `tshub` package is installed correctly and its version is greater than 1.
- A `FAIL` or `ERROR` output indicates some tests did not pass. Review the output details to understand what went wrong.

## Citation

If you use TransSimHub in your research, please cite our paper ([arXiv:2510.15365](https://arxiv.org/abs/2510.15365)):

```bibtex
@article{wang2025transimhub,
  title={TranSimHub: A Unified Air-Ground Simulation Platform for Multi-Modal Perception and Decision-Making},
  author={Wang, Maonan and Chen, Yirong and Cai, Yuxin and Pang, Aoyu and Xie, Yuejiao and Ma, Zian and Xu, Chengcheng and Jiang, Kemou and Wang, Ding and Roullet, Laurent and others},
  journal={arXiv preprint arXiv:2510.15365},
  year={2025}
}
```
