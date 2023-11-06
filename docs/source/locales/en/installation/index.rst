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
----------------

If you want to enable additional features of TransSimHub and install the related dependencies, you can use the following method:

.. code-block:: bash

   # Install Sphinx and related packages
   pip install -U -e ".[doc]"

This will install Sphinx and other related packages to enable the additional features of TransSimHub. Please note that this may require some extra time and resources to install and build the required dependencies.

By following these steps, you will have successfully installed TransSimHub and be ready to use it in your Python environment.

.. note::
   If you encounter any issues during the installation process, refer to the project's GitHub repository for troubleshooting or seek help from the project's community.

Next, let's learn how to use TransSimHub in your project.
