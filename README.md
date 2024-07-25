<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 10:57:30
 * @Description: TransSimHub README
 * @LastEditTime: 2024-07-26 05:24:36
-->
# TransSimHub

TransSimHub is a lightweight Python library for simulating and controlling transportation systems. 

Get started at
[English Docs](https://transsimhub.readthedocs.io/en/latest/) | 
[中文文档](https://transsimhub.readthedocs.io/en/latest/locales/zh_CN/index.html)

## Test

1. **Run the Tests:** You can use Python's unittest discovery mode to automatically find and run tests. From the root directory of your project, run:

```shell
python -m unittest discover -s test
```

The `-s test` option tells unittest to start discovery in the `test` directory. Python will automatically find files named like `test*.py` and execute the test cases defined within them.

2. **Review the Test Results:**
- An `OK` output indicates all tests passed, confirming the `tshub` package is installed correctly and its version is greater than 1.
- A `FAIL` or `ERROR` output indicates some tests did not pass. Review the output details to understand what went wrong.
