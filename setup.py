from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="frappe_ai_architect",
    version="1.0.0",
    description="AI-Powered System Architect for Frappe Framework using Gemini API",
    author="Suvaidyam",
    author_email="suvaidyam@villintel.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
