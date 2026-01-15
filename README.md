# LinuxDo 每日签到（每日打卡）

## 项目描述

这个项目用于自动登录 [LinuxDo](https://linux.do/) 网站进行每日签到。它使用 Python 标准库实现，无需安装任何第三方依赖，轻量高效。

## 功能

- 自动登录`LinuxDo`。
- 支持多账户同时签到。
- 每天在`GitHub Actions`中自动运行。
- 支持`青龙面板` 和 `Github Actions` 自动运行。
- (可选)`Gotify`通知功能，推送获取签到结果。
- (可选)`Server酱³`通知功能，推送获取签到结果。

## 环境变量配置

### 必填变量

#### 单账户配置

| 环境变量名称             | 描述                | 示例值                                |
|--------------------|-------------------|------------------------------------|
| `LINUXDO_USERNAME` | 你的 LinuxDo 用户名或邮箱 | `your_username` 或 `your@email.com` |
| `LINUXDO_PASSWORD` | 你的 LinuxDo 密码     | `your_password`                    |

#### 多账户配置（推荐）

支持配置多个账户，使用编号后缀区分：

| 环境变量名称               | 描述                | 示例值                                |
|----------------------|-------------------|------------------------------------|
| `LINUXDO_USERNAME_1` | 账户1的用户名或邮箱      | `user1` 或 `user1@email.com`        |
| `LINUXDO_PASSWORD_1` | 账户1的密码          | `pass1`                            |
| `LINUXDO_USERNAME_2` | 账户2的用户名或邮箱      | `user2` 或 `user2@email.com`        |
| `LINUXDO_PASSWORD_2` | 账户2的密码          | `pass2`                            |
| `LINUXDO_USERNAME_3` | 账户3的用户名或邮箱      | `user3` 或 `user3@email.com`        |
| `LINUXDO_PASSWORD_3` | 账户3的密码          | `pass3`                            |

> 注意：编号必须从 1 开始连续，不能跳号。例如配置了账户1和账户3，但未配置账户2，程序只会读取账户1。

### 可选变量

| 环境变量名称            | 描述                   | 示例值                                    |
|-------------------|----------------------|----------------------------------------|
| `GOTIFY_URL`      | Gotify 服务器地址         | `https://your.gotify.server:8080`      |
| `GOTIFY_TOKEN`    | Gotify 应用的 API Token | `your_application_token`               |
| `SC3_PUSH_KEY`    | Server酱³ SendKey     | `sctpxxxxt`                             |

---

## 如何使用

### GitHub Actions 自动运行

此项目的 GitHub Actions 配置会自动每天运行2次签到脚本。你无需进行任何操作即可启动此自动化任务。GitHub Actions 的工作流文件位于 `.github/workflows` 目录下，文件名为 `daily-check-in.yml`。

#### 配置步骤

1. **设置环境变量**：
    - 在 GitHub 仓库的 `Settings` -> `Secrets and variables` -> `Actions` 中添加以下变量：
        - `LINUXDO_USERNAME_1`：你的 LinuxDo 用户名或邮箱（账户1）。
        - `LINUXDO_PASSWORD_1`：你的 LinuxDo 密码（账户1）。
        - (可选) `LINUXDO_USERNAME_2`、`LINUXDO_PASSWORD_2`（账户2）。
        - (可选) 更多账户按编号递增配置。
        - (可选) `GOTIFY_URL` 和 `GOTIFY_TOKEN`。
        - (可选) `SC3_PUSH_KEY`。

2. **手动触发工作流**：
    - 进入 GitHub 仓库的 `Actions` 选项卡。
    - 选择你想运行的工作流。
    - 点击 `Run workflow` 按钮，选择分支，然后点击 `Run workflow` 以启动工作流。

#### 运行结果

##### 网页中查看

`Actions`栏 -> 点击最新的`Daily Check-in` workflow run -> `run_script` -> `Execute script`

可看到`Connect Info`：
（新号可能这里为空，多挂几天就有了）
![image](https://github.com/user-attachments/assets/853549a5-b11d-4d5a-9284-7ad2f8ea698b)

### 青龙面板使用

1. **添加仓库**
    - 进入青龙面板 -> 订阅管理 -> 创建订阅
    - 依次在对应的字段填入内容（未提及的不填）：
      - **名称**：Linux.DO 签到
      - **类型**：公开仓库
      - **链接**：https://github.com/doveppp/linuxdo-checkin.git
      - **分支**：main
      - **定时类型**：`crontab`
      - **定时规则**(拉取上游代码的时间，一天一次，可以自由调整频率): 0 0 * * *

2. **配置环境变量**
    - 进入青龙面板 -> 环境变量 -> 创建变量
    - 需要配置以下变量：
        - `LINUXDO_USERNAME_1`：你的LinuxDo用户名/邮箱（账户1）
        - `LINUXDO_PASSWORD_1`：你的LinuxDo密码（账户1）
        - (可选) `LINUXDO_USERNAME_2`、`LINUXDO_PASSWORD_2`（账户2）
        - (可选) 更多账户按编号递增配置
        - (可选) `GOTIFY_URL`：Gotify服务器地址
        - (可选) `GOTIFY_TOKEN`：Gotify应用Token
        - (可选) `SC3_PUSH_KEY`：Server酱³ SendKey

3. **手动拉取脚本**
    - 首次添加仓库后不会立即拉取脚本，需要等待到定时任务触发，当然可以手动触发拉取
    - 点击右侧"运行"按钮可手动执行

#### 运行结果

##### 青龙面板中查看
- 进入青龙面板 -> 定时任务 -> 找到`Linux.DO 签到` -> 点击右侧的`日志`

### 本地运行

由于本项目只使用 Python 标准库，无需安装任何依赖，直接运行即可：

```bash
python main.py
```

或者配置环境变量后运行：

```bash
export LINUXDO_USERNAME_1="your_username"
export LINUXDO_PASSWORD_1="your_password"
python main.py
```

### Gotify 通知

当配置了 `GOTIFY_URL` 和 `GOTIFY_TOKEN` 时，签到结果会通过 Gotify 推送通知。
具体 Gotify 配置方法请参考 [Gotify 官方文档](https://gotify.net/docs/).

**多账户通知示例：**
```
✅每日签到完成 - 成功: 2/3
✅ 账户1 (user1)
❌ 账户2 (user2)
✅ 账户3 (user3)
```

### Server酱³ 通知

当配置了 `SC3_PUSH_KEY` 时，签到结果会通过 Server酱³ 推送通知。
获取 SendKey：请访问 [Server酱³ SendKey获取](https://sc3.ft07.com/sendkey) 获取你的推送密钥。

## 自动更新

- **Github Actions**：默认状态下自动更新是关闭的，[点击此处](https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web/blob/main/README_CN.md#%E6%89%93%E5%BC%80%E8%87%AA%E5%8A%A8%E6%9B%B4%E6%96%B0)
查看打开自动更新步骤。
- **青龙面板**：更新是以仓库设置的定时规则有关，按照本文配置，则是每天0点更新一次。

## 常见问题

### Q: 为什么不需要安装依赖？
A: 本项目已重构为只使用 Python 标准库，无需安装任何第三方依赖包，开箱即用。

### Q: 如何配置多个账户？
A: 使用编号后缀配置环境变量，如 `LINUXDO_USERNAME_1`、`LINUXDO_USERNAME_2` 等，编号必须从1开始连续。

### Q: 签到失败怎么办？
A: 可以手动重新运行脚本，或者等待下次定时任务自动执行。如果频繁失败，请检查账号密码是否正确。

### Q: 如何查看签到结果？
A: 可以通过 GitHub Actions 日志、青龙面板日志，或配置 Gotify/Server酱³ 推送通知来查看结果。
