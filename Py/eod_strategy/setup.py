from setuptools import setup, find_packages

setup(
    name="eod-strategy",
    version="0.1.0",
    description="End-of-Day Continuation Strategy in pure Python",
    author="Your Name",
    author_email="you@example.com",
    packages=find_packages(),
    install_requires=["pandas", "numpy", "matplotlib"],
    entry_points={
        "console_scripts": [
            "eod-strategy = eod_strategy.eod_continuation:main",
        ],
    },
)
