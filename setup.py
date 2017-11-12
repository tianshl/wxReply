# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path
from wxReply import __version__

here = path.abspath(path.dirname(__file__))


def content(name):
    with open(path.join(here, name), encoding='utf-8') as f:
        desc = f.read()
    return desc


__author__ = 'tianshl'
__date__ = '2017/01/26'


setup(
    name='wxReply',                                 # 名称
    version=__version__,                            # 版本号
    description='wxReply',                          # 简单描述
    long_description=content('README.rst'),         # 详细描述
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    keywords='wechat robot weixin wxReply',         # 关键字
    author='tianshl',                               # 作者
    author_email='xiyuan91@126.com',                # 邮箱
    url='https://github.com/tianshl/wxReply',       # 包含包的项目地址
    license='MIT',                                  # 授权方式
    packages=find_packages(),                       # 包列表
    install_requires=['requests', 'itchat'],
    include_package_data=True,
    zip_safe=True,
    use_2to3=True,
)
