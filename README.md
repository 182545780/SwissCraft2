# SwissCraft 小瑞士 — 星际争霸2 瑞士轮赛事系统

> 一个开箱即用的星际争霸2线上赛事管理平台，支持瑞士轮自动配对 + 八强淘汰赛全流程。
> 附赠零代码可视化仪表盘，改文字、换颜色、传图片，点几下鼠标就完事。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 瑞士轮配对 | 自动按胜场配对，已交手的不重复相遇 |
| 积分榜 | 实时排名，对手分破同分 |
| 八强淘汰赛 | 树状赛程，自动晋级 |
| 在线报名 | 选手自行提交，管理员控制开关和名额 |
| 录像库 | 上传下载比赛录像 |
| 可视化仪表盘 | 改文字、换颜色、调主题、传Banner，零基础友好 |
| 多语言 | 内置中文和英文，自动检测浏览器语言 |
| 演示数据 | 一键生成假选手和比赛数据，方便测试 |

---
<img width="3600" height="2086" alt="05ac599ce2ff4dc373596ccc25c9a5a7" src="https://github.com/user-attachments/assets/03262c41-f9bb-4c74-aff0-a2090425611a" />
<img width="3600" height="2086" alt="39323d0fdd63800bbae247c001e9f10e" src="https://github.com/user-attachments/assets/c432ebc5-37e1-4f0d-b73d-1aead4795023" />
<img width="3600" height="2086" alt="51d542b7f4e7aa807ab87679e7b65bcf" src="https://github.com/user-attachments/assets/18627a0e-f464-4d3f-af72-2661f935cae4" />
<img width="3600" height="2086" alt="9d8d29e4542481c77cd3e46eea1449ac" src="https://github.com/user-attachments/assets/001daaa8-40c6-4924-a3f4-5f454cb0999e" />
<img width="3600" height="2086" alt="cabf161019158908c258df5a177aa618" src="https://github.com/user-attachments/assets/e0682234-902e-4df2-9ccf-68da8118f268" />


## 5分钟快速启动

### 环境要求
- Python 3.10+
- pip

### 安装启动

```bash
git clone https://github.com/182545780/SwissCraft.git
cd SwissCraft

pip install -r requirements.txt

chmod +x run.sh
./run.sh

# 指定端口
./run.sh 8080
```

浏览器打开 **http://127.0.0.1:8000**

---

## 配置说明

编辑 `config.json` 即可修改，不用碰代码：

```json
{
  "admin_password": "dsb2026",
  "total_rounds": 5,
  "max_players": 24,
  "default_language": "zh",
  "seed_players": []
}
```

| 配置项 | 说明 |
|--------|------|
| admin_password | 仪表盘管理员密码 |
| total_rounds | 瑞士轮总轮数 |
| default_language | `zh` 中文 / `en` 英文 |
| seed_players | 预置选手列表（留空则从仪表盘添加） |

---

## 可视化仪表盘

访问 **http://127.0.0.1:8000/admin**

**默认密码: `dsb2026`**

### 改页面内容
比赛名称、赛程时间、奖金金额、联系方式，输入框里直接改，点保存刷新首页就看效果。

### 换颜色主题
背景色、卡片色、文字色、强调色，调色盘随便选。

### 换Banner图
上传一张新图片，自动替换首页大横幅。

### 管理比赛
- 点一下生成下一轮，自动配对
- 点选手名字记录胜负
- 一键生成八强对阵

### 管报名
开关报名通道、改名额、审核选手。

### 演示数据
系统设置 > 生成演示数据，一键创建12名假选手+2轮比赛结果，点清除全部清空。

---

## 多语言

每个页面右上角都有语言切换按钮：

- **中** — 中文
- **EN** — English

翻译文件在 `src/i18n/zh.json` 和 `src/i18n/en.json`，想加新语言直接新建一个 json 文件就行。

---

## 项目结构

```
SwissCraft/
  config.json           配置文件（不改代码）
  run.sh                启动脚本
  requirements.txt      依赖（就 fastapi 和 uvicorn）
  README.md             本文件
  LICENSE               MIT 协议
  .gitignore

  src/                  Python 后端
    main.py             FastAPI 入口 + 全部 API
    database.py         SQLite 数据库（选手/比赛/状态）
    dashboard_db.py     仪表盘配置模块（38项可编辑内容）
    i18n.py             多语言模块
    bracket.py          八强淘汰赛逻辑
    registration.py     在线报名系统
    dsb_videos.py       录像管理
    models.py           数据模型
    image/              地图图片
    i18n/               翻译文件
      zh.json           中文
      en.json           英文

  bisai/                前端页面
    main.html           首页（赛事章程）
    saicheng.html       积分榜
    bracket.html        淘汰赛
    register.html       报名页
    videos.html         录像库
    admin.html          可视化仪表盘
```

---

## 管理员操作

| 页面 | 路径 | 说明 |
|------|------|------|
| 仪表盘 | `/admin` | 可视化修改所有内容 |
| 赛事章程 | `/` | 首页规则展示 |
| 积分榜 | `/saicheng` | 实时排名 |
| 淘汰赛 | `/bracket` | 八强树状图 |
| 报名 | `/register` | 选手报名 |
| 录像库 | `/videos` | 比赛录像 |

### 修改管理员密码

仪表盘系统设置 > 修改密码

或者环境变量：
```bash
export DSB_ADMIN_PASSWORD=你的密码
./run.sh
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python + FastAPI |
| 数据库 | SQLite（无需安装，自动创建） |
| 前端 | 原生 HTML/CSS/JS（零框架依赖） |
| 图标 | SVG（页面零 emoji） |
| 部署 | 单命令启动，一行搞定 |

---

## 开源协议

MIT License — 随便用、随便改、随便发。

---

## 联系

- 交流群: 701237203
- 问题反馈: GitHub Issues

**GL HF**

---

> **English Summary:** SwissCraft is an open-source StarCraft II Swiss tournament system with auto-pairing, bracket knockout, online registration, VOD library, and a no-code visual dashboard. Built with Python + FastAPI + SQLite, zero frontend dependencies. MIT licensed.

