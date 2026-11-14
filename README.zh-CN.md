# RepoSnipy-NL

**RepoSnipy 生态中的自然语言仓库检索扩展。**

RepoSnipy-NL 是 [RepoMining/RepoSnipy](https://github.com/RepoMining/RepoSnipy)
的实验性扩展。用户可以输入自然语言功能需求，在已预计算的 RepoSim4Py
Python 仓库向量中检索相关项目。

本项目当前处于初始化阶段，只包含英文项目说明、中文说明、许可证和 Python
包目录。检索功能将在后续阶段逐步迁移。

## 计划范围

- 同时支持 `owner/repo` 与自然语言需求。
- 需求文本只编码一次。
- 复用已有 README 与 docstring 向量，不重新编码仓库语料。
- 使用通道归一化、加权余弦和缺失通道重归一化排序。
- 保留原有仓库到仓库的检索流程。

## 来源与署名

原始 WebPro 原型及开发记录位于
[dyb158507/RepoSnipy-WebPro](https://github.com/dyb158507/RepoSnipy-WebPro)。

项目建立在 RepoSnipy、RepoSim4Py 和 UniXCoder 等开源工作之上。上游模型、
数据管线和原始应用代码继续归属于各自作者。

## 许可

本项目遵循 [MIT License](LICENSE)。
