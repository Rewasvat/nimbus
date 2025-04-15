import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='nimbus',
    version='1.0',
    py_modules=["nimbus"],
    entry_points={
        "console_scripts": [
            "nimbus = nimbus.nimbus:main"
        ]
    },
    author="Fernando Omar Aluani",
    author_email="rewasvat@gmail.com",
    description="Collection of personal scripts and other utilities organized in a simple to use CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Rewasvat/nimbus",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Exclusive Copyright",
        "Operating System :: OS Independent",
    ],
    install_requires=["libasvat", "pyinstaller"]
)
