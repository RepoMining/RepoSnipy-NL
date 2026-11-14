# RepoSnipy-NL

**RepoSnipy 生态中的自然语言仓库检索扩展。**

RepoSnipy-NL 是 [RepoMining/RepoSnipy](https://github.com/RepoMining/RepoSnipy)
的实验性扩展。用户可以输入自然语言功能需求，在已预计算的 RepoSim4Py
Python 仓库向量中检索相关项目。

Python 包当前已包含自然语言查询、通道投影、融合排序、缺失通道重归一化和
FastAPI 服务，并提供 Vue 3 检索界面和可复现的需求检索评测。

## 计划范围

- 同时支持 `owner/repo` 与自然语言需求。
- 需求文本只编码一次。
- 复用已有 README 与 docstring 向量，不重新编码仓库语料。
- 使用通道归一化、加权余弦和缺失通道重归一化排序。
- 保留原有仓库到仓库的检索流程。

## 评测

仓库内只保留一份冻结评测基线，包含 40 个功能意图、80 条中英文查询和
2,706 条查询-仓库候选判断。运行以下命令校验数据完整性并复算全部 101 个融合
权重点：

```bash
python evaluation/audit_benchmark.py
```

验证集选出 README `0.33` / docstring `0.67`。评测范围是固定候选池重排，不表示
全索引召回率。协议、指标与限制见
[evaluation/README.md](evaluation/README.md)。

## 安装、测试与 Demo

完整安装说明见 [docs/installation.md](docs/installation.md)，库和 HTTP 接口用法见
[docs/usage.md](docs/usage.md)。

以下命令不需要模型或仓库索引即可运行：

```bash
python examples/retrieval_demo.py
python -m unittest discover -s tests -v
python evaluation/audit_benchmark.py
```

Demo 使用合成向量展示投影、融合和排序流程，仅用于说明调用方式，不作为实验数据。

## 来源与署名

原始 WebPro 原型及开发记录位于
[dyb158507/RepoSnipy-WebPro](https://github.com/dyb158507/RepoSnipy-WebPro)。

项目建立在 RepoSnipy、RepoSim4Py 和 UniXCoder 等开源工作之上。上游模型、
数据管线和原始应用代码继续归属于各自作者。

## 许可

本项目遵循 [MIT License](LICENSE)。
