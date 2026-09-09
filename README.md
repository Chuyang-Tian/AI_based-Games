# DeiDei 叠叠对战

一个带 GUI 的策略对战小游戏项目，包含：

- 本地双状态博弈规则与结算逻辑
- 简单 AI / 近似 GTO AI / 专家 RL AI
- 面向新手的招式说明、规则提示和对局记录
- 用于训练与评估 RL 模型的脚本

## 运行环境

- Windows
- Python 3.10+

## 快速开始

推荐直接双击根目录下的 `DeiDei启动.bat`。

它会自动：

1. 检查本机是否安装 Python
2. 首次安装依赖
3. 启动 `gui_deidei.py`

如果你想手动启动，也可以执行：

```powershell
python -m pip install -r requirements_rl.txt
python gui_deidei.py
```

## 主要文件

- `gui_deidei.py`：主界面与交互逻辑
- `deidei_env.py`：核心规则、状态与结算逻辑
- `deidei_gym_env.py`：Gym 环境封装
- `rl_ai.py`：专家 AI 推理与模型加载
- `train_ppo_selfplay.py`：自博弈训练脚本
- `evaluate_rl_now.py`：模型即时评估脚本
- `requirements_rl.txt`：依赖列表

## 专家 AI 说明

专家 AI 默认从 `rl_checkpoints/latest.zip` 加载模型。

这个源码仓库会保留运行所需的 `latest.zip`，但不会跟踪训练过程中的历史检查点、TensorBoard 日志、打包目录、`exe` 和发布压缩包，避免仓库体积持续膨胀。

## GitHub 发布建议

- GitHub 仓库：放源码、说明文档和运行所需的最小模型文件
- GitHub Releases：放 `DeiDei_v1.0.zip` 这类给朋友直接下载的成品包

这样仓库会更干净，也更适合后续继续开发。
