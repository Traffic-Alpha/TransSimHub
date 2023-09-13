.. _install:

TransSimHub 安装
======================

通过 GitHub 安装
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

您可以通过 GitHub 源码来安装 `TransSimHub`，请按照以下步骤操作：

1. 克隆 GitHub 仓库：

   .. code-block:: bash

      git clone https://github.com/Traffic-Alpha/TransSimHub.git
      cd TransSimHub.git

2. 使用pip安装：

   .. code-block:: bash

      pip install -e .

安装完成后，您可以使用以下Python命令检查TransSimHub是否安装成功，并查看其版本号：

.. code-block:: python

   import tshub
   print(tshub.__version__)


特殊版本
~~~~~~~~~~~~

如果您希望启用TransSimHub的额外功能并安装相关依赖，请使用以下方法：

.. code-block:: bash

   # 安装Sphinx和相关包
   pip install -U -e ".[doc]"

这将安装 Sphinx 和其他相关包，以启用 TransSimHub 的额外功能。请注意，这可能需要一些额外的时间和资源来安装和构建所需的依赖项。

通过按照上述步骤，您将成功安装TransSimHub，并准备好在Python环境中使用它。

.. note::
   如果在安装过程中遇到任何问题，请参考项目的GitHub仓库进行故障排除，或向项目的社区寻求帮助。

接下来，让我们了解如何在您的项目中使用TransSimHub。
