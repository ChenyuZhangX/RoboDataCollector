from setuptools import find_packages, setup

package_name = "zed_mono_v4l2"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="robot",
    maintainer_email="robot@robot.local",
    description="ZED-M mono image publisher via V4L2 (no SDK required)",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "zed_mono_node = zed_mono_v4l2.zed_mono_node:main",
        ],
    },
)
