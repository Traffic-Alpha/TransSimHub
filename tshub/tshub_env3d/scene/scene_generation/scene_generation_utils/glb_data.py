'''
@Author: WANG Maonan
@Date: 2024-07-13 07:28:05
@Description: GLB Class
@LastEditTime: 2024-07-13 07:28:05
'''
from pathlib import Path
from typing import Union

class GLBData:
    """Convenience class for writing GLB files.
    """
    def __init__(self, bytes_) -> None:
        self._bytes = bytes_

    def write_glb(self, output_path: Union[str, Path]) -> None:
        """Generate a geometry file."""
        with open(output_path, "wb") as f:
            f.write(self._bytes)