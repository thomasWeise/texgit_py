[![build script](https://github.com/thomasWeise/texgit_py/actions/workflows/build.yml/badge.svg)](https://github.com/thomasWeise/texgit_py/actions/workflows/build.yml)
[![pypi version](https://img.shields.io/pypi/v/texgit)](https://pypi.org/project/texgit)
[![pypi downloads](https://img.shields.io/pypi/dw/texgit.svg)](https://pypistats.org/packages/texgit)
[![coverage report](https://thomasweise.github.io/texgit_py/tc/badge.svg)](https://thomasweise.github.io/texgit_py/tc/index.html)


# texgit: Accessing Git Repositories from LaTeX

- [Introduction](#1-introduction)
- [Installation](#2-installation)
- [License](#3-license)
- [Contact](#4-contact)


## 1. Introduction

`texgit` is a preprocessor for accessing files from `git` repositories from LaTeX.
This Python package works in conjunction with the [`texgit` LaTeX style](http://github.com/thomasWeise/texgit_tex/).
Basically, the LaTeX package fills the `aux` file of a TeX project with repository file loading request.
This Python package here then parses the `aux` file, loads the requests, then performs the request, and adds commands with the resulting file paths and URLs to the `aux` file.
In the second pdfLaTeX compilation, these then become available.


## 2. Installation

In order to use this package and to, e.g., run the example codes, you need to first install it using [`pip`](https://pypi.org/project/pip/) or some other tool that can install packages from [PyPi](https://pypi.org).
You can install the newest version of this library from PyPi using [`pip`](https://pypi.org/project/pip/) by doing

```shell
pip install texgit
```

This will install the latest official release of our package as well as [all dependencies](https://thomasweise.github.io/texgit_py/requirements_txt.html).
If you want to install the latest source code version from GitHub (which may not yet be officially released), you can do

```shell
pip install repository+https://github.com/thomasWeise/texgit_py.git
```

If you want to install the latest source code version from GitHub (which may not yet be officially released) and you have set up a private/public key for GitHub, you can also do:

```shell
git clone ssh://git@github.com/thomasWeise/texgit_py
pip install texgit_py
```

This may sometimes work better if you are having trouble reaching GitHub via `https` or `http`.

You can also clone the repository and then run a [`make` build](https://thomasweise.github.io/texgit_py/Makefile.html), which will automatically install all dependencies, run all the tests, and then install the package on your system, too.
This will work only on Linux, though.
It also installs the [dependencies for building](https://thomasweise.github.io/texgit_py/requirements-dev_txt.html), which include, e.g., those for unit testing and static analysis.
If this build completes successful, you can be sure that [`texgit`](https://thomasweise.github.io/texgit_py) will work properly on your machine.

All dependencies for using and running `texgit` are listed at [here](https://thomasweise.github.io/texgit_py/requirements_txt.html).
The additional dependencies for a [full `make` build](https://thomasweise.github.io/texgit_py/Makefile.html), including unit tests, static analysis, and the generation of documentation are listed [here](https://thomasweise.github.io/texgit_py/requirements-dev_txt.html).


## 3. License

[`texgit`](https://thomasweise.github.io/texgit_py) is a tool for accessing files in `git` repositories from `LaTeX`.

Copyright (C) 2023-&mdash;2025 Thomas Weise (汤卫思教授)

Dr. Thomas Weise (see [Contact](#4-contact)) holds the copyright of this package.

`texgit` is provided to the public as open source software under the [GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007](https://thomasweise.github.io/texgit_py/LICENSE.html).
Terms for other licenses, e.g., for specific industrial applications, can be negotiated with Dr. Thomas Weise (who can be reached via the [contact information](#4-contact) below).

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>.

Please visit the [contributions guidelines](https://thomasweise.github.io/texgit_py/CONTRIBUTING_md.html) for `texgit` if you would like to contribute to our package.
If you have any concerns regarding security, please visit our [security policy](https://thomasweise.github.io/texgit_py/SECURITY_md.html).


## 4. Contact

If you have any questions or suggestions, please contact
Prof. Dr. Thomas Weise (汤卫思教授) of the 
Institute of Applied Optimization (应用优化研究所, IAO) of the
School of Artificial Intelligence and Big Data ([人工智能与大数据学院](http://www.hfuu.edu.cn/aibd/)) at
[Hefei University](http://www.hfuu.edu.cn/english/) ([合肥大学](http://www.hfuu.edu.cn/)) in
Hefei, Anhui, China (中国安徽省合肥市) via
email to [tweise@hfuu.edu.cn](mailto:tweise@hfuu.edu.cn) with CC to [tweise@ustc.edu.cn](mailto:tweise@ustc.edu.cn).
