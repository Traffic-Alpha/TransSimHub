'''
@Author: WANG Maonan
@Date: 2024-07-26 05:21:00
@Description: 检测是否安装成功
@LastEditTime: 2024-07-26 05:23:51
'''
import tshub
import unittest
from packaging import version

class TestTSHubInstallation(unittest.TestCase):
    def test_version_greater_than_1(self) -> None:
        """Test if the installed TSHub package version is greater than 1.
        """
        self.assertTrue(version.parse(tshub.__version__) >= version.parse("1.0"))

if __name__ == '__main__':
    unittest.main()
