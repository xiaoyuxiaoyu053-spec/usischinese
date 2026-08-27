# STAONS

一个类 Roblox 风格的小型游戏平台原型:注册 / 登录 / 图形验证码 / 游戏大厅 / 开发者后台。

## 功能说明

- **首页(封面页)**:显示 `static/img/cover.png` 封面图 + 网站名「STAONS」+「注册账户」「登录」按钮。
  - 封面图是我生成的一张不含任何角色形象的占位图(避免版权问题),你可以直接替换 `static/img/cover.png` 为你自己拥有版权的图片,尺寸建议横向、宽度 ≥ 800px。
- **注册**:用户名(3-20位,字母/数字/下划线)+ 密码(≥8位,与 Roblox 类似的基础规则,不含性别/生日)+ 图形验证码,验证通过才能注册成功,注册成功后跳回首页。
- **登录**:用户名+密码登录后进入游戏大厅;账户被封禁则无法登录。
- **游戏大厅** `/games`:展示后台添加的所有游戏(图标+名字)。
- **开发者后台**:
  - 每个页面右上角都有 `dev` 按钮,点击进入 `/dev` 输入密码 `starconssifu`。
  - 后台 `/admin` 可以:
    - 查看所有注册玩家,封禁/解封、删除账户
    - 添加游戏(名字 + 图标图片),添加后立即出现在游戏大厅
    - 删除已添加的游戏

## 目录结构

```
staons/
├── app.py                # Flask 主程序(路由、数据库模型、验证码)
├── requirements.txt
├── Procfile               # Render 启动命令
├── render.yaml             # Render 一键部署蓝图(可选)
├── templates/              # 页面模板
└── static/
    ├── css/style.css
    ├── img/cover.png       # 封面图(可替换)
    └── uploads/             # 后台上传的游戏图标存放处
```

## 本地运行

```bash
cd staons
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

打开浏览器访问 `http://127.0.0.1:5000`。

## 部署到 Render

### 方式一:使用 render.yaml 一键部署(推荐)

1. 把这个项目推送到一个 GitHub 仓库(私有或公开均可)。
2. 登录 [Render](https://render.com) → New → **Blueprint**。
3. 选择你的仓库,Render 会自动读取 `render.yaml` 并创建一个 Web Service。
4. 等待构建完成即可访问分配到的 `xxx.onrender.com` 域名。

### 方式二:手动创建 Web Service

1. GitHub 新建仓库并上传本项目全部文件。
2. Render 控制台 → New → **Web Service** → 关联该仓库。
3. 配置:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. 在 Environment 变量中添加 `SECRET_KEY`(任意一串随机字符串)。
5. 点击 Create Web Service,等待部署完成。

### 关于数据持久化(重要)

项目默认使用 SQLite(`staons.db`)保存账户和游戏数据,上传的游戏图标保存在 `static/uploads/`。

Render **免费套餐的磁盘是非持久化的**:每次重新部署(push 新代码 / 手动 redeploy)都会清空这些文件,服务本身运行期间数据是正常保留的。如果你需要数据长期不丢失,有两个办法:

1. 给 Web Service 挂载一个 **Render Disk**(付费的持久化磁盘),把 `staons.db` 和 `static/uploads/` 目录指向这个磁盘路径;或者
2. 换成 Render 提供的免费 **PostgreSQL** 数据库,把 `DATABASE_URL` 环境变量指向它(代码里已经支持通过 `DATABASE_URL` 环境变量覆盖数据库地址),游戏图标则建议改为上传到外部图床/对象存储(如 Cloudinary)。

对于测试、演示或课程作业级别的用途,默认的 SQLite 方案完全够用。

## 修改开发者密码

开发者后台密码写在 `app.py` 顶部的 `DEV_PASSWORD = "starconssifu"`,如需修改直接改这个值即可(建议正式使用前修改为你自己的密码,并考虑通过环境变量传入而不是写死在代码里)。
