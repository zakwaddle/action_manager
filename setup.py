from setuptools import setup, find_packages

setup(
    name='action_manager',
    version='0.0.4',
    url='https://github.com/zakwaddle/action_manager',
    packages=find_packages(where="."),
    package_dir={"": "."},
    description="a contained action system",
    author='Zak',
    author_email='zakwaddle@gmail.com',
    install_requires=[],
    python_requires=">=3.7",
)
