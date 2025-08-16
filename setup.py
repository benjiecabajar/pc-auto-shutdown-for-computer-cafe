from setuptools import setup

setup(
    name='AutoShutdown',
    version='1.0',
    description='Smart Auto Shutdown Utility',
    author='BenjieCabajar',
    py_modules=['ads'],
    install_requires=[
        'customtkinter',
        'pynput',
        'sounddevice',
        'numpy',
        'pywin32',
    ],
    entry_points={
        'gui_scripts': [
            'autoshutdown = ads:main_entry',
        ],
    },
)
