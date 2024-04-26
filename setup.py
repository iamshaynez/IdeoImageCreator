from setuptools import find_packages, setup

setup(
    name="ideo_cc",
    version="0.1.3",
    author="xiaowenz",
    author_email="xiaowen.z@outlook.com",
    description="High quality image generation by ideogram.ai. Reverse engineered API. Rely on R2ConfigCenter.",
    url="https://github.com/iamshaynez/IdeoImageCreator",
    project_urls={
        "Bug Report": "https://github.com/iamshaynez/IdeoImageCreator/issues/new",
    },
    install_requires=[
        "curl_cffi",
        "requests",
        "fake-useragent",
        "jwt",
        "python-dotenv",
    ],
    packages=find_packages(),
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": ["ideo = ideo.ideo:main"],
    },
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
