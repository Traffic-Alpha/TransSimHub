.. _install:

TransSimHub Installation
============================

Install via GitHub
--------------------------

You can install `TransSimHub` by cloning the GitHub repository. Follow these steps:

1. Clone the GitHub repository:

   .. code-block:: bash

      git clone https://github.com/Traffic-Alpha/TransSimHub.git
      cd TransSimHub

2. Install using pip:

   .. code-block:: bash

      pip install -e .

After the installation is complete, you can use the following Python command to check if TransSimHub is installed and view its version:

.. code-block:: python

   import tshub
   print(tshub.__version__)


Special Versions
~~~~~~~~~~~~~~~~

If you want to enable additional features of TransSimHub and install related dependencies, you can use extra parameters. For example, adding `doc` will enable the documentation editing features of TransSimHub:

.. code-block:: bash

   # Install Sphinx and related packages
   pip install -U -e ".[doc]"

To install **all dependencies** at once, it is highly recommended to use the **all** parameter, as shown below:

.. code-block:: bash

   pip install -U -e ".[all]"

Please note that this may require additional time and resources to install and build the necessary dependencies.

By following these steps, you will successfully install TransSimHub and be ready to use it in your Python environment.

.. note::
   If you encounter any issues during installation, please refer to the project's GitHub repository for troubleshooting or seek help from the project community.

Next, let’s learn how to use TransSimHub in your projects.
