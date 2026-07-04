# 🌍 智能旅行规划助手

基于 **LangChain + LangGraph + Streamlit** 的智能旅行规划系统，采用 Multi-Agents 架构，结合双模型协作（DeepSeek R1 + Qwen3），为用户提供智能化的旅行方案。

## 📋 目录

- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [安装运行](#安装运行)
- [使用方法](#使用方法)
- [项目结构](#项目结构)

---

## 🎯 核心功能

- **智能信息提取**：从自然语言中提取出发地、目的地、日期、预算等关键信息
- **交通方案对比**：查询火车票、自驾路线，综合推荐最优方案
- **住宿推荐**：根据预算自动筛选酒店
- **天气查询**：查询旅行日期的天气预报
- **行程规划**：生成每日详细行程和预算分配
- **路线地图**：生成可视化的路线地图
- **RAG 知识检索**：基于向量数据库的旅游攻略查询

---

## 🏗️ 技术架构

### Multi-Agents 工作流

```
用户输入 → Planner Agent → Executor Agent → Summarizer Agent → 最终输出
              (信息提取)      (工具执行)        (方案合成)
```

### 核心技术栈

- **LangGraph**：Multi-Agents 工作流编排
- **LangChain**：Agent 框架和工具集成
- **Streamlit**：Web UI 界面
- **ChromaDB**：向量数据库
- **DeepSeek R1**：复杂推理模型
- **Qwen3**：信息提取和方案生成
- **MCP**：外部工具集成（12306、高德地图、黄历等）

---

## 📦 安装运行

### 1. 安装依赖

```bash
cd multi-agents
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `multi-agents/.env` 文件：

```bash
DEEPSEEK_API_KEY=your-deepseek-api-key
DASHSCOPE_API_KEY=your-dashscope-api-key
BAIDU_AK=your-baidu-api-key
SENSEVERSE_KEY=your-senseverse-key
```

### 3. 启动应用

```bash
cd multi-agents
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

---

## 📖 使用方法

### 简单查询

```
用户：苏州有什么好玩的？
用户：推荐一下成都的景点
```

### 完整规划

```
用户：我想从上海去苏州玩2天，预算1000元，明天出发，帮我规划一下
```

系统会自动生成：
- 基本信息（路线、日期、天气）
- 交通方案对比
- 住宿推荐
- 每日行程安排
- 预算分配明细

---

## 📁 项目结构

```
travel-agent/
├── multi-agents/
│   ├── agent_nodes/          # Agent 实现
│   │   ├── planner_agent.py     # 规划师
│   │   ├── executor_agent.py    # 执行者
│   │   ├── summarizer_agent.py  # 总结者
│   │   ├── feedback_agent.py    # 反馈代理
│   │   └── main_agent.py        # 主协调
│   ├── config/               # 配置文件
│   │   ├── prompts.py           # Prompt 模板
│   │   ├── settings.py          # 全局配置
│   │   └── servers_config.json  # MCP 服务器配置
│   ├── graph/                # LangGraph 工作流
│   │   ├── workflow.py          # 工作流定义
│   │   └── state.py             # 状态类型
│   ├── tools/                # 工具集
│   │   ├── rag_tool.py          # RAG 向量检索
│   │   ├── mcp_tools.py         # MCP 工具管理
│   │   └── tool_registry.py     # 工具注册
│   ├── components/           # UI 组件
│   ├── data/                 # 数据目录
│   ├── app.py                # Streamlit 入口
│   └── requirements.txt      # 依赖列表
├── README.md
└── LICENSE
```

---

## 📄 许可证

本项目采用 MIT 许可证。