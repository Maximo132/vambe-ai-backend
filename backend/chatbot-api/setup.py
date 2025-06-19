from setuptools import setup, find_packages

# Leer requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="chatbot_api",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    python_requires=">=3.9",
    include_package_data=True,
    package_data={
        "": ["*.ini", "*.py", "*.pyi", "py.typed"],
    },
)
