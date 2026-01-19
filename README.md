# Linux.Do 签到

自动登录 Linux.Do 并进行浏览任务，支持多账号、通知和 GitHub Actions/青龙面板运行。

## 功能

- 多账号顺序执行
- 自动登录 + 浏览帖子
- 单账号超时控制（浏览开启 15 分钟；关闭 3 分钟）
- Gotify / Server酱³ 通知
- GitHub Actions 定时与手动测试

## 环境变量

### 必填（两种方式任选其一）

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `LINUXDO_ACCOUNTS` | 多账号，`username:password`，使用 `;` 或换行分隔 | `user1:pass1;user2:pass2` |
| `LINUXDO_USERNAME` | 单个或多个用户名（与密码数量一致） | `user1;user2` |
| `LINUXDO_PASSWORD` | 单个或多个密码（与用户名数量一致） | `pass1;pass2` |

### 可选

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `BROWSE_ENABLED` | 是否启用浏览 | `true` |
| `BROWSE_MAX_TOPICS` | 每账号浏览帖子上限 | `10` |
| `AUTO_INSTALL_DEPS` | 自动检测并安装依赖（需要 pip） | `true` |
| `LINUXDO_UA` | 多账号 UA 列表（按顺序对应） | 空=默认 Windows UA |
| `GOTIFY_URL` | Gotify 服务器地址 | 空 |
| `GOTIFY_TOKEN` | Gotify 应用 Token | 空 |
| `SC3_PUSH_KEY` | Server酱³ SendKey | 空 |

### 多账号 UA 示例

UA 本身包含 `;`，因此使用 `||` 或换行分隔：
```
LINUXDO_UA="UA1||UA2||UA3"
```

未配置或数量不足时，自动使用默认 Windows UA。

## GitHub Actions

### 定时运行（每天北京时间 10:00）

工作流：`.github/workflows/linuxdo-daily.yml`

在仓库 `Settings -> Secrets and variables -> Actions` 配置：
- `LINUXDO_ACCOUNTS`（推荐）
- 或 `LINUXDO_USERNAME` / `LINUXDO_PASSWORD`
- (可选) `LINUXDO_UA` / `BROWSE_ENABLED` / `GOTIFY_URL` / `GOTIFY_TOKEN` / `SC3_PUSH_KEY`

### 手动测试（只浏览 1 个帖子）

工作流：`.github/workflows/manual-test.yml`

手动运行即可，功能与正式一致，但固定 `BROWSE_MAX_TOPICS=1`。

## 青龙面板

1) 依赖安装  
进入青龙面板 -> 依赖管理 -> 安装依赖  
类型选择 `python3`，内容填写 `requirements.txt` 的全部内容。

2) 安装 Chromium  
依赖管理 -> 安装 Linux 依赖 -> `chromium`

3) 配置环境变量  
青龙面板 -> 环境变量  
建议设置 `LINUXDO_ACCOUNTS`，多账号更直观。

## 常见问题

- `pip3: command not found`  
  使用青龙依赖管理器安装，或先安装 `python3-pip`。

- `curl-cffi` 安装失败（提示缺少 gcc）  
  需要安装编译环境：`gcc` / `make` / `libffi-dev` / `python3-dev` 等，或改用青龙依赖管理器安装。

## 免责声明

本项目仅用于学习与自动化实践，请合理使用并遵守网站规则。
